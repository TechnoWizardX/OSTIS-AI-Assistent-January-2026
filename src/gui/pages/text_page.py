from .base_input_page import BaseInputPage
from src.utils.icons import set_theme_icon
class TextPage(BaseInputPage):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Текстовый ввод")
        set_theme_icon(self.side_panel_btn, "text.svg")
        # Кнопка голоса не добавляется