from .base_input_page import BaseInputPage
from src.gui import icon_path
from PyQt6.QtGui import QIcon
class TextPage(BaseInputPage):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Текстовый ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("text.png")))
        # Кнопка голоса не добавляется