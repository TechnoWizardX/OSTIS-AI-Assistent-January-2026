from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from dotenv import load_dotenv
from PySide6.QtCore import QCoreApplication, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication

from src.core.network_monitor import NetworkChecker
from src.gui.main_window import UserInterface
from src.gui.signals import ui_signals
from src.modules.well_being.usage_tracker import get_usage_tracker
from src.services.ai_service.intent_handler import IntentHandler, IntentWorker
from src.services.ai_service.llm_client import LocalModel
from src.services.ai_service.recommendation import (METHOD_LABELS,
                                                    AccessibilityRecommender)
from src.utils.BasicUtils import global_signals
from src.utils.chat_history import (add_message, clear_chat_history,
                                    format_chat_history,
                                    load_recent_chat_history)
from src.utils.config_manager import (ConfigManager, get_env_variable,
                                      get_settings_config_value,
                                      load_settings_config,
                                      set_settings_config_value)
from src.utils.database import DataBaseEditor
from src.utils.logger import logger
from src.utils.network import has_internet
from src.utils.system_control import ControlSystem
from src.utils.user_data import get_user_data_dir

if TYPE_CHECKING:
    from src.modules.voice.stt_engine import WhisperRecognition
    from src.modules.voice.tts_engine import SileroTTS

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv()
DATABASE_EDITOR = DataBaseEditor()
INTENT_HANDLER = IntentHandler(online_model="openrouter/free", base_url="https://openrouter.ai/api/v1")


class _ModelLoadingSignals(QObject):
    loaded = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.loaded.connect(self._on_loaded)
        self.failed.connect(self._on_failed)

    @Slot(str, object)
    def _on_loaded(self, model_name: str, model: object) -> None:
        self._owner._on_model_loaded(model_name, model)

    @Slot(str, str)
    def _on_failed(self, model_name: str, error: str) -> None:
        self._owner._on_model_load_failed(model_name, error)


class _IntentWorkerTracker(QObject):
    _worker_finished = Signal(object)

    def __init__(self):
        super().__init__()
        self._workers = set()
        self._worker_finished.connect(self._forget_worker)

    def track(self, worker: IntentWorker) -> None:
        self._workers.add(worker)
        worker.finished.connect(
            lambda worker=worker: self._worker_finished.emit(worker)
        )

    @Slot(object)
    def _forget_worker(self, worker: object) -> None:
        self._workers.discard(worker)

    def wait_for_all(self) -> None:
        for worker in tuple(self._workers):
            worker.wait()


class AssistentCore():
    def __init__(self, api_key: str = ""):
        logger("AssistentCore", "INFO", "Инициализация Ядра...")

        self.user_interface = UserInterface(api_key=api_key)
        self.settings_config = load_settings_config()
        self._shutting_down = False
        self._intent_worker_tracker = _IntentWorkerTracker()

        self.whisper_model: WhisperRecognition | None = None
        self.ttssilero_model: SileroTTS | None = None
        self._whisper_requested = False
        self._pending_tts: str | None = None
        self._model_load_threads: dict[str, threading.Thread] = {}
        self._model_loading_signals = _ModelLoadingSignals(self)

        # Учёт использования приложений для вкладки «Благополучие»
        self.usage_tracker = get_usage_tracker()
        self.usage_tracker.usage_flushed.connect(self._on_usage_flushed)
        self.usage_tracker.set_enabled(
            bool(get_settings_config_value("well_being_tracking_enabled"))
        )

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

        # Отдельный сигнал для получения рекомендации при сохранении нарушений
        ui_signals.recommendation_requested.connect(lambda: self.accessibility_advisor.request_recommendation(0))

        # Флаг: были ли отредактированы нарушения перед получением рекомендации
        self._dysfunctions_edited = False

        self.recognition_model = self.settings_config.get("recognition_model", "auto")

        self.tts_voice = get_settings_config_value("tts_voice")

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
            logger("AssistentCore", "WARNING", "Интернет отсутствует")
        else:
            logger("AssistentCore", "INFO", "Интернет подключён")

    def _on_usage_flushed(self, _date_str: str):
        """Сообщает интерфейсу, что статистика записана в БД."""
        ui_signals.app_usage_updated.emit()

    def _load_model_in_background(
        self,
        model_name: str,
        factory: Callable[[], object],
    ) -> None:
        if model_name in self._model_load_threads:
            return

        def load_model():
            try:
                model = factory()
            except Exception as error:
                logger(
                    "AssistentCore",
                    "ERROR",
                    f"Не удалось загрузить модель {model_name}: {error}",
                )
                if not self._shutting_down:
                    self._model_loading_signals.failed.emit(
                        model_name, str(error)
                    )
            else:
                if self._shutting_down:
                    self._dispose_loaded_model(model_name, model)
                else:
                    self._model_loading_signals.loaded.emit(model_name, model)

        thread = threading.Thread(
            target=load_model,
            name=f"{model_name}-model-loader",
            daemon=True,
        )
        self._model_load_threads[model_name] = thread
        thread.start()

    def _on_model_loaded(self, model_name: str, model: object) -> None:
        self._model_load_threads.pop(model_name, None)
        if self._shutting_down:
            self._dispose_loaded_model(model_name, model)
            return

        if model_name == "whisper":
            from src.modules.voice.stt_engine import WhisperRecognition

            if not isinstance(model, WhisperRecognition):
                self._report_model_error(model_name, "Некорректный экземпляр модели")
                return
            self.whisper_model = model
            if self._whisper_requested:
                try:
                    self.whisper_model.start_recognition()
                except Exception as error:
                    self._whisper_requested = False
                    self._report_model_error(model_name, error)
        elif model_name == "tts":
            from src.modules.voice.tts_engine import SileroTTS

            if not isinstance(model, SileroTTS):
                self._report_model_error(model_name, "Некорректный экземпляр модели")
                return
            self.ttssilero_model = model
            pending_text = self._pending_tts
            self._pending_tts = None
            if pending_text:
                self.text_to_speech(pending_text)

    def _on_model_load_failed(self, model_name: str, error: str) -> None:
        self._model_load_threads.pop(model_name, None)
        if self._shutting_down:
            return

        if model_name == "whisper":
            self._whisper_requested = False
        elif model_name == "tts":
            self._pending_tts = None
            ui_signals.speaker_stop_all.emit()
        self._report_model_error(model_name, error)

    @staticmethod
    def _dispose_loaded_model(model_name: str, model: object) -> None:
        if model_name == "tts":
            cleanup = getattr(model, "cleanup", None)
        else:
            cleanup = getattr(model, "stop_recognition", None)
        if callable(cleanup):
            try:
                cleanup()
            except Exception as error:
                logger(
                    "AssistentCore",
                    "ERROR",
                    f"Ошибка освобождения модели {model_name}: {error}",
                )

    def _report_model_error(self, model_name: str, error: object) -> None:
        message = f"Не удалось загрузить модель {model_name}: {error}"
        logger("AssistentCore", "ERROR", message)
        ui_signals.message_sent.emit("IAMOS", message)
        add_message("IAMOS", message)

    @staticmethod
    def _create_whisper_model() -> WhisperRecognition:
        from src.modules.voice.stt_engine import WhisperRecognition

        return WhisperRecognition(model_download_root=str(PROJECT_ROOT / "models"))

    @staticmethod
    def _create_tts_model() -> SileroTTS:
        from src.modules.voice.tts_engine import SileroTTS

        return SileroTTS()

    def _on_dysfunctions_saved(self):
        """Обработка сигнала о сохранении нарушений."""
        self._dysfunctions_edited = True
        logger("AssistentCore", "INFO", "Нарушения отредактированы, следующая рекомендация будет озвучена")

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
        tts_recommendation_always = get_settings_config_value("tts_recommendation_always")
        if tts_recommendation_always and self._dysfunctions_edited:
            logger("AssistentCore | Recommendation", "INFO", "Озвучивание рекомендации")
            self.text_to_speech(formatted_text)
            self._dysfunctions_edited = False

    def handle_intent(self, intent_data: dict):
        """Обработка распознанного интента от IntentHandler и выполнение соответствующих действий"""
        message = intent_data.get("message", "")
        tasks = intent_data.get("tasks", [])
        logger("CORE | IntentHandler", "INFO", f"Получен интент: {intent_data}")

        # Проверяем, пустой ли ответ от ИИ
        if not message or not message.strip():
            # Получаем состояние переключателя авто-озвучки
            auto_tts_enabled = get_settings_config_value("auto_tts")
            # Формируем сообщение о состоянии
            status_message = "Пустой ответ от ИИ"
            # Пишем сообщение в чат
            self.send_ai_message(status_message)
            # Озвучиваем состояние
            tts_recommendation_always = get_settings_config_value("tts_recommendation_always")
            if tts_recommendation_always and self._dysfunctions_edited:
                self.text_to_speech(status_message)
            logger("CORE | IntentHandler", "INFO", f"Пустой ответ от ИИ. Состояние auto_tts: {auto_tts_enabled}")
        else:
            self.send_ai_message(message)
        for task in tasks:
            function = task.get("function", "")
            params = task.get("params", {})
            info = task.get("info", "")
            self.actions_mapping(function, params, info)
    def actions_mapping(self, function_name: str, params: dict, info: str):
        """Здесь будет логика сопоставления имен функций к реальным функциям в коде"""
        logger("CORE | ActionsMapping", "INFO", f"Вызов функции: {function_name} с параметрами: {params} и info: {info}")
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
                logger("CORE | ActionsMapping", "WARNING", f"Неизвестная функция: {function_name}")
        except Exception as e:
            logger("CORE | ActionsMapping", "ERROR", f"Ошибка при выполнении функции {function_name}: {e}")
            global_signals.error_signal.emit(f"Не удалось выполнить функцию {function_name}: {e}")

    def send_ai_message(self, message: str):
        """Отправляет сообщение от AI в интерфейс с логированием"""
        logger("CORE | AI Message", "INFO", f"AI: {message}")
        ui_signals.message_sent.emit("IAMOS", message)
        add_message("IAMOS", message)
        if get_settings_config_value("auto_tts"):
            logger("CORE | AI Message", "INFO", "Автоматическая озвучка включена, отправляем сообщение в TTS")
            self.text_to_speech(message)

    def handle_error(self, error_message: str):
        """Обработка ошибок, полученных из разных частей системы, с логированием"""
        if self._shutting_down:
            return
        ui_signals.typing_finished.emit()
        self.text_to_speech(error_message)

    def clear_chat_history(self):
        """Очищает историю чата через BasicUtils с логированием"""
        logger("CORE | ClearHistory", "INFO", "Запрошена очистка истории чата")
        try:
            clear_chat_history()  # новый метод из BasicUtils
            logger("CORE | ClearHistory", "INFO", "История чата успешно очищена")
            ui_signals.history_cleared.emit()
        except Exception as e:
            logger("CORE | ClearHistory", "ERROR", f"Ошибка при очистке истории: {e}")
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
        logger("CORE | VoiceInputChanged", "INFO", f"Статус голосового ввода (конфиг): {get_settings_config_value('recording_enabled')}")
        logger("CORE | VoiceInputChanged", "INFO", f"Получен статус: {status}")
        if status and get_settings_config_value("recording_enabled"):
            self.control_whisper(True)
        else:
            set_settings_config_value("recording_enabled", False)
            self.control_whisper(False)

    def control_whisper(self, new_status: bool):
        """Управление Whisper"""
        if self._shutting_down:
            return
        self._whisper_requested = new_status
        if new_status:
            if self.whisper_model is None:
                self._load_model_in_background(
                    "whisper",
                    self._create_whisper_model,
                )
            else:
                self.whisper_model.start_recognition()
        elif self.whisper_model is not None:
            self.whisper_model.stop_recognition()

    def text_to_speech(self, text: str):
        """Преобразование текста в речь с выбором модели TTS в зависимости от настроек"""
        if self._shutting_down or not text or not text.strip():
            return
    
        # Останавливаем предыдущее воспроизведение и сбрасываем все кнопки
        self.stop_speech()

        if self.ttssilero_model is None:
            self._pending_tts = text
            self._load_model_in_background("tts", self._create_tts_model)
            return
    
        # Получаем настройки
        tts_speed = get_settings_config_value("tts_speed")
        tts_model = get_settings_config_value("tts_model")
        tts_voice = get_settings_config_value("tts_voice")
    
        # Словарь с доступными TTS моделями
        tts_engines = {
            "silero": self.ttssilero_model,
            # тут могут быть другие модели по аналогии с silero
        }
    
        # Выбираем нужную модель или используем Silero по умолчанию
        tts_engine = tts_engines.get(tts_model, self.ttssilero_model)
    
        if tts_model != "silero" and tts_model not in tts_engines:
            logger("CORE | TTS", "WARNING", f"Неизвестная модель TTS: {tts_model}, используем Silero")
    
        logger("CORE | TTS", "INFO", f"TTS: модель={tts_model}, голос={tts_voice}, скорость={tts_speed}")
    
        # Функция обратного вызова по окончании воспроизведения
        def on_finished():
            logger("CORE | TTS", "INFO", "Воспроизведение завершено")
            ui_signals.speaker_finished.emit()
    
        # Запускаем асинхронное воспроизведение с callback
        if hasattr(tts_engine, 'speak_async'):
            tts_engine.speak_async(text, tts_voice, tts_speed, callback=on_finished)
        else:
            # fallback на обычный speak (без callback)
            tts_engine.speak(text, tts_voice, tts_speed)
            # В этом случае кнопка не сбросится автоматически, но можно запустить таймер
            logger("CORE | TTS", "WARNING", "Модель TTS не поддерживает speak_async, кнопка не сбросится автоматически")

    def stop_speech(self):
        """Останавливает текущее воспроизведение речи и сбрасывает кнопки."""
        self._pending_tts = None
        if self.ttssilero_model is None:
            ui_signals.speaker_stop_all.emit()
            return

        if hasattr(self.ttssilero_model, 'stop'):
            self.ttssilero_model.stop()
            logger("CORE | TTS", "INFO", "Воспроизведение остановлено пользователем")
            # Сбрасываем все кнопки динамиков
            ui_signals.speaker_stop_all.emit()
        else:
            logger("CORE | TTS", "WARNING", "Модель TTS не поддерживает остановку")

    def on_message_sent(self, sender: str = "Unknown", message: str = "No message"):
        """Обработка сообщения пользователя: отправка в IntentHandler для анализа."""
        if self._shutting_down or sender != "user" or message == "No message":
            return
    
        logger("CORE", "INFO", f"Пользователь: {message}")
        recent_history = load_recent_chat_history(10)
        formatted_history = format_chat_history(recent_history, 10)
    
        use_online = get_settings_config_value("use_online_model") and has_internet()
        if use_online:
            logger("CORE", "INFO", "Использование облачного ИИ для обработки запроса")
            if get_settings_config_value("allow_online_model_user_info"):
                logger("CORE", "INFO", "Разрешён доступ облачному ИИ к персональным данным")
                user_context = self.intent_handler.build_user_data(
                    name=DATABASE_EDITOR.get_data("Users", "firstname", 0),
                    birthday=DATABASE_EDITOR.get_data("Users", "birthday", 0),
                    gender=DATABASE_EDITOR.get_data("Users", "gender", 0),
                    chat_history=formatted_history,
                    current_app=ControlSystem.get_active_app(),
                    available_apps=ControlSystem.get_available_apps(),
                )
            else:
                logger("CORE", "INFO", "Доступ облачному ИИ к персональным данным запрещён")
                user_context = self.intent_handler.build_user_data(
                    chat_history=formatted_history,
                    current_app=ControlSystem.get_active_app(),
                    available_apps=ControlSystem.get_available_apps(),
                )
        else:
            logger("CORE", "INFO", "Использование локального ИИ для обработки запроса")
            user_context = self.intent_handler.build_user_data(
                    name=DATABASE_EDITOR.get_data("Users", "firstname", 0),
                    birthday=DATABASE_EDITOR.get_data("Users", "birthday", 0),
                    gender=DATABASE_EDITOR.get_data("Users", "gender", 0),
                    chat_history=formatted_history,
                    current_app=ControlSystem.get_active_app(),
                    available_apps=ControlSystem.get_available_apps(),
                )
        self.ai_thread = IntentWorker(handler=self.intent_handler, user_text=message, user_data=user_context, use_online = use_online)
        self._intent_worker_tracker.track(self.ai_thread)
    
        self.ai_thread.result_ready.connect(self.handle_ai_result)
        self.ai_thread.error.connect(self.handle_error)
        self.ai_thread.start()
        ui_signals.typing_started.emit()

    def handle_ai_result(self, result):
        """Метод-обработчик успешного ответа"""
        if self._shutting_down:
            return
        ui_signals.typing_finished.emit()
        self.handle_intent(result)


    def update_voice_recognition_model(self, new_model: str):
        """Функция, перезапускающая модель в реальном времени, если та включена"""
        if new_model != self.recognition_model:
            logger("CORE | VoiceRecognitionModel", "INFO", f"Обновление модели распознавания голоса: {new_model}")
            self.recognition_model = new_model

            self.control_whisper(False)

            if get_settings_config_value("recording_enabled"):
                self.control_whisper(True)

    def on_settings_changed(self, new_settings: dict):
        logger("CORE | SettingsConfiguration", "INFO", f"Настройки конфигурации обновлены: {new_settings}")
        if "recognition_model" in new_settings:
            self.update_voice_recognition_model(new_settings["recognition_model"])

    def voice_text_recived_core(self, text: str):
        """Приём распознанного текста и пересылка в интерфейс"""
        logger("CORE | VoiceTextRecivedCore", "INFO", f"Распознан текст: {text}")
        ui_signals.voice_message_received.emit(text)

    def run(self):
        """Запуск интерфейса"""
        self.user_interface.show()

    def shutdown(self) -> None:
        """Stop background work before the Qt application exits."""
        if self._shutting_down:
            return

        self._shutting_down = True
        self._whisper_requested = False
        self._pending_tts = None

        self._cleanup_step(
            "gesture camera",
            self.user_interface.gestures_input_page.stop_camera,
        )
        if self.whisper_model is not None:
            self._cleanup_step(
                "Whisper listener", self.whisper_model.stop_recognition
            )
        if self.ttssilero_model is not None:
            self._cleanup_step("TTS worker", self.ttssilero_model.cleanup)

        self._cleanup_step("network monitor", self.network_checker.stop)
        self._cleanup_step("usage tracker", self.usage_tracker.stop)
        self._cleanup_step(
            "recommendation worker", self.accessibility_advisor.shutdown
        )
        self._cleanup_step(
            "intent workers", self._intent_worker_tracker.wait_for_all
        )

        for thread in tuple(self._model_load_threads.values()):
            thread.join()
        QCoreApplication.processEvents()
        self._model_load_threads.clear()

        self._cleanup_step("Ollama", self.intent_handler.shutdown_ollama)
        logger("AssistentCore", "INFO", "Фоновые ресурсы остановлены")

    @staticmethod
    def _cleanup_step(name: str, cleanup: Callable[[], object]) -> None:
        try:
            cleanup()
        except Exception as error:
            logger(
                "AssistentCore",
                "ERROR",
                f"Ошибка при завершении {name}: {error}",
            )


def run_core():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("IAMOS")
    get_user_data_dir()
    ConfigManager.init_config()
    app.setStyle("Fusion")
    api_key = get_env_variable("OPENROUTER_API_KEY")
    assistent = AssistentCore(api_key=api_key)
    app.aboutToQuit.connect(assistent.shutdown)
    assistent.run()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_core()
