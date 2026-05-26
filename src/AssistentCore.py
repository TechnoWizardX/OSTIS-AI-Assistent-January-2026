from src.gui.userinterface import UserInterface, ui_signals
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
from src.utils.BasicUtils import BasicUtils, DataBaseEditor, global_signals
import VoiceInput.WhisperRecognition as Whisper
from TTSSilero import SileroTTS
from ai_services.services import NetworkChecker, LocalModel
from ai_services.accessibility_recommender import AccessibilityRecommender, RecommendationParser, METHOD_LABELS
from IntentHandler import IntentHandler, IntentWorker
from dotenv import load_dotenv
from SystemControl import ControlSystem
load_dotenv()
DATABASE_EDITOR = DataBaseEditor()
WHISPER_MODEL = Whisper.WhisperRecognition(model_download_root="./models")
TTSSILERO_MODEL = SileroTTS()
INTENT_HANDLER = IntentHandler(online_model="poolside/laguna-xs.2:free", base_url="https://openrouter.ai/api/v1")

class AssistentCore():
    def __init__(self, api_key: str = ""):
        BasicUtils.logger("AssistentCore", "INFO", "Инициализация Ядра...")
        self.user_interface = UserInterface(api_key=api_key)
        self.settings_config = BasicUtils.load_settings_config()
        
        self.network_checker = NetworkChecker()
        self.network_checker.connection_changed.connect(self._on_network_status)
        self.network_checker.start()

        # Локальная модель 
        self.local_model = LocalModel()
        self.active_model = self.local_model
        self.current_worker = None

        # Инициализация рекомендателя (рекомендации отправляются только в профиль)
        self.accessibility_advisor = AccessibilityRecommender()
        # Подключаем сигнал рекомендателя к сигналу интерфейса для обновления профиля
        # accessibility_advisor передаёт (methods, text), recommendation_ready принимает то же
        # Форматируем текст рекомендации перед отправкой в интерфейс
        self.accessibility_advisor.recommendation_obtained.connect(
            self._on_recommendation_obtained
        )

        # Автозапуск при каждом сохранении профиля
        ui_signals.profile_updated.connect(lambda: self.accessibility_advisor.request_recommendation(0))
        
        # Флаг: были ли отредактированы нарушения перед получением рекомендации
        self._dysfunctions_edited = False

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
        ui_signals.dysfunctions_saved.connect(self._on_dysfunctions_saved)
   
    def _on_network_status(self, online: bool):
        """Обработка статуса сети (для информации)."""
        if not online:
            BasicUtils.logger("AssistentCore", "WARNING", "Интернет отсутствует")
        else:
            BasicUtils.logger("AssistentCore", "INFO", "Интернет подключён")

    def _on_dysfunctions_saved(self):
        """Обработка сигнала о сохранении нарушений."""
        self._dysfunctions_edited = True
        BasicUtils.logger("AssistentCore", "INFO", "Нарушения отредактированы, следующая рекомендация будет озвучена")

    def _on_recommendation_obtained(self, methods: list, text: str):
        """
        Обработка полученной рекомендации.
        """
        # 1. Форматируем текст (замена RecommendationFormatter)
        if methods:
            readable_names = [METHOD_LABELS.get(m, m) for m in methods]
            formatted_text = f"Рекомендуемые методы ввода: {', '.join(readable_names)}\n\n{text}"
        else:
            formatted_text = text

        # 2. Отправляем в интерфейс
        ui_signals.recommendation_ready.emit(methods, formatted_text)

        # 3. Озвучка (ваша существующая логика)
        tts_recommendation_always = BasicUtils.get_settings_config_value("tts_recommendation_always")
        if tts_recommendation_always and self._dysfunctions_edited:
            BasicUtils.logger("AssistentCore | Recommendation", "INFO", "Озвучивание рекомендации")
            self.text_to_speech(formatted_text)
        
        self._dysfunctions_edited = False

    def handle_intent(self, intent_data: dict):
        """Обработка распознанного интента от IntentHandler и выполнение соответствующих действий"""
        message = intent_data.get("message", "")
        tasks = intent_data.get("tasks", [])
        BasicUtils.logger("CORE | IntentHandler", "INFO", f"Получен интент: {intent_data}")

        # Проверяем, пустой ли ответ от ИИ
        if not message or not message.strip():
            # Получаем состояние переключателя авто-озвучки
            auto_tts_enabled = BasicUtils.get_settings_config_value("auto_tts")
            # Формируем сообщение о состоянии
            status_message = "Пустой ответ от ИИ"
            # Пишем сообщение в чат
            self.send_ai_message(status_message)
            # Озвучиваем состояние
            tts_recommendation_always = BasicUtils.get_settings_config_value("tts_recommendation_always")
            if tts_recommendation_always and self._dysfunctions_edited:
                self.text_to_speech(status_message)
            BasicUtils.logger("CORE | IntentHandler", "INFO", f"Пустой ответ от ИИ. Состояние auto_tts: {auto_tts_enabled}")
        else:
            self.send_ai_message(message)
        for task in tasks:
            function = task.get("function", "")
            params = task.get("params", {})
            info = task.get("info", "")
            self.actions_mapping(function, params, info)
    def actions_mapping(self, function_name: str, params: dict, info: str):
        """Здесь будет логика сопоставления имен функций к реальным функциям в коде"""
        BasicUtils.logger("CORE | ActionsMapping", "INFO", f"Вызов функции: {function_name} с параметрами: {params} и info: {info}")
        methods = {
            # 1. БРАУЗЕР
            "open_site": lambda: ControlSystem.open_site(params.get("url", "")),
            "close_current_tab": ControlSystem.close_current_tab,

            # 2. ПРИЛОЖЕНИЯ И ОКНА
            "open_application": lambda: ControlSystem.open_application(params.get("app_name", "")),
            "close_application": lambda: ControlSystem.close_application(params.get("app_name", "")),
            "reload_application": lambda: ControlSystem.reload_application(params.get("app_name", "")),
            "minimize_all_windows": ControlSystem.minimize_all_windows,
            "toggle_always_on_top": ControlSystem.toggle_always_on_top,
            "set_window_state": lambda: ControlSystem.set_window_state(params.get("action", "restore")),
            "set_window_transparency": lambda: ControlSystem.set_window_transparency(params.get("alpha", 255)),
            "snap_window": lambda: ControlSystem.snap_window(params.get("side", "left")),

            # 3. ПАРАМЕТРЫ СИСТЕМЫ
            "set_brightness": lambda: ControlSystem.set_brightness(params.get("level", 50)),
            "set_volume": lambda: ControlSystem.set_volume(params.get("level", 50)),

            # 4. ПИТАНИЕ ПК
            "os_sleep": ControlSystem.os_sleep,
            "os_shutdown": lambda: ControlSystem.os_shutdown(params.get("delay", 60)),
            "cancel_shutdown": ControlSystem.cancel_shutdown,
            "os_restart": lambda: ControlSystem.os_restart(params.get("delay", 0)),

            # 5. СЕРВИСНЫЕ
            "insert_text": lambda: ControlSystem.insert_text(
                params.get("text", ""),
                params.get("target_word"),
                params.get("target_app")
            ),
            "empty_recycle_bin": ControlSystem.empty_recycle_bin,
            "get_system_stats": ControlSystem.get_system_stats,
            "disconnect_wifi": ControlSystem.disconnect_wifi,
            "connect_wifi": lambda: ControlSystem.connect_wifi(params.get("ssid_name")),
            "set_airplane_mode": lambda: ControlSystem.set_airplane_mode(params.get("state", False)),
            "create_quick_note": lambda: ControlSystem.create_quick_note(
                params.get("content", ""),
                params.get("filename", "note.txt")
            ),
            "open_directory": lambda: ControlSystem.open_directory(params.get("path_type", "desktop")),
            "take_screenshot": lambda: ControlSystem.take_screenshot(params.get("name")),
            "media_control": lambda: ControlSystem.media_control(params.get("action", "play"))
        }
        try:
            if function_name in methods:
                methods[function_name]()
            else:
                BasicUtils.logger("CORE | ActionsMapping", "WARNING", f"Неизвестная функция: {function_name}")
        except Exception as e:
            BasicUtils.logger("CORE | ActionsMapping", "ERROR", f"Ошибка при выполнении функции {function_name}: {e}")
            global_signals.error_signal.emit(f"Не удалось выполнить функцию {function_name}: {e}")
    
    def send_ai_message(self, message: str):
        """Отправляет сообщение от AI в интерфейс с логированием"""
        BasicUtils.logger("CORE | AI Message", "INFO", f"AI: {message}")
        ui_signals.message_sent.emit("IAMOS", message)
        BasicUtils.add_message("IAMOS", message)
        if BasicUtils.get_settings_config_value("auto_tts"):
            BasicUtils.logger("CORE | AI Message", "INFO", "Автоматическая озвучка включена, отправляем сообщение в TTS")
            self.text_to_speech(message)
    
    def handle_error(self, error_message: str):
        """Обработка ошибок, полученных из разных частей системы, с логированием"""
        ui_signals.typing_finished.emit()
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
        formatted_history = BasicUtils.format_chat_history(raw_history, 10)

        use_online = BasicUtils.get_settings_config_value("use_online_model") and BasicUtils.has_internet()
        if use_online:
            BasicUtils.logger("CORE", "INFO", "Использование облачного ИИ для обработки запроса")
            if BasicUtils.get_settings_config_value("allow_online_model_user_info"):
                BasicUtils.logger("CORE", "INFO", "Разрешён доступ облачному ИИ к персональным данным")
                user_context = self.intent_handler.build_user_data(
                    name=DATABASE_EDITOR.get_data("Users", "firstname", 0),
                    birthday=DATABASE_EDITOR.get_data("Users", "birthday", 0),
                    gender=DATABASE_EDITOR.get_data("Users", "gender", 0),
                    chat_history=formatted_history,
                    current_app=ControlSystem.get_active_app(),
                    available_apps=ControlSystem.get_available_apps(),
                )
            else:
                BasicUtils.logger("CORE", "INFO", "Доступ облачному ИИ к персональным данным запрещён")
                user_context = self.intent_handler.build_user_data(
                    chat_history=formatted_history,
                    current_app=ControlSystem.get_active_app(),
                    available_apps=ControlSystem.get_available_apps(),
                )
        else:
            BasicUtils.logger("CORE", "INFO", "Использование локального ИИ для обработки запроса")
            user_context = self.intent_handler.build_user_data(
                    name=DATABASE_EDITOR.get_data("Users", "firstname", 0),
                    birthday=DATABASE_EDITOR.get_data("Users", "birthday", 0),
                    gender=DATABASE_EDITOR.get_data("Users", "gender", 0),
                    chat_history=formatted_history,
                    current_app=ControlSystem.get_active_app(),
                    available_apps=ControlSystem.get_available_apps(),
                )
        self.ai_thread = IntentWorker(handler=self.intent_handler, user_text=message, user_data=user_context, use_online = use_online)

        self.ai_thread.finished.connect(self.handle_ai_result)
        self.ai_thread.error.connect(self.handle_error)
        self.ai_thread.start()
        ui_signals.typing_started.emit()

    def handle_ai_result(self, result):
        """Метод-обработчик успешного ответа"""
        ui_signals.typing_finished.emit()
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
        
def run_core():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    api_key = BasicUtils.get_env_variable("OPENROUTER_API_KEY")
    assistent = AssistentCore(api_key)
    app.aboutToQuit.connect(assistent.intent_handler.shutdown_ollama)
    assistent.run()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_core()