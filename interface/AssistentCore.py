from UserInterface import UserInterface, ui_signals
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtCore import QThread
from typing import Union, List
import sys
import os
from datetime import datetime
VOICE_INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'interface', 'VoiceInput'))
if VOICE_INPUT_DIR not in sys.path:
    sys.path.insert(0, VOICE_INPUT_DIR)
import threading
from BasicUtils import BasicUtils, DataBaseEditor, global_signals
import VoiceInput.WhisperRecognition as Whisper
from TTSSilero import SileroTTS 
from Ai_Request.NetworkChecker import NetworkChecker
from Ai_Request.MedicalAPI import MedicalAPI
from Ai_Request.LocalModel import LocalModel
import VoiceInput.VoskRecognition as Vosk 
from dotenv import load_dotenv

load_dotenv()
DATABASE_EDITOR = DataBaseEditor()
WHISPER_MODEL = Whisper.WhisperRecognition(model_download_root="./models")
VOSK_MODEL = Vosk.VoskRecognizer(model_path="./models/vosk-model-small-ru-0.22")

TTSSILERO_MODEL = SileroTTS()

class MedicalWorker(QThread):
    finished = pyqtSignal(object)  # str или List[str]

    def __init__(self, model, prompt):
        super().__init__()
        self.model = model
        self.prompt = prompt

    def run(self):
        try:
            result = self.model.generate(self.prompt)
            self.finished.emit(result)
        except Exception as e:
            BasicUtils.logger("MedicalWorker", "ERROR", f"Ошибка генерации: {e}")
            self.finished.emit(f"Ошибка при обращении к модели: {str(e)}")

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
        
        self.network_checker = NetworkChecker()
        self.network_checker.connection_changed.connect(self._on_network_status)
        self.network_checker.start()
        
        # Инициализация моделей
        try:
            self.remote_model = MedicalAPI()
            BasicUtils.logger("AssistentCore", "INFO", "MedicalAPI успешно инициализирован")
        except Exception as e:
            BasicUtils.logger("AssistentCore", "ERROR", f"Не удалось инициализировать MedicalAPI: {e}")
            self.remote_model = None

        self.local_model = LocalModel()
        self.active_model = self.local_model
        self.current_worker = None
   
    def _on_network_status(self, online: bool):
        if online and self.remote_model is not None:
            self.active_model = self.remote_model
            BasicUtils.logger("AssistentCore", "INFO", "Активирована облачная медицинская модель")
        else:
            self.active_model = self.local_model
            if not online:
                BasicUtils.logger("AssistentCore", "WARNING", "Интернет отсутствует – активирована локальная заглушка")
            else:
                BasicUtils.logger("AssistentCore", "ERROR", "Облачная модель недоступна, используется локальная заглушка")

    def generate_medical_answer(self, prompt: Union[str, List[str]]):
        if self.active_model is None:
            self._on_network_status(self.network_checker.is_online())
        BasicUtils.logger("AssistentCore", "INFO", f"Запрос к {self.active_model.__class__.__name__}: {prompt}")
        if self.current_worker and self.current_worker.isRunning():
            BasicUtils.logger("AssistentCore", "WARNING", "Предыдущий запрос ещё выполняется, игнорируем новый")
            return
        self.current_worker = MedicalWorker(self.active_model, prompt)
        self.current_worker.finished.connect(self._on_medical_answer)
        self.current_worker.start()

    def _on_medical_answer(self, answer: Union[str, List[str]]):
        self.current_worker = None
        if isinstance(answer, list):
            for ans in answer:
                BasicUtils.add_message("assistant", ans)
                ui_signals.message_sent.emit("assistant", ans)
                self.text_to_speech(ans)
        else:
            BasicUtils.add_message("assistant", answer)
            ui_signals.message_sent.emit("assistant", answer)
            self.text_to_speech(answer)
   
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

    def on_message_sent(self, sender: str = "Unknown", message: str = "No Message"):
        BasicUtils.logger("CORE | MessageSent", "INFO", f"Сообщение от {sender}: {message}")
        if sender == "user":
            self.generate_medical_answer(message)
    
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
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    assistent = AssistentCore()
    assistent.run()
    sys.exit(app.exec())