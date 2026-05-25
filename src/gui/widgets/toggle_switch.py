from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from src.utils.config import load_settings_config, set_settings_config_value
from src.gui.signals import ui_signals

class ToggleSwitch(QWidget):
    """Красивый переключатель с плавной анимацией"""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumWidth(52)
        self.setMinimumHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Состояние
        self._checked = False
        
        # Цвета из темы
        _t = THEMES[SELECTED_THEME]["toggle_switch"]
        self._bg_color_off = QColor(_t["bg_off"])
        self._bg_color_on = QColor(_t["bg_on"])
        self._circle_color = QColor(_t["circle"])
        
        # Анимация позиции (0.0 - 1.0)
        self._anim_progress = 0.0
        self._anim_target = 0.0

        # Таймер анимации
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60 FPS
        self._anim_timer.timeout.connect(self._animate)

    def isChecked(self):
        return self._checked

    def setChecked(self, state):
        if self._checked == state:
            return
        self._checked = state
        self._anim_target = 1.0 if state else 0.0
        if not self._anim_timer.isActive():
            self._anim_timer.start()
        self.update()
        self.toggled.emit(state)

    def toggle(self):
        self.setChecked(not self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _animate(self):
        """Плавная анимация переключения"""
        diff = self._anim_target - self._anim_progress
        if abs(diff) < 0.01:
            self._anim_progress = self._anim_target
            self._anim_timer.stop()
        else:
            self._anim_progress += diff * 0.3
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Фон - скругленный прямоугольник
        bg_rect = QRectF(1, height/2 - 11, width - 2, 22)
        path = QPainterPath()
        path.addRoundedRect(bg_rect, 11, 11)

        # Цвет фона с анимацией
        bg_color = self._bg_color_on if self._checked else self._bg_color_off
        painter.fillPath(path, bg_color)

        # Круг с анимацией позиции
        circle_radius = 9
        max_x = width - circle_radius - 2
        min_x = circle_radius + 2
        circle_x = min_x + (max_x - min_x) * self._anim_progress
        circle_y = height / 2

        painter.setBrush(self._circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(circle_x - circle_radius, circle_y - circle_radius,
                                   circle_radius * 2, circle_radius * 2))
        painter.end()

    def _apply_theme(self, theme: dict):
        """Обновляет цвета переключателя."""
        ts = theme["toggle_switch"]
        self._bg_color_off = QColor(ts["bg_off"])
        self._bg_color_on = QColor(ts["bg_on"])
        self._circle_color = QColor(ts["circle"])
        self.update()


class ToggleSwitchRow(QWidget):
    """Фрейм с меткой и переключателем для настроек"""

    toggled = pyqtSignal(bool)

    def __init__(self, text, parent=None, checked=False):
        super().__init__(parent)

        # Основной лайаут
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # фрейм для переключателя
        self.toggle_frame = QFrame()
        self.toggle_frame.setStyleSheet(THEMES[SELECTED_THEME]["toggle_switch_row"])
        self.toggle_frame.setFixedHeight(40)
        main_layout.addWidget(self.toggle_frame)

        # лайаут фрейма переключателя
        self.toggle_frame_lay = QHBoxLayout(self.toggle_frame)
        self.toggle_frame_lay.setContentsMargins(10, 5, 15, 10)
        self.toggle_frame_lay.setSpacing(10)

        # Текстовая метка
        self.label = QLabel(text)
        self.label.setStyleSheet(THEMES[SELECTED_THEME]["toggle_switch_row_label"])
        self.toggle_frame_lay.addWidget(self.label, 1)

        # Переключатель
        self.toggle_switch = ToggleSwitch()
        self.toggle_frame_lay.addWidget(self.toggle_switch)

        # Подключаем сигнал
        self.toggle_switch.toggled.connect(self.toggled.emit)

    def isChecked(self):
        return self.toggle_switch.isChecked()

    def setChecked(self, state):
        self.toggle_switch.setChecked(state)

    def _apply_theme(self, theme: dict):
        """Обновляет стили фрейма и метки."""
        self.toggle_frame.setStyleSheet(theme["toggle_switch_row"])
        self.label.setStyleSheet(theme["toggle_switch_row_label"])
        self.toggle_switch._apply_theme(theme)


class ToggleSwitchState:
    """Класс для сохранения и загрузки состояния переключателя"""
    
    def __init__(self, config_key):
        self.config_key = config_key
    
    def save(self, state):
        """Сохраняет состояние переключателя в конфиг"""
        set_settings_config_value(self.config_key, state)
        ui_signals.settings_changed.emit({self.config_key: state})
    
    def load(self):
        """Загружает состояние переключателя из конфига"""
        settings_config = load_settings_config()
        return settings_config.get(self.config_key, False)