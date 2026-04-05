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
        self.setMinimumSize(700, 525)
        self.setStyleSheet("""
                           background-color: #D9D9D9;
                           """)
        # Основное окно
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Основной лайаут: размещает боковую панель и панель контента горизонтально
        self.main_layout = QHBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        self.content_pages = [Settings(self), Profile(self),
                               VoiceInput(self), TextInput(self),
                               GesturesInput(self)]

        self.side_panel_buttons = []
        
         # Панель контента(является лэйаутом)
        self.content_panel = QStackedWidget(self.main_widget)
        self.content_panel.setMinimumWidth(330)
        self.content_panel.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
    

        
        # Боковая панель
        self.side_panel = QWidget(self.main_widget)
        self.side_panel.setMaximumWidth(190) 
        self.side_panel.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
        
        
        # Лайаут боковой панели
        self.side_panel_layout = QVBoxLayout(self.side_panel)
        self.side_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        self.side_panel_layout.setSpacing(10)
    

        self.side_panel_layout.addStretch(1)


        self.main_layout.addWidget(self.side_panel, 2)
        self.main_layout.addWidget(self.content_panel, 7)






       

        

        

class ContentPageWidget(QWidget):
    def __init__(self, master):
        super().__init__(master)
        
        self.side_panel_button = QPushButton()
        self.side_panel_button.setStyleSheet("""    
            background-color: #D9D9D9;            
            border-radius: 12px;
            color: #000000;
            font-size: 16px;
            font-family: "Roboto";                            
            """)          
        self.side_panel_button.setMinimumSize(160, 60)
        
# ===========================================================
# НАСТРОЙКИ
# ===========================================================
class Settings(ContentPageWidget):
    def __init__(self, master):
        super().__init__(master)
        self.side_panel_button.setText("Настройки") 
        

# ===========================================================
# ПРОФИЛЬ
# ===========================================================
class Profile(ContentPageWidget):
    def __init__(self, master):
        super().__init__(master)
        self.side_panel_button.setText("Профиль") 

# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(ContentPageWidget):
    def __init__(self, master):
        super().__init__(master)
        self.side_panel_button.setText("Голосовой Ввод") 

# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(ContentPageWidget):
    def __init__(self, master):
        super().__init__(master)
        self.side_panel_button.setText("Текстовый Ввод") 

# ===========================================================
# ЖЕСТОВЫЙ ВВОД
# ===========================================================
class GesturesInput(ContentPageWidget):
    def __init__(self, master):
        super().__init__(master)
        self.side_panel_button.setText("Жестовый Ввод") 

# ===========================================================
# ДИКТОР
# ===========================================================
class ScreenReader(QWidget):
    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    window.show()
    sys.exit(app.exec())
