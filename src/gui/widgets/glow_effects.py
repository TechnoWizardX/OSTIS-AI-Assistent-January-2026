from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap, QTextOption, QPen
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME   
import math

class RunningLineOverlay(QWidget):
    """
    Overlay-виджет для отрисовки бегущей линии по периметру кнопки.
    Цвет линии адаптируется к текущей теме интерфейса.
    """
    def __init__(self, parent, button, theme_name: str = "dark"):
        super().__init__(parent)
        self.button = button
        self.phase = 0
        self.theme_name = theme_name
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # Получаем параметры свечения из темы
        colors = _COLOR_MAP.get(theme_name, _COLOR_MAP["dark"])
        
        # Цвет и радиус свечения из темы
        glow_color_hex = colors.get("glow", "#00FF00")
        glow_blur = colors.get("glow_blur", 30)
        
        self.line_color = QColor(glow_color_hex)

        # Тень для линии — яркий эффект с параметрами из темы
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(glow_blur)
        self.glow_effect.setColor(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 200))
        self.glow_effect.setXOffset(0)
        self.glow_effect.setYOffset(0)
        self.setGraphicsEffect(self.glow_effect)

    def paintEvent(self, event):
        """Рисует бегущую линию по периметру с скруглёнными углами."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Размеры кнопки
        w = self.width()
        h = self.height()
        margin = 2  # отступ для границы
        corner_radius = 12  # радиус скругления как у кнопки

        # Рисуем полный контур кнопки (скруглённый прямоугольник)
        path = QPainterPath()
        path.addRoundedRect(margin, margin, w - 2*margin, h - 2*margin, corner_radius, corner_radius)

        # Получаем длину контура
        perimeter = path.length()

        # Позиция бегущей линии
        line_length = perimeter * 0.35  # длина линии 35% от периметра
        start_pos = (self.phase % 4) * perimeter / 4

        # Рисуем линию вдоль контура с градиентом прозрачности
        num_segments = int(line_length)
        for i in range(num_segments):
            pos = (start_pos + i) % perimeter
            prev_pos = (start_pos + i - 1) % perimeter if i > 0 else pos

            # Градиент прозрачности: яркий центр, тусклые края
            dist_from_start = i / line_length
            # Используем синусоиду для плавного градиента
            alpha = int(255 * math.sin(dist_from_start * math.pi))

            point = path.pointAtPercent(pos / perimeter)
            prev_point = path.pointAtPercent(prev_pos / perimeter)

            # Рисуем сегмент линии с цветом из темы
            pen = QPen(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), alpha), 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            if i > 0:
                painter.drawLine(prev_point, point)

        painter.end()
        
class RecommendationGlowEffect:
    """
    Класс для управления анимированной 'бегущей' подсветкой по периметру кнопки.
    Создает overlay-виджет с бегущей линией и тенью поверх кнопки.
    """

    def __init__(self, button: QPushButton, theme_name: str = "dark"):
        self.button = button
        self.theme_name = theme_name
        self.overlay = None
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_position)
        self.phase = 0
        self.is_active = False

    def start(self):
        """Запускает анимацию бегущей линии."""
        if self.is_active:
            return
        self.is_active = True

        # Создаем overlay-виджет если ещё не создан
        if not self.overlay:
            self._create_overlay()

        self.overlay.show()
        self.animation_timer.start(16)  # ~60 FPS для плавности

    def stop(self):
        """Останавливает анимацию и скрывает overlay."""
        self.is_active = False
        self.animation_timer.stop()
        if self.overlay:
            self.overlay.hide()

    def update_theme(self, theme_name: str):
        """Обновляет тему и пересоздает overlay с новым цветом."""
        self.theme_name = theme_name
        if self.overlay:
            # Скрываем старый overlay
            self.overlay.hide()
            # Пересоздаем overlay с новой темой
            self._create_overlay()
            # Если анимация была активна, показываем новый overlay
            if self.is_active:
                self.overlay.show()

    def _create_overlay(self):
        """Создает overlay-виджет для отрисовки бегущей линии."""
        self.overlay = RunningLineOverlay(self.button.parent(), self.button, self.theme_name)
        self.overlay.setGeometry(self.button.geometry())
        self.overlay.raise_()

    def _update_position(self):
        """Обновляет позицию бегущей линии."""
        if not self.is_active or not self.overlay:
            return

        self.phase += 0.03  # Медленнее для плавности

        # Синхронизируем overlay с позицией и размером кнопки
        self.overlay.setGeometry(self.button.geometry())
        self.overlay.raise_()

        # Обновляем фазу для отрисовки
        self.overlay.phase = self.phase
        self.overlay.update()  # Вызываем перерисовку
