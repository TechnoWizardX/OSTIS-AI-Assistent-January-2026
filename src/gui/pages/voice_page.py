from .base_input_page import BaseInputPage
from src.gui import icon_path
from PyQt6.QtGui import QIcon

class VoicePage(BaseInputPage):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Голосовой ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("microphone.png")))
        self.send_box.addVoiceButton()   # добавляем кнопку голоса
        self.send_box.showVoiceButton()