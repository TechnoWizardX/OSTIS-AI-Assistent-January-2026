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
        self.setStyleSheet("""
                           background-color: #D9D9D9;
                           """)
        # Основное окно
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Основной лайаут: размещает боковую панель и панель контента горизонтально
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)

# АРТЁМ ТЫ ТУТ?

        # Боковая панель
        self.side_panel = QWidget(self.main_widget)
        self.side_panel.setFixedWidth(200) 
        
        self.main_layout.addWidget(self.side_panel, 2)
        
        # Лайаут боковой панели
        self.side_panel_layout = QVBoxLayout(self.side_panel)

        self.side_panel_frame = QFrame(self.side_panel)
        self.side_panel_frame.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
        self.side_panel_layout.addWidget(self.side_panel_frame)

        self.side_panel_frame_layout = QVBoxLayout(self.side_panel_frame)
        self.side_panel_frame_layout.setContentsMargins(0, 0, 0, 0)




        # Виджеты на панели контента
        self.settings_widget = QWidget(self)
        self.profile_widget = QWidget(self)
        self.voice_input_widget = QWidget(self)
        self.text_input_widget = QWidget(self)
        self.gestures_input_widget = QWidget(self)
        self.dictator_widget = QWidget(self)
        
        
        
        # Панель контента
        self.content_panel = QStackedWidget(self.main_widget)
        self.main_layout.addWidget(self.content_panel, 7)
        
        
        
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
class Settings(QWidget):
    def __init__(self):
        super().__init__()


# ===========================================================
# ПРОФИЛЬ
# ===========================================================
class Profile(QWidget):
    def __init__(self):
        super().__init__()


# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(QWidget):
    def __init__(self):
        super().__init__()


# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(QWidget):
    def __init__(self):
        super().__init__()


# ===========================================================
# ЖЕСТОВЫЙ ВВОД
# ===========================================================
class GesturesInput(QWidget):
    def __init__(self):
        super().__init__()


# ===========================================================
# ДИКТОР
# ===========================================================
class Dictator(QWidget):
    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    window.show()
    sys.exit(app.exec())
