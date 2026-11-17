from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QPushButton, QScrollArea, QVBoxLayout,
                             QWidget)

from src.gui.signals import ui_signals
from src.gui.widgets.message_item import Message
from src.gui.widgets.typing_indicator import TypingIndicator
from src.utils.chat_history import load_chat_history_page

HISTORY_PAGE_SIZE = 30


class DialogBox(QWidget):
    """Чат (здесь отображаются сообщения)"""

    PAGE_SIZE = HISTORY_PAGE_SIZE

    def __init__(self):
        super().__init__()
        # Сплиттер не должен сжимать чат в ноль
        self.setMinimumHeight(150)
        # Экземпляр создаётся один раз и живёт всё время приложения;
        # PySide6 сам отвязывает соединения при уничтожении объекта-приёмника
        ui_signals.message_sent.connect(self._on_message_sent)
        ui_signals.history_cleared.connect(self.reload_history)
        ui_signals.typing_started.connect(self.show_typing_indicator)
        ui_signals.typing_finished.connect(self.hide_typing_indicator)

        self._typing_indicator = None
        self._message_handler = None
        self._history_loaded = False
        self._history_dirty = False
        self._history_offset = 0
        self._history_exhausted = False
        self._auto_follow = True

        self.dialog_box_lay = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True) # Важно: позволяет контейнеру растягиваться
        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)

        self.load_more_btn = QPushButton("Показать более ранние сообщения")
        self.load_more_btn.setObjectName("loadMoreButton")
        self.load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_more_btn.clicked.connect(self._load_older)
        self.load_more_btn.hide()
        self.main_frame_lay.addWidget(
            self.load_more_btn, 0, Qt.AlignmentFlag.AlignHCenter
        )

        self.main_frame_lay.addStretch(10)

        self.scroll_area.setWidget(self.main_frame)
        self.dialog_box_lay.addWidget(self.scroll_area)

        scroll_bar = self.scroll_area.verticalScrollBar()
        # Мгновенный доскролл при росте контента, если пользователь у низа
        scroll_bar.rangeChanged.connect(self._on_range_changed)
        # Если пользователь отлистал вверх — не дёргаем его новыми сообщениями
        scroll_bar.valueChanged.connect(self._on_value_changed)

    def showEvent(self, event):
        super().showEvent(event)
        # История грузится при первом показе или когда скрытая вкладка
        # пропустила новые сообщения
        if not self._history_loaded or self._history_dirty:
            self.load_history()

    _FOLLOW_THRESHOLD = 40  # px от низа, считаемся «у низа»

    def _on_range_changed(self, _min: int, maximum: int):
        """Рост контента: доскролл, если пользователь у низа чата."""
        if self._auto_follow:
            self.scroll_area.verticalScrollBar().setValue(maximum)

    def _on_value_changed(self, value: int):
        """Пользователь листает сам: отключаем/включаем автоскролл."""
        scroll_bar = self.scroll_area.verticalScrollBar()
        self._auto_follow = value >= scroll_bar.maximum() - self._FOLLOW_THRESHOLD

    def _scroll_to_bottom(self):
        scroll_bar = self.scroll_area.verticalScrollBar()
        self._auto_follow = True
        scroll_bar.setValue(scroll_bar.maximum())

    def _on_message_sent(self, author: str, text: str):
        if self.isVisible():
            self.add_message(author, text)
        else:
            # Чат скрыт (пользователь не на странице ввода): перечитаем
            # историю при следующем показе
            self._history_dirty = True

    def show_typing_indicator(self, author_name: str = "IAMOS"):
        """Показывает анимированный индикатор думания нейросети."""
        if not self.isVisible() or self._typing_indicator is not None:
            return  # скрытая вкладка / уже показан
        self._typing_indicator = TypingIndicator(author_name=author_name)
        count = self.main_frame_lay.count()
        self.main_frame_lay.insertWidget(count - 1, self._typing_indicator)
        self._typing_indicator.start()
        self._scroll_to_bottom()

    def hide_typing_indicator(self):
        """Скрывает и удаляет индикатор думания."""
        if self._typing_indicator is None:
            return
        self._typing_indicator.stop()
        self.main_frame_lay.removeWidget(self._typing_indicator)
        self._typing_indicator.deleteLater()
        self._typing_indicator = None

    def add_message(self, author: str, text: str, time: str = None):
        self._append_message(author, text, time)
        self._scroll_to_bottom()

    def _append_message(self, author: str, text: str, time: str = None) -> Message:
        message = Message(author, text, time)
        self.main_frame_lay.insertWidget(self.main_frame_lay.count() - 1, message)
        return message

    def load_history(self):
        """Показывает последние сообщения; остальные — по кнопке."""
        self._clear_messages()
        messages = load_chat_history_page(self.PAGE_SIZE, 0)
        for message in messages:
            self._append_message(
                message["author"], message["text"], message["time"]
            )
        self._history_offset = len(messages)
        self._history_exhausted = len(messages) < self.PAGE_SIZE
        self._history_loaded = True
        self._history_dirty = False
        self.load_more_btn.setVisible(not self._history_exhausted)
        self._scroll_to_bottom()

    def _load_older(self):
        """Догружает предыдущую страницу истории над текущими сообщениями."""
        if self._history_exhausted:
            return

        messages = load_chat_history_page(self.PAGE_SIZE, self._history_offset)
        if not messages:
            self._history_exhausted = True
            self.load_more_btn.hide()
            return

        scroll_bar = self.scroll_area.verticalScrollBar()
        distance_from_bottom = scroll_bar.maximum() - scroll_bar.value()

        for index, message in enumerate(messages):
            widget = Message(
                message["author"], message["text"], message["time"]
            )
            self.main_frame_lay.insertWidget(1 + index, widget)

        self._history_offset += len(messages)
        self._history_exhausted = len(messages) < self.PAGE_SIZE
        self.load_more_btn.setVisible(not self._history_exhausted)
        # Сохраняем позицию чтения: контент вырос сверху.
        QTimer.singleShot(
            0,
            lambda: scroll_bar.setValue(
                max(scroll_bar.maximum() - distance_from_bottom, 0)
            ),
        )

    def reload_history(self):
        """Очищает текущие сообщения и перезагружает историю из файла."""
        self._clear_messages()
        self._history_loaded = False
        self._history_dirty = True
        self._history_offset = 0
        self._history_exhausted = False
        self.load_more_btn.hide()
        if self.isVisible():
            self.load_history()

    def _clear_messages(self):
        """Удаляет сообщения, оставляя кнопку «показать ещё» и растяжку."""
        while self.main_frame_lay.count() > 2:
            item = self.main_frame_lay.takeAt(1)
            widget = item.widget()
            if widget is None:
                continue
            if widget is self._typing_indicator:
                self._typing_indicator = None
            widget.deleteLater()
