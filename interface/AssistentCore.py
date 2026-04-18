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
        self.recognition_model = RECOGNITION_MODEL
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
        BasicUtils.logger("CORE | VoiceInputChanged", "INFO", f"Статус голосового ввода (конфиг): {BasicUtils.get_settings_config_value("recording_enabled")}")
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
            BasicUtils.set_settings_config_value("recording_enabled", False)
            self.control_whisper(False)
            self.control_vosk(False)
    
    def control_whisper(self, new_status: bool):
        if new_status:
            # Просто вызываем метод, он сам создаст фоновый процесс
            self.whisper_model.start_recognition()
        else:
            # Это мгновенно прикажет фоновому потоку перестать слушать
            self.whisper_model.stop_recognition()
    
    def control_vosk(self, new_status: bool):
        pass
    def check_best_voice_rec(self) -> str:
        BasicUtils.logger("CORE | CheckBestVoiceRec", "INFO", "Проверка лучшего распознавания голоса для системы...")
        BasicUtils.logger("CORE | CheckBestVoiceRec", "INFO", "Проверка Vosk...")
        # Здесь должна быть реальная проверка, но для примера просто вернем faster-whisper
        BasicUtils.logger("CORE | CheckBestVoiceRecCORE", "INFO", "Проверка Whisper...")
        # Здесь должна быть реальная проверка, но для примера просто вернем faster-whisper

        self.recognition_model = "faster-whisper"
        BasicUtils.logger("CORE | CheckBestVoiceRec", "INFO", f"Лучшее распознавание голоса: {self.recognition_model}")
        return self.recognition_model
   
   

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
        BasicUtils.logger("CORE | VoiceTextRecivedCore", "INFO", f"Распознан текст: {text}")
        ui_signals.voice_message_received.emit(text)

    
    def run(self):
        self.user_interface.show()
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    assistent = AssistentCore()
    assistent.run()
    sys.exit(app.exec())