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


        
        # Боковая панель
        self.side_panel = QWidget(self.main_widget)
        self.side_panel.setFixedWidth(190) 
        self.side_panel.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
        
        self.main_layout.addWidget(self.side_panel, 2)
        
        # Лайаут боковой панели
        self.side_panel_layout = QVBoxLayout(self.side_panel)

        
        

        
        # Панель контента
        self.content_panel = QStackedWidget(self.main_widget)
        self.setFixedWidth(600)
        self.content_panel.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
        self.main_layout.addWidget(self.content_panel, 7)


        
        
        
        self.pages = [
            Settings(),
            Profile(),
            VoiceInput(),
            TextInput(),
            GesturesInput(),
            Dictator()
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
