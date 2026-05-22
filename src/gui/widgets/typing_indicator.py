from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap, QTextOption, QPen
from themes import THEMES, _COLOR_MAP, SELECTED_THEME
import math

class TypingDotsWidget(QWidget):
    """
    Анимированные три точки, имитирующие эффект печатания/думания.
    Точки поочерёдно пульсируют по яркости и подпрыгивают вверх-вниз (~60 FPS).
    """
    def __init__(self, dot_color: str = "#4CAF50", parent=None):
        super().__init__(parent)
        self._dot_color = QColor(dot_color)
        self._dot_count = 3
        self._phase = 0.0
        self._dot_radius = 5
        self._dot_spacing = 20
        self._min_alpha = 120
        self._max_alpha = 255
        self._jump_amplitude = 2  # амплитуда подпрыгивания в пикселях

        total_w = self._dot_count * self._dot_spacing
        total_h = self._dot_radius * 2 + 6 + self._jump_amplitude * 2
        self.setFixedSize(total_w, total_h)

        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._phase = 0.0
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.update()

    def set_color(self, hex_color: str):
        self._dot_color = QColor(hex_color)
        self.update()

    def apply_theme(self, theme: dict):
        """
        Применяет тему интерфейса — устанавливает цвет точек из темы.
        :param theme: словарь темы с ключом 'typing_dots'
        """
        dots_config = theme.get("typing_dots", {})
        dot_color = dots_config.get("color", "#4CAF50")
        self.set_color(dot_color)

    def _tick(self):
        self._phase = (self._phase + 0.06) % self._dot_count
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self._dot_radius
        base_cy = self.height() // 2
        for i in range(self._dot_count):
            dist = abs((self._phase - i + self._dot_count) % self._dot_count)
            dist = min(dist, self._dot_count - dist)
            brightness = math.cos(dist * math.pi / (self._dot_count - 0.5))
            brightness = max(0.0, brightness)
            alpha = int(self._min_alpha + (self._max_alpha - self._min_alpha) * brightness)
            color = QColor(self._dot_color.red(), self._dot_color.green(),
                           self._dot_color.blue(), alpha)
            
            # Вычисляем смещение по Y для эффекта подпрыгивания
            jump_offset = math.sin((self._phase - i) * math.pi) * self._jump_amplitude * brightness
            cy = base_cy + jump_offset
            
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(cx - self._dot_radius, cy - self._dot_radius,
                       self._dot_radius * 2, self._dot_radius * 2)
            )
            cx += self._dot_spacing
        painter.end()

class TypingIndicator(QWidget):
    """
    Пузырь «думания» нейросети с анимированными точками.
    Стилизован аналогично Message — органично встраивается в DialogBox.
    """
    def __init__(self, author_name: str = "IAMOS", frame_style: str = "",
                 label_style: str = "", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        outer_lay = QHBoxLayout(self)
        outer_lay.setContentsMargins(10, 5, 10, 5)
        outer_lay.setSpacing(5)

        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(frame_style)
        self.main_frame.setMinimumWidth(100)
        self.main_frame.setMaximumWidth(300)
        self.main_frame.setSizePolicy(QSizePolicy.Policy.MinimumExpanding,
                                      QSizePolicy.Policy.MinimumExpanding)

        frame_lay = QVBoxLayout(self.main_frame)
        frame_lay.setContentsMargins(12, 10, 12, 10)
        frame_lay.setSpacing(6)

        self.author_label = QLabel(author_name)
        self.author_label.setStyleSheet(label_style)
        frame_lay.addWidget(self.author_label)

        self.dots = TypingDotsWidget()
        frame_lay.addWidget(self.dots, alignment=Qt.AlignmentFlag.AlignLeft)

        outer_lay.addWidget(self.main_frame)
        outer_lay.addStretch()

    def start(self):
        self.dots.start()

    def stop(self):
        self.dots.stop()

    def _apply_theme(self, theme: dict):
        self.main_frame.setStyleSheet(theme.get("message_frame", ""))
        self.author_label.setStyleSheet(theme.get("message_author", ""))
        self.dots.apply_theme(theme)
