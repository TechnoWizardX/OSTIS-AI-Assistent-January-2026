from UserInterface import UserInterface
from PyQt6.QtWidgets import QApplication
import sys

class AssistentCore():
    def __init__(self):
        self.user_interface = UserInterface()
        self.user_interface.signals.message_sent.connect(self.on_message_sent)
        self.user_interface.signals.settings_changed.connect(self.on_settings_changed)

    def on_message_sent(self, sender, message):
        print(f"Message from {sender}: {message}")

    def run(self):
        self.user_interface.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    window.show()
    sys.exit(app.exec())