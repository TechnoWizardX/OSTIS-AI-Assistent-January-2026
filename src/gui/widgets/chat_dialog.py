from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap, QTextOption, QPen
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from src.gui.signals import ui_signals
from src.gui.widgets.typing_indicator import TypingIndicator
from src.gui.widgets.message_item import Message
from src.utils.BasicUtils import BasicUtils
class DialogBox(QWidget):
    """Чат (здесь отображаются сообщения)"""
    def __init__(self):
        super().__init__()
        # Подключение к сигналу будет сделано извне через set_message_handler
        try:
            ui_signals.message_sent.disconnect(self.add_message)
        except Exception:
            pass
        ui_signals.message_sent.connect(self.add_message)
        ui_signals.history_cleared.connect(self.reload_history)
        ui_signals.typing_started.connect(self.show_typing_indicator)
        ui_signals.typing_finished.connect(self.hide_typing_indicator)
        self._typing_indicator = None
        self._message_handler = None
        self.dialog_box_lay = QVBoxLayout(self)  
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Важно: позволяет контейнеру растягиваться
        self.scroll_area.setStyleSheet(
            THEMES[SELECTED_THEME]["chat_scroll_area"] + THEMES[SELECTED_THEME]["scrollbar"]
        )     
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(THEMES[SELECTED_THEME]["dialog_frame"])
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        self.main_frame_lay.addStretch(10)

        self.scroll_area.setWidget(self.main_frame)
        self.dialog_box_lay.addWidget(self.scroll_area)

        self.load_history()

    def show_typing_indicator(self, author_name: str = "IAMOS"):
        """Показывает анимированный индикатор думания нейросети."""
        if self._typing_indicator is not None:
            return  # уже показан
        self._typing_indicator = TypingIndicator(
            author_name=author_name,
            frame_style=THEMES[SELECTED_THEME].get("message_frame", ""),
            label_style=THEMES[SELECTED_THEME].get("message_author", ""),
        )
        # Применяем тему сразу после создания
        self._typing_indicator._apply_theme(THEMES[SELECTED_THEME])
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
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        # Используем таймер, чтобы дать Qt время пересчитать размеры виджетов
        QTimer.singleShot(500, self._actual_scroll)

    def _actual_scroll(self):
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
    
    def load_history(self):
        """Загружает историю сообщений."""
        history = BasicUtils.load_chat_history()
        for message in history:
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

    def _apply_theme(self, theme: dict):
        """Обновляет стили чата."""
        self.scroll_area.setStyleSheet(theme["chat_scroll_area"] + theme["scrollbar"])
        self.main_frame.setStyleSheet(theme["dialog_frame"])
        
        for i in range(self.main_frame_lay.count()):
            item = self.main_frame_lay.itemAt(i)
            widget = item.widget()

            # Проверяем, что это именно виджет сообщения (чтобы не трогать stretch)
            if isinstance(widget, Message):
                widget._apply_theme(theme)
            elif isinstance(widget, TypingIndicator):
                widget._apply_theme(theme)