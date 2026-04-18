from UserInterface import UserInterface, ui_signals
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
import sys
from datetime import datetime
import threading
from BasicUtils import BasicUtils, DataBaseEditor, global_signals
import WhisperRecognition as Whisper
DATABASE_EDITOR = DataBaseEditor()
RECOGNITION_MODEL = "auto"
WHISPER_MODEL = Whisper.WhisperRecognition(model_download_root="./models")
WHISPER_THREAD = threading.Thread(target=WHISPER_MODEL.start_recognition, daemon=True)

class AssistentCore():
    def __init__(self):
        
        self.user_interface = UserInterface()
        self.settings_config = BasicUtils.load_settings_config()
        self.whisper_model = WHISPER_MODEL
        self.whisper_thread = None
        ui_signals.message_sent.connect(self.on_message_sent)
        ui_signals.settings_changed.connect(self.on_settings_changed)
        ui_signals.voice_input_changed.connect(self.on_voice_input_changed)
        global_signals.voice_message_recognized.connect(self.voice_text_recived_core)

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
        BasicUtils.logger("VoiceInputChanged", "INFO", f"Статус голосового ввода (конфиг): {BasicUtils.get_settings_config_value("recording_enabled")}")
        BasicUtils.logger("VoiceInputChanged", "INFO", f"Получен статус: {status}")
        if status and BasicUtils.get_settings_config_value("recording_enabled"):
            RECOGNITION_MODEL = BasicUtils.get_settings_config_value("recognition_model")
            if RECOGNITION_MODEL == "auto":
                if self.check_best_voice_rec() == "vosk":
                    self.start_vosk()
                elif self.check_best_voice_rec() == "faster-whisper":
                    self.control_whisper(True)
            elif RECOGNITION_MODEL == "vosk":
                pass
            elif RECOGNITION_MODEL == "faster-whisper":
                self.control_whisper(True)
        else:
            BasicUtils.set_settings_config_value("recording_enabled", False)
            self.control_whisper(False)
    
    def control_whisper(self, new_status: bool):
        if new_status:
            # Просто вызываем метод, он сам создаст фоновый процесс
            WHISPER_MODEL.start_recognition()
        else:
            # Это мгновенно прикажет фоновому потоку перестать слушать
            WHISPER_MODEL.stop_recognition()
    
    def start_vosk(self):
        pass
    def check_best_voice_rec(self) -> str:
        BasicUtils.logger("CheckBestVoiceRec", "INFO", "Проверка лучшего распознавания голоса для системы...")
        BasicUtils.logger("CheckBestVoiceRec", "INFO", "Проверка Vosk...")
        # Здесь должна быть реальная проверка, но для примера просто вернем faster-whisper
        BasicUtils.logger("CheckBestVoiceRec", "INFO", "Проверка Whisper...")
        # Здесь должна быть реальная проверка, но для примера просто вернем faster-whisper
        self.voice_recognizer = "faster-whisper"
        BasicUtils.logger("CheckBestVoiceRec", "INFO", f"Лучшее распознавание голоса: {self.voice_recognizer}")
        return self.voice_recognizer
   
   
    @staticmethod
    def on_message_sent(self, sender : str = "Unknown", message : str = "No Message"):
        print(f"Message from {sender}: {message}")

    def on_settings_changed(self, new_settings: dict):
        self.settings_config = new_settings

        BasicUtils.logger("SettingsChanged", "INFO", f"Настройки конфигурации обновлены: {new_settings}") 
    
    def voice_text_recived_core(self, text: str):
        BasicUtils.logger("VoiceTextRecivedCore", "INFO", f"Распознан текст: {text}")
        ui_signals.voice_message_received.emit(text)

    
    def run(self):
        self.user_interface.show()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    assistent = AssistentCore()
    assistent.run()
    sys.exit(app.exec())