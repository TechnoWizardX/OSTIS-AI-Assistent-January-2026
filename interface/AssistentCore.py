from UserInterface import UserInterface, global_signals
from PyQt6.QtWidgets import QApplication
import sys
from BasicUtils import BasicUtils, DataBaseEditor
DATABASE_EDITOR = DataBaseEditor()
class AssistentCore():
    def __init__(self):
        self.user_interface = UserInterface()
        global_signals.message_sent.connect(self.on_message_sent)
        global_signals.settings_changed.connect(self.on_settings_changed)
        global_signals.voice_text_received.connect(self.voice_text_recived_core)
    def on_message_sent(self, sender : str = "Unknown", message : str = "No Message"):
        print(f"Message from {sender}: {message}")

    def on_settings_changed(self):
        print("Settings changed")   
    def run(self):
        self.user_interface.show()

    def voice_text_recived_core(str):
        print(f"Voice text received: {str}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    assistent = AssistentCore()
    assistent.run()
    sys.exit(app.exec())