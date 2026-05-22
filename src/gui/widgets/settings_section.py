from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap, QTextOption, QPen
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from src.gui.signals import ui_signals
from src.gui import icon_path
from src.utils.BasicUtils import BasicUtils