from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
import sys
from AssistentCore import get_available_cameras

"""
====================================================
Правила(напоминание) наименования переменных и атрибутов
button - кнопка - btn
layout - лэйаут - lay
frame - рамка/фрейм - frame
Qt Style Sheets - стили qss - qss
"""


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
        self.main_lay = QHBoxLayout(self.main_widget)
        self.main_lay.setContentsMargins(15, 15, 15, 15)
        self.main_lay.setSpacing(10)


        self.settings_page = Settings()
        self.profile_page = Profile()
        self.voice_input_page = VoiceInput()
        self.text_input_page = TextInput()
        self.gestures_input_page = GesturesInput()
        self.content_pages = {self.settings_page : self.settings_page.side_panel_btn,
                            self.profile_page : self.profile_page.side_panel_btn,
                            self.voice_input_page : self.voice_input_page.side_panel_btn,
                            self.text_input_page : self.text_input_page.side_panel_btn,
                            self.gestures_input_page : self.gestures_input_page.side_panel_btn
                            }
        
        
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
        self.side_panel_lay = QVBoxLayout(self.side_panel)
        self.side_panel_lay.setContentsMargins(10, 10, 10, 10)
        
        self.side_panel_lay.setSpacing(10)
    


        # линкование кнопок
        for page in self.content_pages:
            btn = self.content_pages[page]
            # Фиксируем p=page, чтобы каждая кнопка запомнила свою страницу
            btn.clicked.connect(lambda checked, p=page: self.content_panel.setCurrentWidget(p))
            self.content_panel.addWidget(page)
            self.side_panel_lay.addWidget(btn)


        self.side_panel_lay.addStretch(1)


        self.main_lay.addWidget(self.side_panel, 2)
        self.main_lay.addWidget(self.content_panel, 7)
        self.content_panel.setCurrentIndex(0)






       

        

class ContentPageWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.side_panel_btn = QPushButton()
        self.side_panel_btn.setStyleSheet("""
            QPushButton {
                background-color: #D9D9D9;
                border-radius: 12px;
                color: #000000;
                font-size: 14px;
                font-family: "Roboto";
                border: 3px solid transparent; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #C8C8C8;
                border: 3px solid #888888; 
            }
            QPushButton:pressed {
                background-color: #B8B8B8;
                border: 3px solid #666666; 
            }
        """)          
        self.settings_text_qss = """
            color: #000000;
            font-size: 14px;
            font-family: "Roboto";
        """
        self.dropbox_qss = """
            /* Основной вид кнопки */
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                font-size: 14px;
                color: #000000;
            }
            /* При наведении */
            QComboBox:hover {
                border: 1px solid #888888;
                background-color: #F9F9F9;
            }
            /* При раскрытии списка */
            QComboBox:on {
                border: 1px solid #888888;
            }
            /* Выпадающая стрелка */
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                /* Можно поставить свою иконку, пока оставим стандартную */
                /* image: url(:/icons/arrow.png); */
            }
            /* Стили самого выпадающего меню */
            QComboBox QAbstractItemView {
                background-color: transparent;
                border-radius: 8px;
                selection-background-color: #D9D9D9; /* Цвет выделения */
                selection-color: #000000;
                outline: none;
            }
        """
        self.side_panel_btn.setMinimumSize(160, 60)
        
# ===========================================================
# НАСТРОЙКИ
# ===========================================================
class Settings(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Настройки") 
        
        # сетка-панель настроек
        self.grid_lay = QGridLayout(self)
        self.grid_lay.setContentsMargins(10, 10, 10, 10)
        # фрейм для выбора камеры
        self.camera_frame = QFrame()
        self.camera_frame.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.camera_frame.setFixedHeight(40)
        self.grid_lay.addWidget(self.camera_frame, 0, 0)
        # лайаут фрейма камер
        self.camera_frame_lay = QHBoxLayout(self.camera_frame)
        self.camera_frame_lay.setContentsMargins(10, 5, 5, 10)
        self.camera_frame_lay.setSpacing(10)

        # текстовая метка "Камера"
        self.camera_label = QLabel("Камера:")
        self.camera_label.setStyleSheet(self.settings_text_qss)
        # выпадающий список камер
        self.camera_dropbox = QComboBox()
        self.camera_dropbox.setStyleSheet(self.dropbox_qss)
        self.camera_dropbox.setMinimumHeight(30)

        available = get_available_cameras()
        
        if available:
            self.camera_dropbox.addItems(available)
        else:
            self.camera_dropbox.addItem("Нет доступных камер")

        self.camera_frame_lay.addWidget(self.camera_label, 1)
        self.camera_frame_lay.addWidget(self.camera_dropbox, 1)
        self.camera_frame_lay.addStretch(1)

        


        self.microphone_frame = QFrame()
        self.microphone_frame_lay = QHBoxLayout(self.microphone_frame)
        self.microphone_label = QLabel("Микрофон:")
        self.microphone_frame_lay.addWidget(self.microphone_label)

        self.grid_lay.addWidget(self.microphone_frame, 1, 0)
        self.speaker_frame = QFrame()
        self.grid_lay.addWidget(self.speaker_frame, 2, 0)

        self.speaker_frame_lay = QHBoxLayout(self.speaker_frame)
        self.speaker_label = QLabel("Спикер:")
        self.speaker_frame_lay.addWidget(self.speaker_label)

    def get_current_camera(self):
        return self.camera_dropbox.currentText()
    
    def get_current_microphone(self):
        return self.microphone_dropbox.currentText()
    
    def get_current_speaker(self):
        return self.speaker_dropbox.currentText()

# ===========================================================
# ПРОФИЛЬ
# ===========================================================
class Profile(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Профиль") 

# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Голосовой Ввод") 

# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Текстовый Ввод") 

# ===========================================================
# ЖЕСТОВЫЙ ВВОД
# ===========================================================
class GesturesInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Жестовый Ввод") 

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
