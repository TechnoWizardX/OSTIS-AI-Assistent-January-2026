from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
import sys
import os
from AssistentCore import BasicFunctions

# Базовый путь для иконок
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")



def icon_path(filename):
    """Возвращает абсолютный путь к иконке"""
    return os.path.join(ICONS_DIR, filename)

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
        self.main_lay.setContentsMargins(10, 10, 10, 10)
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

        #создаём группу кнопок
        self.button_group = QButtonGroup(self)

        # линкование кнопок
        for page in self.content_pages:
            btn = self.content_pages[page]
            
            # добавляем кнопку в группу
            self.button_group.addButton(btn)
            
            # Фиксируем p=page, чтобы каждая кнопка запомнила свою страницу
            btn.clicked.connect(lambda checked, p=page: self.content_panel.setCurrentWidget(p))
            self.content_panel.addWidget(page)
            self.side_panel_lay.addWidget(btn)



        self.side_panel_lay.addStretch(1)


        self.main_lay.addWidget(self.side_panel, 2)
        self.main_lay.addWidget(self.content_panel, 7)
        self.content_panel.setCurrentIndex(0)




# ==========================================================
# Виджет отправки сообщений (текстовое поле)
# ==========================================================
class ChatSendBox(QWidget):
    def __init__(self):
        super().__init__()
        self.chats_send_box_lay = QVBoxLayout(self)
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
        self.chats_send_box_lay.addWidget(self.main_frame)
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        self.chat_send_input = QTextEdit()
        self.chat_send_input.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                font-size: 14px;
                font-family: "Roboto";
                color: #000000;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #CCCCCC;
                width: 8px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #B0B0B0;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                subcontrol-position: bottom;
            }
        """)
        self.main_frame_lay.addWidget(self.chat_send_input, 1)
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #D9D9D9;
                border-radius: 12px;
                color: #000000;
                font-size: 14px;
                font-family: "Roboto";
                border: 3px solid transparent;
                padding: 10px 10px 10px 20px;
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
        self.send_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.send_btn.setIcon(QIcon(icon_path("send.png")))
        self.main_frame_lay.addWidget(self.send_btn, 1, Qt.AlignmentFlag.AlignLeft)
        self.send_btn.clicked.connect(self.send_message)

        self.chat_send_input.installEventFilter(self)
    def send_message(self):
        text = self.chat_send_input.toPlainText()
        
        if not text:
            return
        BasicFunctions.add_message("user", text)
        self.chat_send_input.clear()

    def eventFilter(self, obj, event):
        if obj == self.chat_send_input and event.type() == event.Type.KeyPress:
        # Проверяем, нажат ли Enter (обычный или на NumPad)
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Проверяем, НЕ зажат ли Shift (чтобы Shift+Enter делал новую строку)
                if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.send_message()
                    return True  # Возвращаем True, чтобы QTextEdit не вставил перенос строки
    
    # Для всех остальных событий используем стандартную обработку
        return super().eventFilter(obj, event)

        
        


        
#==========================================================
#Основание для панелей контента
#==========================================================
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
                padding: 5px 5px 5px 16px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #C8C8C8;
                border: 3px solid #888888; 
            }
            QPushButton:pressed {
                background-color: #B8B8B8;
                border: 3px solid #666666; 
            }
            /*Для изменения цвета кнопки при нажатии*/
            QPushButton:checked {
                background-color: #AAFF00;  /* цвет активной кнопки */
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

        # состояние кнопки при нажатии
        self.side_panel_btn.setCheckable(True)
        
        # единый размер иконок
        self._icon_size = QSize(25, 25)
        
        self.side_panel_btn.setIconSize(self._icon_size)

        
# ===========================================================
# НАСТРОЙКИ
# ===========================================================
class Settings(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Настройки")
        self.side_panel_btn.setIcon(QIcon(icon_path("settings.png")))
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(0, 0, 0, 0)
        
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
                background-color: #FFFFFF;
                border-radius: 16px;
        """)
        # сетка-панель настроек
        self.main_lay.addWidget(self.main_frame)
        self.grid_lay = QGridLayout(self.main_frame)
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

        available = BasicFunctions.get_available_cameras()
        
        if available:
            self.camera_dropbox.addItems(available)
        else:
            self.camera_dropbox.addItem("Нет доступных камер")

        self.camera_frame_lay.addWidget(self.camera_label, 1)
        self.camera_frame_lay.addWidget(self.camera_dropbox, 1)

        
        self.microphone_frame = QFrame()
        self.microphone_frame.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.microphone_frame.setFixedHeight(40)
        self.grid_lay.addWidget(self.microphone_frame, 1, 0)
        # лайаут фрейма микрофона
        self.microphone_frame_lay = QHBoxLayout(self.microphone_frame)
        self.microphone_frame_lay.setContentsMargins(10, 5, 5, 10)
        self.microphone_frame_lay.setSpacing(10)

        # текстовая метка "Микрофон"
        self.microphone_label = QLabel("Микрофон:")
        self.microphone_label.setStyleSheet(self.settings_text_qss)
        # выпадающий список микрофонов
        self.microphone_dropbox = QComboBox()
        self.microphone_dropbox.setStyleSheet(self.dropbox_qss)
        self.microphone_dropbox.setMinimumHeight(30)

        available_mics = BasicFunctions.get_available_microphones()

        if available_mics:
            self.microphone_dropbox.addItems(available_mics)
        else:
            self.microphone_dropbox.addItem("Нет доступных микрофонов")

        self.microphone_frame_lay.addWidget(self.microphone_label, 1)
        self.microphone_frame_lay.addWidget(self.microphone_dropbox, 1)
        
        
        
        self.speaker_frame = QFrame()
        self.speaker_frame.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.speaker_frame.setFixedHeight(40)
        self.grid_lay.addWidget(self.speaker_frame, 2, 0)
        # лайаут фрейма микрофона
        self.speaker_frame_lay = QHBoxLayout(self.speaker_frame)
        self.speaker_frame_lay.setContentsMargins(10, 5, 5, 10)
        self.speaker_frame_lay.setSpacing(10)

        # текстовая метка "Микрофон"
        self.speaker_label = QLabel("Диктор:")
        self.speaker_label.setStyleSheet(self.settings_text_qss)
        # выпадающий список микрофонов
        self.speaker_dropbox = QComboBox()
        self.speaker_dropbox.setStyleSheet(self.dropbox_qss)
        self.speaker_dropbox.setMinimumHeight(30)

        self.speaker_frame_lay.addWidget(self.speaker_label, 1)
        self.speaker_frame_lay.addWidget(self.speaker_dropbox, 1)
        self.grid_lay.setRowStretch(3, 1)


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
        self.side_panel_btn.setIcon(QIcon(icon_path("profile.png")))

# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Голосовой Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("microphone.png"))) 

# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #D9D9D9;
                border-radius: 16px;
               }
        """)
        self.side_panel_btn.setText("Текстовый Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("text.png"))) 
        self.text_input_lay = QVBoxLayout(self)
        self.chat_box = ChatSendBox()
        self.text_input_lay.addWidget(self.chat_box)

# ===========================================================
# ЖЕСТОВЫЙ ВВОД
# ===========================================================
class GesturesInput(ContentPageWidget):

    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Жестовый Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("camera.png")))
        
        # Вертикальный лайаут всей страницы
        self.chat_lay = QVBoxLayout(self)
        self.chat_lay.setContentsMargins(15, 15, 15, 15)
        self.chat_lay.setSpacing(10)

        # Чат(временно)
        self.chat_frame = QFrame()
        self.chat_frame.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.chat_lay.addWidget(self.chat_frame, stretch=1)

        self.chat_frame_lay = QVBoxLayout(self.chat_frame)
        self.chat_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.chat_frame_lay.setSpacing(10)

        self.chat_message = QTextEdit()
        self.chat_message.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border-radius: 8px;
            }
        """)
        self.chat_message.setReadOnly(True)
        self.chat_message.setPlaceholderText("Сообщения появятся здесь...")
        self.chat_frame_lay.addWidget(self.chat_message, stretch=1)

        # Разделение для демки с камеры и вводом текста
        self.bottom_lay = QHBoxLayout()
        self.bottom_lay.setSpacing(10)

        # Поле ввода
        self.send_box = ChatSendBox()
        self.bottom_lay.addWidget(self.send_box, stretch=1)
        # Превью камеры
        self.camera_preview_frame = QFrame()
        self.camera_preview_frame.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.bottom_lay.addWidget(self.camera_preview_frame, stretch=1)

        # Вертикальный лайаут внутри превью камеры
        self.camera_preview_lay = QVBoxLayout(self.camera_preview_frame)
        self.camera_preview_lay.setContentsMargins(10, 10, 10, 10)
        self.camera_preview_lay.setSpacing(5)

        # Картинка с камеры(пока просто текст)
        self.camera_preview_label = QLabel("Картинка с камеры")
        self.camera_preview_label.setStyleSheet(self.settings_text_qss)
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_lay.addWidget(self.camera_preview_label, stretch=1)

        self.chat_lay.addLayout(self.bottom_lay)

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
