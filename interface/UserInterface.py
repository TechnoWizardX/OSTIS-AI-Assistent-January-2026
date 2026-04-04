from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
import sys





# ===========================================================
# ГЛАВНЫЙ ИНТЕРФЕЙС
# ===========================================================
class UserInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IAMOS")
        self.setGeometry(100, 100, 820, 690)
        self.setMinimumSize(800, 600)

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.main_grid_layaout = QGridLayout(self.main_widget)
        
        
        
        self.pages = [
            Settings(),
            Profile(),
            VoiceInput(),
            TextInput(),
            GesturesInput(),
            Dictator()
        ]
        
        self.buttons = [
            QPushButton("Настройки"),
            QPushButton("Профиль"),
            QPushButton("Голосовой ввод"),
            QPushButton("Текстовый ввод"),
            QPushButton("Жестовый ввод"),
            QPushButton("Экранный диктор")
        ]


# ===========================================================
# НАСТРОЙКИ
# ===========================================================
class Settings(QMainWindow):
    def __init__(self):
        super().__init__()


# ===========================================================
# ПРОФИЛЬ
# ===========================================================
class Profile(QMainWindow):
    def __init__(self):
        super().__init__()


# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(QMainWindow):
    def __init__(self):
        super().__init__()


# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(QMainWindow):
    def __init__(self):
        super().__init__()


# ===========================================================
# ЖЕСТОВЫЙ ВВОД
# ===========================================================
class GesturesInput(QMainWindow):
    def __init__(self):
        super().__init__()


# ===========================================================
# ДИКТОР
# ===========================================================
class Dictator(QMainWindow):
    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    window.show()
    sys.exit(app.exec())
