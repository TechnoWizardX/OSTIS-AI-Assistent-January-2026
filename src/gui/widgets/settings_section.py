from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME

class SettingsSectionLabel(QWidget):
    """Минималистичный заголовок-разделитель для группировки настроек.
    Рисует тонкую цветную полосу слева и текст метки."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        # Тонкий вертикальный акцент-прямоугольник
        self._accent = QFrame()
        self._accent.setFixedSize(3, 16)
        self._accent.setStyleSheet(THEMES[SELECTED_THEME]["accent"])
        lay.addWidget(self._accent, 0, Qt.AlignmentFlag.AlignVCenter)

        # Текстовая метка
        self._label = QLabel(text)
        self._label.setStyleSheet(THEMES[SELECTED_THEME]["settings_section_label"])
        lay.addWidget(self._label, 1)

        # Горизонтальная разделительная линия
        self._line = QFrame()
        self._line.setFrameShape(QFrame.Shape.HLine)
        self._line.setFixedHeight(1)
        self._line.setStyleSheet(THEMES[SELECTED_THEME]["border"])
        lay.addWidget(self._line, 6)

    def _apply_theme(self, theme: dict):
        self._accent.setStyleSheet(theme["accent"])
        self._label.setStyleSheet(theme["settings_section_label"])
        self._line.setStyleSheet(theme["border"])
