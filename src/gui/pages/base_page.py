from PyQt6.QtWidgets import (QWidget, QGraphicsDropShadowEffect, QPushButton
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
class ContentPageWidget(QWidget):
    """Основание для панелей контента"""
    def __init__(self):
        super().__init__()

        self.side_panel_btn = QPushButton()
        self.side_panel_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_2"])
        self.settings_text_qss = THEMES[SELECTED_THEME]["settings_text"]
        self.dropbox_qss = THEMES[SELECTED_THEME]["settings_combobox"]
        self.side_panel_btn.setMinimumSize(55, 60)

        # состояние кнопки при нажатии
        self.side_panel_btn.setCheckable(True)

        # единый размер иконок
        self._icon_size = QSize(25, 25)

        self.side_panel_btn.setIconSize(self._icon_size)

        # Тень при наведении — создаём без родителя, чтобы не удалялся
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(20)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(4)
        self._shadow.setColor(QColor(0, 0, 0, 120))

        self.side_panel_btn.setGraphicsEffect(self._shadow)
        self._shadow.setEnabled(False)

        # Обработка наведения — с проверкой существования эффекта
        def on_enter(e):
            if hasattr(self, '_shadow') and self._shadow:
                self._shadow.setEnabled(True)
        def on_leave(e):
            if hasattr(self, '_shadow') and self._shadow:
                self._shadow.setEnabled(False)
        
        self.side_panel_btn.enterEvent = on_enter
        self.side_panel_btn.leaveEvent = on_leave

    def _apply_theme(self, theme: dict):
        """Обновляет стили кнопки боковой панели."""
        self.side_panel_btn.setStyleSheet(theme["btn_2"])
        self.settings_text_qss = theme["settings_text"]
        self.dropbox_qss = theme["settings_combobox"]
