from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from src.gui.pages.base_page import ContentPageWidget
from src.gui.widgets.chat_send_box import ChatSendBox


class BaseInputPage(ContentPageWidget):
    def __init__(self):
        super().__init__()
        # Общий чат (один DialogBox на все страницы ввода) подключается
        # извне через attach_chat; здесь только плейсхолдер под него
        self.dialog_box = None
        self._chat_placeholder = None
        self._chat_sizes: list[int] = []
        self.send_box = ChatSendBox()
        self._setup_layout()

    def _setup_layout(self):
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical)
        # Плейсхолдер держит пропорции сплиттера до подключения общего чата
        self._chat_placeholder = QWidget()
        self._chat_placeholder.setMinimumHeight(200)
        self.chat_splitter.addWidget(self._chat_placeholder)
        self.chat_splitter.addWidget(self.send_box)
        self.chat_splitter.setSizes([400, 200])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chat_splitter)
        self.setLayout(layout)

    def attach_chat(self, dialog_box):
        """Помещает общий чат в сплиттер страницы.

        Виджет перекидывается с предыдущей страницы (репарентинг),
        поэтому во всём приложении существует один экземпляр чата.
        """
        if self.dialog_box is dialog_box and dialog_box.parentWidget() is self.chat_splitter:
            return  # уже подключён к этой странице
        self.dialog_box = dialog_box
        dialog_box.setParent(None)

        # Плейсхолдер больше не нужен: состав сплиттера стабилен [чат, send_box]
        if self._chat_placeholder is not None:
            self._chat_placeholder.setParent(None)
            self._chat_placeholder.deleteLater()
            self._chat_placeholder = None

        self.chat_splitter.insertWidget(0, dialog_box)
        # Восстанавливаем пропорции, сохранённые при уходе со страницы
        if len(self._chat_sizes) == self.chat_splitter.count():
            self.chat_splitter.setSizes(self._chat_sizes)
        else:
            # Первый показ: чату ~60% высоты (абсолютные значения —
            # QSplitter игнорирует относительные веса вроде [2, 1])
            total = max(1, sum(self.chat_splitter.sizes()))
            chat_share = max(200, int(total * 0.6))
            self.chat_splitter.setSizes([chat_share, total - chat_share])
        dialog_box.show()

    def hideEvent(self, event):
        # Запоминаем пропорции сплиттера, чтобы вернуть их при возврате
        if self.dialog_box is not None:
            self._chat_sizes = self.chat_splitter.sizes()
        super().hideEvent(event)
