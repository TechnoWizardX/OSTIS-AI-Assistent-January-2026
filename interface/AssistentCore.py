from UserInterface import UserInterface, ui_signals
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtCore import QThread
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
from Ai_Request_Manager.NetworkChecker import NetworkChecker
from Ai_Request_Manager.LocalModel import LocalModel
from Ai_Requests.AccessibilityRecommender import AccessibilityRecommender
from IntentHandler import IntentHandler, IntentWorker
from dotenv import load_dotenv
from SystemControl import ControlSystem
load_dotenv()
DATABASE_EDITOR = DataBaseEditor()
WHISPER_MODEL = Whisper.WhisperRecognition(model_download_root="./models")
TTSSILERO_MODEL = SileroTTS()
INTENT_HANDLER = IntentHandler(online_model="google/gemma-4-26b-a4b-it:free")

class AssistentCore():
    def __init__(self, api_key: str = ""):
        self.user_interface = UserInterface(api_key=api_key)
        self.settings_config = BasicUtils.load_settings_config()
        
        self.network_checker = NetworkChecker()
        self.network_checker.connection_changed.connect(self._on_network_status)
        self.network_checker.start()

        # Локальная модель используется только как заглушка
        self.local_model = LocalModel()
        self.active_model = self.local_model
        self.current_worker = None

        # Инициализация рекомендателя (рекомендации отправляются только в профиль)
        self.accessibility_advisor = AccessibilityRecommender()
        # Подключаем сигнал рекомендателя к сигналу интерфейса для обновления профиля
        # accessibility_advisor передаёт (methods, text), recommendation_ready принимает то же
        self.accessibility_advisor.recommendation_obtained.connect(lambda methods, text: ui_signals.recommendation_ready.emit(methods, text))

        # Автозапуск при каждом сохранении профиля
        ui_signals.profile_updated.connect(lambda: self.accessibility_advisor.request_recommendation(0))
        
        self.recognition_model = self.settings_config.get("recognition_model", "auto")

        self.whisper_model = WHISPER_MODEL
        self.tts_voice = BasicUtils.get_settings_config_value("tts_voice")
        self.ttssilero_model = TTSSILERO_MODEL
        
        self.intent_handler = INTENT_HANDLER
        self.intent_handler.start_ollama()
        
        # Подписка на сигналы интерфейса
        ui_signals.message_sent.connect(self.on_message_sent)
        ui_signals.settings_changed.connect(self.on_settings_changed)
        ui_signals.voice_input_changed.connect(self.on_voice_input_changed)
        global_signals.voice_message_recognized.connect(self.voice_text_recived_core)
        ui_signals.speaker_pressed.connect(self.text_to_speech)
        ui_signals.speaker_stop_request.connect(self.stop_speech)
        ui_signals.clear_history_requested.connect(self.clear_chat_history)
        global_signals.error_signal.connect(self.handle_error)
        ui_signals.openrouter_api_key_changed.connect(lambda key: self.intent_handler.update_api_key(key))
   
    def _on_network_status(self, online: bool):
        """Обработка статуса сети (для информации)."""
        if not online:
            BasicUtils.logger("AssistentCore", "WARNING", "Интернет отсутствует")
        else:
            BasicUtils.logger("AssistentCore", "INFO", "Интернет подключён")

    def handle_intent(self, intent_data: dict):
        """Обработка распознанного интента от IntentHandler и выполнение соответствующих действий"""
        message = intent_data.get("message", "")
        action = intent_data.get("action", "answer")
        function = intent_data.get("function", "")
        params = intent_data.get("params", {})
        info = intent_data.get("info", "")
        BasicUtils.logger("CORE | IntentHandler", "INFO", f"Получен интент: {intent_data}")
        
        if action == "answer":
            self.send_ai_message(message)
        elif action == "unknown":
            self.send_ai_message(message)
        elif action == "invalid":
            self.send_ai_message(message)
        else:
            self.send_ai_message(message)
            self.actions_mapping(function, params, info)
    def actions_mapping(self, function_name: str, params: dict, info: str):
        """Здесь будет логика сопоставления имен функций к реальным функциям в коде"""
        BasicUtils.logger("CORE | ActionsMapping", "INFO", f"Вызов функции: {function_name} с параметрами: {params} и info: {info}")
        # Пример:
        if function_name == "open_site":
            url = params.get("url", "")
            if url:
                ControlSystem.open_site(url)
        elif function_name == "open_application":
            app_name = params.get("app_name", "")
            if app_name:
                ControlSystem.open_application(app_name)
        elif function_name == "close_application":
            app_name = params.get("app_name", "")
            if app_name:
                ControlSystem.close_application(app_name)
        elif function_name == "reload_application":
            app_name = params.get("app_name", "")
            if app_name:
                ControlSystem.reload_application(app_name)
        elif function_name == "close_current_tab":
            ControlSystem.close_current_tab()
        elif function_name == "set_brightness":
            level = params.get("level", 50)
            ControlSystem.set_brightness(level)
        elif function_name == "set_volume":
            level = params.get("level", 50)
            ControlSystem.set_volume(level)
        elif function_name == "os_sleep":
            ControlSystem.os_sleep()
        elif function_name == "os_shutdown":
            delay = params.get("delay", 0)
            ControlSystem.os_shutdown(delay)
        elif function_name == "os_restart":
            delay = params.get("delay", 0)
            ControlSystem.os_restart(delay)
        elif function_name == "cancel_shutdown":
            ControlSystem.cancel_shutdown()
        elif function_name == "connect_wifi":
            ssid = params.get("ssid_name", "")
            ControlSystem.connect_wifi(ssid)
        elif function_name == "disconnect_wifi":
            ControlSystem.disconnect_wifi()
        elif function_name == "set_airplane_mode":
            state = params.get("state", False)
            ControlSystem.set_airplane_mode(state)
        elif function_name == "empty_recycle_bin":
            ControlSystem.empty_recycle_bin()
        elif function_name == "insert_text":
            text = params.get("text", "")
            target_word = params.get("target_word", None)
            target_app = params.get("target_app", None)
            ControlSystem.insert_text(text, target_word, target_app)
    
    def send_ai_message(self, message: str):
        """Отправляет сообщение от AI в интерфейс с логированием"""
        BasicUtils.logger("CORE | AI Message", "INFO", f"AI: {message}")
        ui_signals.message_sent.emit("IAMOS", message)
        BasicUtils.add_message("IAMOS", message)
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
               1. Всё ок, включает Whisper -> Далее голосовой распознаватель как только распознает команду, создаёт сигнал
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
            self.control_whisper(True)
        else:
            BasicUtils.set_settings_config_value("recording_enabled", False)
            self.control_whisper(False)
    
    def control_whisper(self, new_status: bool):
        """Управление Whisper"""
        if new_status:
            self.whisper_model.start_recognition()
        else:
            self.whisper_model.stop_recognition()

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

    def on_message_sent(self, sender: str = "Unknown", message: str = "No message"):
        """Обработка сообщения пользователя: отправка в IntentHandler для анализа."""
        if sender != "user" or message == "No message":
            return

        BasicUtils.logger("CORE", "INFO", f"Пользователь: {message}")
        raw_history = BasicUtils.load_chat_history()
        formatted_history = BasicUtils.format_chat_history(raw_history)

        user_context = self.intent_handler.build_user_data(
            name=DATABASE_EDITOR.get_data("Users", "firstname", 0),
            birthday=DATABASE_EDITOR.get_data("Users", "birthday", 0),
            gender=DATABASE_EDITOR.get_data("Users", "gender", 0),
            chat_history=formatted_history,
            current_app=ControlSystem.get_active_app(),
            available_apps=ControlSystem.get_available_apps(),
        )
        use_online = BasicUtils.get_settings_config_value("use_online_model") and BasicUtils.has_internet()
        self.ai_thread = IntentWorker(self.intent_handler, message, user_context, use_online)

        self.ai_thread.finished.connect(self.handle_ai_result)
        self.ai_thread.error.connect(self.handle_error)
        self.ai_thread.start()

    def handle_ai_result(self, result):
        """Метод-обработчик успешного ответа"""
        self.handle_intent(result)

    
    def update_voice_recognition_model(self, new_model: str):
        """Функция, перезапускающая модель в реальном времени, если та включена"""
        if new_model != self.recognition_model:
            BasicUtils.logger("CORE | VoiceRecognitionModel", "INFO", f"Обновление модели распознавания голоса: {new_model}")
            self.recognition_model = new_model

            self.control_whisper(False)

            if BasicUtils.get_settings_config_value("recording_enabled"):
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
    api_key = BasicUtils.get_env_variable("OPENROUTER_API_KEY")
    assistent = AssistentCore(api_key)
    app.aboutToQuit.connect(assistent.intent_handler.shutdown_ollama)
    assistent.run()
    sys.exit(app.exec())