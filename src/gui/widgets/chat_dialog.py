from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from src.gui.signals import ui_signals
from src.gui.widgets.message_item import Message
from src.gui.widgets.typing_indicator import TypingIndicator
from src.utils.chat_history import load_chat_history

# Сколько последних сообщений истории рендерить виджетами
MAX_RENDERED_HISTORY = 100


class DialogBox(QWidget):
    """Чат (здесь отображаются сообщения)"""
    def __init__(self):
        super().__init__()
        # Сплиттер не должен сжимать чат в ноль
        self.setMinimumHeight(150)
        # Экземпляр создаётся один раз и живёт всё время приложения;
        # PySide6 сам отвязывает соединения при уничтожении объекта-приёмника
        ui_signals.message_sent.connect(self.add_message)
        ui_signals.history_cleared.connect(self.reload_history)
        ui_signals.typing_started.connect(self.show_typing_indicator)
        ui_signals.typing_finished.connect(self.hide_typing_indicator)
        self._typing_indicator = None
        self._message_handler = None
        self._history_loaded = False
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
        # История грузится один раз, при первом показе страницы
        if not self._history_loaded:
            self._history_loaded = True
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

    def show_typing_indicator(self, author_name: str = "IAMOS"):
        """Показывает анимированный индикатор думания нейросети."""
        if self._typing_indicator is not None:
            return  # уже показан
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
        message = Message(author, text, time)
        count = self.main_frame_lay.count()
        self.main_frame_lay.insertWidget(count - 1, message)   # Без alignment
        # Доскролл сделает _on_range_changed, когда контент вырастет
        # (авто-следованию отключается, если пользователь листает выше)

    def load_history(self):
        """Загружает последние сообщения истории."""
        history = load_chat_history()
        for message in history[-MAX_RENDERED_HISTORY:]:
            self.add_message(message["author"], message["text"], message["time"])

    def reload_history(self):
        """Очищает текущие сообщения и перезагружает историю из файла"""
        # Удаляем все виджеты сообщений, оставляя только растяжку (последний элемент)
        while self.main_frame_lay.count() > 1:
            item = self.main_frame_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Загружаем историю заново
        self.load_history()
