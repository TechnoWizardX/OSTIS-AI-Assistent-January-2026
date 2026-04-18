from UserInterface import UserInterface, ui_signals
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
import sys
import os
from datetime import datetime
VOICE_INPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'samples', 'VoiceInput'))
if VOICE_INPUT_DIR not in sys.path:
    sys.path.insert(0, VOICE_INPUT_DIR)
import threading
from BasicUtils import BasicUtils, DataBaseEditor, global_signals
import WhisperRecognition as Whisper
import voiceVosk  # ← ДОБАВЛЕН ИМПОРТ

DATABASE_EDITOR = DataBaseEditor()
# УДАЛЕНО: RECOGNITION_MODEL = "auto"  ← больше не нужен как глобальная переменная
print(f"📁 Текущая рабочая директория: {os.getcwd()}")
print(f"📁 Модель Vosk будет в: {os.path.abspath('./models/vosk-model-small-ru-0.22')}")
# Инициализация моделей (пути можно вынести в конфиг)
WHISPER_MODEL = Whisper.WhisperRecognition(model_download_root="./models")
VOSK_MODEL = voiceVosk.VoskRecognizer(model_path="./models/vosk-model-small-ru-0.22")

# УДАЛЕНО: лишняя инициализация потока — start_recognition() сам создаёт поток
# WHISPER_THREAD = threading.Thread(target=WHISPER_MODEL.start_recognition, daemon=True)


class AssistentCore():
    def __init__(self):
        self.user_interface = UserInterface()
        self.settings_config = BasicUtils.load_settings_config()
        
        # ← ГЛАВНОЕ ИЗМЕНЕНИЕ: инкапсулированная переменная
        self.recognition_model = self.settings_config.get("recognition_model", "auto")
        
        self.whisper_model = WHISPER_MODEL
        self.whisper_thread = None
        
        # Подписка на сигналы интерфейса
        ui_signals.message_sent.connect(self.on_message_sent)
        ui_signals.settings_changed.connect(self.on_settings_changed)
        ui_signals.voice_input_changed.connect(self.on_voice_input_changed)
        global_signals.voice_message_recognized.connect(self.voice_text_recived_core)

    def on_voice_input_changed(self, status):
        """Принимает status: True - включена, False - выключена."""
        BasicUtils.logger("VoiceInputChanged", "INFO", 
                         f"Статус голосового ввода (конфиг): {BasicUtils.get_settings_config_value('recording_enabled')}")
        BasicUtils.logger("VoiceInputChanged", "INFO", f"Получен статус: {status}")
        
        if status and BasicUtils.get_settings_config_value("recording_enabled"):
            # ← Используем self.recognition_model вместо глобальной переменной
            if self.recognition_model == "auto":
                best = self.check_best_voice_rec()  # Оптимизация: один вызов
                if best == "vosk":
                    self.control_vosk(True)
                elif best == "faster-whisper":
                    self.control_whisper(True)
            elif self.recognition_model == "vosk":
                self.control_vosk(True)  # ← Теперь работает, а не pass
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
            WHISPER_MODEL.start_recognition()
        else:
            WHISPER_MODEL.stop_recognition()
    
    def control_vosk(self, new_status: bool):
        """Управление Vosk (полный аналог control_whisper)"""
        if new_status:
            VOSK_MODEL.start_recognition()
        else:
            VOSK_MODEL.stop_recognition()
    
    def check_best_voice_rec(self) -> str:
        """Определяет лучший распознаватель для системы"""
        BasicUtils.logger("CheckBestVoiceRec", "INFO", "Проверка лучшего распознавания голоса...")
        # Здесь можно добавить реальную проверку (GPU, RAM, скорость)
        # Для примера возвращаем faster-whisper
        self.voice_recognizer = "faster-whisper"
        BasicUtils.logger("CheckBestVoiceRec", "INFO", 
                         f"Лучшее распознавание голоса: {self.voice_recognizer}")
        return self.voice_recognizer
   
    @staticmethod
    def on_message_sent(sender: str = "Unknown", message: str = "No Message"):
        """Обработка отправленного сообщения"""
        print(f"Message from {sender}: {message}")

    def on_settings_changed(self, new_settings: dict):
        """Реакция на изменение настроек"""
        self.settings_config = new_settings
        # ← Обновляем self.recognition_model при смене настроек
        if "recognition_model" in new_settings:
            self.recognition_model = new_settings["recognition_model"]
            BasicUtils.logger("SettingsChanged", "INFO", 
                             f"Модель распознавания изменена на: {self.recognition_model}")
        BasicUtils.logger("SettingsChanged", "INFO", f"Настройки обновлены: {new_settings}") 
    
    def voice_text_recived_core(self, text: str):
        """Приём распознанного текста и пересылка в интерфейс"""
        BasicUtils.logger("VoiceTextRecivedCore", "INFO", f"Распознан текст: {text}")
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