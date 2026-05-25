from PyQt6.QtWidgets import (QVBoxLayout,QSplitter
)
from PyQt6.QtCore import Qt
from .base_page import ContentPageWidget
from ..widgets.chat_dialog import DialogBox
from ..widgets.chat_send_box import ChatSendBox
class BaseInputPage(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.dialog_box = DialogBox()
        self.send_box = ChatSendBox()
        self._setup_layout()

    def _setup_layout(self):
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat_splitter.addWidget(self.dialog_box)
        self.chat_splitter.addWidget(self.send_box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chat_splitter)
        self.setLayout(layout)

    def _apply_theme(self, theme):
        super()._apply_theme(theme)
        self.dialog_box._apply_theme(theme)
        self.send_box._apply_theme(theme)