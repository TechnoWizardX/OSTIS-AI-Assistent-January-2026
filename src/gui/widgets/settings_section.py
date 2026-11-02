from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class SettingsSectionLabel(QWidget):
    """Минималистичный заголовок-разделитель для группировки настроек.
    Рисует тонкую цветную полосу слева и текст метки."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsSection")
        self._text = text
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        # Тонкий вертикальный акцент-прямоугольник
        self._accent = QFrame()
        self._accent.setObjectName("accentFrame")
        self._accent.setFixedSize(3, 16)
        lay.addWidget(self._accent, 0, Qt.AlignmentFlag.AlignVCenter)

        # Текстовая метка
        self._label = QLabel(text)
        self._label.setObjectName("settingsSectionLabel")
        lay.addWidget(self._label, 1)

        # Горизонтальная разделительная линия
        self._line = QFrame()
        self._line.setObjectName("borderLine")
        self._line.setFrameShape(QFrame.Shape.HLine)
        self._line.setFixedHeight(1)
        lay.addWidget(self._line, 6)
