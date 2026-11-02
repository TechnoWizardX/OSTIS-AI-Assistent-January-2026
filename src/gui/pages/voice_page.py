from .base_input_page import BaseInputPage
from src.utils.icons import set_theme_icon

class VoicePage(BaseInputPage):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Голосовой ввод")
        set_theme_icon(self.side_panel_btn, "microphone.svg")
        self.send_box.addVoiceButton()   # добавляем кнопку голоса
        self.send_box.showVoiceButton()