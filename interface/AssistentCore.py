from UserInterface import UserInterface, ui_signals
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
import sys
import os
from datetime import datetime
from pathlib import Path
VOICE_INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'interface', 'VoiceInput'))
if VOICE_INPUT_DIR not in sys.path:
    sys.path.insert(0, VOICE_INPUT_DIR)
import threading
from BasicUtils import BasicUtils, DataBaseEditor, global_signals
import VoiceInput.WhisperRecognition as Whisper
from TTSSilero import SileroTTS 
from qwen_recommender.QwenModel import QwenModel, QWEN_MODEL
from qwen_recommender.QwenRequest import QwenRequest
from qwen_recommender.RecommendationManager import RecommendationManager
import VoiceInput.VoskRecognition as Vosk 
RECOMMENDATION_CACHE = Path(__file__).parent.parent / "data" / "recommendation.json"
DATABASE_EDITOR = DataBaseEditor()
WHISPER_MODEL = Whisper.WhisperRecognition(model_download_root="./models")
VOSK_MODEL = Vosk.VoskRecognizer(model_path="./models/vosk-model-small-ru-0.22")
QWEN_MODEL = QwenModel("./models/qwen2.5-3b/qwen2.5-3b.Q4_K_M.gguf")
QWEN_REQUEST = QwenRequest(QWEN_MODEL.model_file, n_threads=4, n_gpu_layers=0)
TTSSILERO_MODEL = SileroTTS()

class AssistentCore():
    def __init__(self):
        self.user_interface = UserInterface()
        self.settings_config = BasicUtils.load_settings_config()
        self.recognition_model = self.settings_config.get("recognition_model", "auto")

        self.whisper_model = WHISPER_MODEL
        self.vosk_model = VOSK_MODEL
        self.tts_voice = BasicUtils.get_settings_config_value("tts_voice")
        self.ttssilero_model = TTSSILERO_MODEL
        # Подписка на сигналы интерфейса
        ui_signals.message_sent.connect(self.on_message_sent)
        ui_signals.settings_changed.connect(self.on_settings_changed)
        ui_signals.voice_input_changed.connect(self.on_voice_input_changed)
        global_signals.voice_message_recognized.connect(self.voice_text_recived_core)
        ui_signals.speaker_pressed.connect(self.text_to_speech)
        ui_signals.speaker_stop_request.connect(self.stop_speech)
        ui_signals.clear_history_requested.connect(self.clear_chat_history)
        global_signals.error_signal.connect(self.handle_error)
        QWEN_REQUEST.recommendation_ready.connect(self._apply_recommendations)
        self.rec_manager = RecommendationManager(QWEN_REQUEST)
        self.rec_manager.recommendation_ready.connect(self._on_rec_ready)
        self.rec_manager.analyze()  # Асинхронный запуск: кэш → AI → сигнал
    
        
    def handle_error(self, error_message: str):
        """Обработка ошибок, полученных из разных частей системы, с логированием"""
        self.text_to_speech(error_message)

    def clear_chat_history(self):
        """Очищает историю чата через BasicUtils с логированием"""
        BasicUtils.logger("CORE | ClearHistory", "INFO", "Запрошена очистка истории чата")
        try:
            BasicUtils.clear_chat_history()  # новый метод из BasicUtils
            BasicUtils.logger("CORE | ClearHistory", "INFO", "История чата успешно очищена")
            ui_signals.history_cleared.emit()
        except Exception as e:
            BasicUtils.logger("CORE | ClearHistory", "ERROR", f"Ошибка при очистке истории: {e}")  
            global_signals.error_signal.emit(f"Ошибка при очистке истории: {e}")

    def on_voice_input_changed(self, status):
        """Принимает status: True - включена, False - выключена."""
        """
           Логика работы голосового:
           1. Пользователь включает кнопку -> Интерфейс создает сигнал с True
           2. Ядро принимает сигнал, если status == True -> Проверяет, не ложный ли он и изменились параметры ->
               1. Всё ок, проверяет режим, если auto -> Проверяет, какой распознаватель лучше для текущей системы ->
               Включает его -> Далее голосовой распознаватель как только распознает команду, создаёт сигнал
               voice_message_recognized и отправляет распознанный текст в ядро -> Ядро принимает сигнал и 
               рассылает его всем, кому нужно (например, в интерфейс для отображения распознанного текста)
               2. -> Что-то не так, выключает голосовое и пишет в настройки, что запись отключена 
            3. Как только текст распознан, вызывается функция voice_text_recived_core, которой передается распознанный 
            текст, и та уже создает сигнал, отправляющий сообщение
            4. Пользователь выключает кнопку -> Интерфейс создает сигнал с False -> Ядро принимает сигнал, выключает распознавание и пишет в настройки, что запись отключена
        """
        BasicUtils.logger("CORE | VoiceInputChanged", "INFO", f"Статус голосового ввода (конфиг): {BasicUtils.get_settings_config_value('recording_enabled')}")
        BasicUtils.logger("CORE | VoiceInputChanged", "INFO", f"Получен статус: {status}")
        if status and BasicUtils.get_settings_config_value("recording_enabled"):
            self.recognition_model= BasicUtils.get_settings_config_value("recognition_model")
            if self.recognition_model == "auto":
                if self.check_best_voice_rec() == "vosk":
                    self.start_vosk()
                elif self.check_best_voice_rec() == "faster-whisper":
                    self.control_whisper(True)
            elif self.recognition_model == "vosk":
                self.control_vosk(True)
            elif self.recognition_model == "faster-whisper":
                self.control_whisper(True)
        else:
            # При выключении останавливаем ОБЕ модели
            BasicUtils.set_settings_config_value("recording_enabled", False)
            self.control_whisper(False)
            self.control_vosk(False)
    
    def control_whisper(self, new_status: bool):
        """Управление Whisper"""
        if new_status:
            self.whisper_model.start_recognition()
        else:
            self.whisper_model.stop_recognition()
    
    def control_vosk(self, new_status: bool):
        """Управление Vosk"""
        if new_status:
            self.vosk_model.start_recognition()
        else:
            self.vosk_model.stop_recognition()
    
    def check_best_voice_rec(self) -> str:
        BasicUtils.logger("CORE | CheckBestVoiceRec", "INFO", "Проверка лучшего распознавания голоса для системы...")
        BasicUtils.logger("CORE | CheckBestVoiceRec", "INFO", "Проверка Vosk...")
        # Здесь должна быть реальная проверка, но для примера просто вернем faster-whisper
        BasicUtils.logger("CORE | CheckBestVoiceRecCORE", "INFO", "Проверка Whisper...")
        # Здесь должна быть реальная проверка, но для примера просто вернем faster-whisper

        self.recognition_model = "faster-whisper"
        BasicUtils.logger("CORE | CheckBestVoiceRec", "INFO", f"Лучшее распознавание голоса: {self.recognition_model}")
        return self.recognition_model
   
    def text_to_speech(self, text: str):
        """Преобразование текста в речь с выбором модели TTS в зависимости от настроек"""
        if not text or not text.strip():
            return
        
        # Останавливаем предыдущее воспроизведение и сбрасываем все кнопки
        self.stop_speech()
        
        # Получаем настройки
        tts_speed = BasicUtils.get_settings_config_value("tts_speed")
        tts_model = BasicUtils.get_settings_config_value("tts_model")
        tts_voice = BasicUtils.get_settings_config_value("tts_voice")
        
        # Словарь с доступными TTS моделями
        tts_engines = {
            "silero": self.ttssilero_model,
            # тут могут быть другие модели по аналогии с silero
        }
        
        # Выбираем нужную модель или используем Silero по умолчанию
        tts_engine = tts_engines.get(tts_model, self.ttssilero_model)
        
        if tts_model != "silero" and tts_model not in tts_engines:
            BasicUtils.logger("CORE | TTS", "WARNING", f"Неизвестная модель TTS: {tts_model}, используем Silero")
        
        BasicUtils.logger("CORE | TTS", "INFO", f"TTS: модель={tts_model}, голос={tts_voice}, скорость={tts_speed}")
        
        # Функция обратного вызова по окончании воспроизведения
        def on_finished():
            BasicUtils.logger("CORE | TTS", "INFO", "Воспроизведение завершено")
            ui_signals.speaker_finished.emit()
        
        # Запускаем асинхронное воспроизведение с callback
        if hasattr(tts_engine, 'speak_async'):
            tts_engine.speak_async(text, tts_voice, tts_speed, callback=on_finished)
        else:
            # fallback на обычный speak (без callback)
            tts_engine.speak(text, tts_voice, tts_speed)
            # В этом случае кнопка не сбросится автоматически, но можно запустить таймер
            BasicUtils.logger("CORE | TTS", "WARNING", "Модель TTS не поддерживает speak_async, кнопка не сбросится автоматически")
        
    def stop_speech(self):
        """Останавливает текущее воспроизведение речи и сбрасывает кнопки."""
        if hasattr(self.ttssilero_model, 'stop'):
            self.ttssilero_model.stop()
            BasicUtils.logger("CORE | TTS", "INFO", "Воспроизведение остановлено пользователем")
            # Сбрасываем все кнопки динамиков
            ui_signals.speaker_stop_all.emit()
        else:
            BasicUtils.logger("CORE | TTS", "WARNING", "Модель TTS не поддерживает остановку")    

    def on_message_sent(self, sender : str = "Unknown", message : str = "No Message"):
        print(f"Message from {sender}: {message}")
    
    def update_voice_recognition_model(self, new_model: str):
        """Функция, перезапускающая модель в реальном времени, если та включена"""
        if new_model != self.recognition_model:
            BasicUtils.logger("CORE | VoiceRecognitionModel", "INFO", f"Обновление модели распознавания голоса: {new_model}")
            self.recognition_model = new_model
            
            self.control_whisper(False)
            self.control_vosk(False)

            target = self.recognition_model
            if BasicUtils.get_settings_config_value("recording_enabled"):
                if target == "auto":
                    if self.check_best_voice_rec() == "vosk":
                        self.control_vosk(True)
                    elif self.check_best_voice_rec() == "faster-whisper":
                        self.control_whisper(True)
                elif target == "vosk":
                    self.control_vosk(True)
                elif target == "faster-whisper":
                    self.control_whisper(True)

    def on_settings_changed(self, new_settings: dict):
        BasicUtils.logger("CORE | SettingsConfiguration", "INFO", f"Настройки конфигурации обновлены: {new_settings}") 
        if "recognition_model" in new_settings:
            self.update_voice_recognition_model(new_settings["recognition_model"])

    def voice_text_recived_core(self, text: str):
        """Приём распознанного текста и пересылка в интерфейс"""
        BasicUtils.logger("CORE | VoiceTextRecivedCore", "INFO", f"Распознан текст: {text}")
        ui_signals.voice_message_received.emit(text)

    def run(self):
        """Запуск интерфейса"""
        self.user_interface.show()
        
    def _check_qwen_ready(self) -> bool:
        """Безопасная проверка готовности модели перед инференсом."""
        if not QWEN_MODEL.is_ready:
            BasicUtils.logger("CORE | Qwen", "WARNING", "Модель Qwen2.5:3b ещё загружается или недоступна. Запрос отклонён.")
            # Опционально: можно отправить сигнал в UI, чтобы показать пользователю статус
            return False
        return True  

    def _on_rec_ready(self, recommendation_text: str):
        """Парсит ответ AI, конвертирует в русский текст для UI и сохраняет технические коды в конфиг."""
        # 1. Очистка от знаков препинания и приведение к нижнему регистру
        cleaned = recommendation_text.lower().replace(',', ' ').replace('.', ' ').replace(';', ' ')
        raw_methods = cleaned.split()
        valid_methods = {"vosk", "faster-whisper", "gesture", "text"}
        chosen = [m for m in raw_methods if m in valid_methods]

        if not chosen:
            chosen = ["text"]

        # 2. Маппинг технических названий → человекочитаемый русский текст
        MODEL_TO_RU = {
            "vosk": "Голосовой ввод (Vosk)",
            "faster-whisper": "Голосовой ввод (Whisper)",
            "gesture": "Жестовый ввод",
            "text": "Текстовый ввод"
        }

        human_readable = [MODEL_TO_RU.get(m, m) for m in chosen]
        rec_string = ", ".join(human_readable)

        # 3. Находим первый рекомендованный голосовой движок для автоматического переключения
        voice_model = next((m for m in chosen if m in ("vosk", "faster-whisper")), None)

        # 4. Сохраняем ТЕХНИЧЕСКИЕ параметры в конфиг (для работы движков)
        BasicUtils.set_settings_config_value("primary_input_method", chosen[0])
        if voice_model:
            BasicUtils.set_settings_config_value("recognition_model", voice_model)

        BasicUtils.logger("CORE | Advisor", "INFO", f"AI рекомендовал способы: {rec_string}")

        # 5. Отправляем в интерфейс РУССКУЮ рекомендацию + технический переключатель
        update_payload = {
            "ai_recommendation": f"Рекомендуемые способы: {rec_string}"
        }
        if voice_model:
            update_payload["recognition_model"] = voice_model

        ui_signals.settings_changed.emit(update_payload)
        
    def _on_rec_failed(self, error: str):
        """Логирование ошибки без озвучки (чтобы не пугать пользователя)."""
        BasicUtils.logger("CORE | Advisor", "ERROR", f"Сбой анализа профиля: {error}")
        # Опционально: можно отправить fallback-текст в UI
        ui_signals.settings_changed.emit({
            "ai_recommendation": "Не удалось получить рекомендацию. Используются стандартные настройки."
        })

    def _handle_qwen_error(self, error_msg: str):
        """Обработка ошибок анализа (не озвучивает, только логирует)."""
        BasicUtils.logger("CORE | QwenAdvisor", "ERROR", f"Ошибка анализа профиля: {error_msg}")
        
    def _apply_recommendations(self, recommendation_text: str):
        BasicUtils.logger("CORE | Advisor", "INFO", f"Рекомендация: {recommendation_text}")
        ui_signals.settings_changed.emit({"ai_recommendation": recommendation_text})
                        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    assistent = AssistentCore()
    assistent.run()
    sys.exit(app.exec())