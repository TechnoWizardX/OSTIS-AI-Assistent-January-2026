from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap
import sys
import os
from BasicUtils import BasicUtils, DataBaseEditor
from datetime import datetime

# Добавляем путь к жестам для импорта
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GESTURES_DIR = os.path.join(PROJECT_ROOT, "samples", "GesturesInput")
if GESTURES_DIR not in sys.path:
    sys.path.insert(0, GESTURES_DIR)

from gestures import GestureCameraThread

# Добавляем путь к голосовому вводу для импорта
VOICE_DIR = os.path.join(PROJECT_ROOT, "samples", "VoiceInput")
if VOICE_DIR not in sys.path:
    sys.path.insert(0, VOICE_DIR)

from voiceVosk import init_voice, set_voice_callback, stop_voice, get_voice_text, download_model, MODEL_PATH

# Базовый путь для иконок
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
DATABASE_EDITOR = DataBaseEditor()


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
class Signals(QObject):
    settings_changed = pyqtSignal(dict)
    camera_selected = pyqtSignal(str)
    microphone_selected = pyqtSignal(str)
    profile_updated = pyqtSignal()
    voice_text_received = pyqtSignal(str)  # Сигнал для передачи текста из голосового ввода
    message_sent = pyqtSignal(str, str)
global_signals = Signals()
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

        # Подключаемся на переключение страниц — останавливаем камеру при уходе с жестов
        self.content_panel.currentChanged.connect(self._on_page_changed)

    def _on_page_changed(self, index):
        """При переключении на другую страницу — останавливаем камеру."""
        page = self.content_panel.widget(index)
        if page is not self.gestures_input_page:
            if self.gestures_input_page.camera_thread is not None:
                self.gestures_input_page.stop_camera()

    def closeEvent(self, event):
        """При закрытии окна — останавливаем камеру."""
        self.gestures_input_page.stop_camera()
        super().closeEvent(event)




# ==========================================================
# Виджет отправки сообщений (текстовое поле)
# ==========================================================
class ChatSendBox(QWidget):
    # Сигнал о создании сообщения (ЛОКАЛЬНЫЙ, не глобальный)
    voice_text_ready = pyqtSignal(str)  # Сигнал для безопасной передачи текста из фонового потока

    def __init__(self):
        super().__init__()

        # Для защиты от дублирования голосового ввода
        self._last_voice_text = ""
        self._voice_processing = False

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
        
        # Горизонтальный layout для кнопок
        self.buttons_lay = QHBoxLayout()
        self.buttons_lay.setSpacing(10)
        
        self.voice_btn = QPushButton()
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background-color: #D9D9D9;
                border-radius: 12px;
                border: 3px solid transparent;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #C8C8C8;
                border: 3px solid #888888;
            }
            QPushButton:pressed {
                background-color: #B8B8B8;
                border: 3px solid #666666;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                border: 3px solid #388E3C;
            }
        """)
        self.voice_btn.setIcon(QIcon(icon_path("microphone.png")))
        self.voice_btn.setIconSize(QSize(25, 25))
        self.voice_btn.setCheckable(True)
        self.voice_btn.setFixedSize(45, 45)
        self.voice_btn.setVisible(False)  # Скрываем кнопку по умолчанию
        self.buttons_lay.addWidget(self.voice_btn)
        
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
        self.send_btn.setFixedSize(130, 45)
        self.send_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.send_btn.setIcon(QIcon(icon_path("send.png")))
        self.buttons_lay.addStretch(1)
        self.buttons_lay.addWidget(self.voice_btn)
        self.buttons_lay.addWidget(self.send_btn)
        self.main_frame_lay.addLayout(self.buttons_lay)
        self.send_btn.clicked.connect(self.send_message)

        self.chat_send_input.installEventFilter(self)

        # Подключаем кнопку голоса к переключению записи
        self.voice_btn.clicked.connect(self.toggle_voice_recording)

        # Подключаем сигнал для безопасной обработки текста в главном потоке
        self.voice_text_ready.connect(self.handle_voice_text)

        # Для защиты от дублирования
        self._last_voice_text = ""
        self._voice_processing = False

    def toggle_voice_recording(self, checked: bool):
        """Переключение голосовой записи (вкл/выкл)"""
        if checked:
            # Проверяем наличие модели перед записью
            if not os.path.exists(MODEL_PATH):
                self.voice_btn.setChecked(False)
                msg = QMessageBox(self)
                msg.setWindowTitle("Модель не найдена")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setText("Голосовая модель не загружена")
                msg.setInformativeText(
                    "Для работы голосового ввода необходимо загрузить модель (~50 МБ).\n"
                    "Хотите загрузить сейчас?"
                )
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg.setDefaultButton(QMessageBox.StandardButton.Yes)
                msg.button(QMessageBox.StandardButton.Yes).setText("Загрузить")
                msg.button(QMessageBox.StandardButton.No).setText("Отмена")
                reply = msg.exec()

                if reply == QMessageBox.StandardButton.Yes:
                    result = download_model()
                    if not result:
                        err_msg = QMessageBox(self)
                        err_msg.setWindowTitle("Ошибка")
                        err_msg.setIcon(QMessageBox.Icon.Warning)
                        err_msg.setText("Не удалось загрузить модель")
                        err_msg.setInformativeText("Проверьте подключение к интернету и попробуйте снова.")
                        err_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                        err_msg.exec()
                return

            # Включаем запись
            self._last_voice_text = ""
            self._voice_processing = False
            init_voice()

            # Устанавливаем callback — текст придёт автоматически
            set_voice_callback(self.on_voice_text)

            print("Голосовая запись начата")
        else:
            # Выключаем запись
            stop_voice()
            print("Голосовая запись остановлена")

    def on_voice_text(self, text: str):
        """Вызывается когда распознан текст через голос (из фонового потока!)"""
        # Отправляем сигнал в главный поток для безопасного обновления UI
        self.voice_text_ready.emit(text)

    def handle_voice_text(self, text: str):
        """Обрабатывает распознанный текст (вызывается в главном потоке)"""
        # Защита от дублирования: игнорируем повторяющийся текст
        if text == self._last_voice_text or self._voice_processing or not text.strip():
            return
        print(f"Voice text received: {text}")
        self._voice_processing = True
        self._last_voice_text = text

        # Проверяем состояние переключателя из настроек
        send_directly = False
        main_window = self.window()
        if hasattr(main_window, 'settings_page'):
            send_directly = main_window.settings_page.is_toggle_checked()

        if send_directly:
            # Отправляем сразу в чат
            BasicUtils.add_message("user", text)
            global_signals.message_sent.emit("user", text)
        else:
            # Вставляем текст в поле ввода
            current_text = self.chat_send_input.toPlainText()
            if current_text:
                self.chat_send_input.setPlainText(current_text + " " + text)
            else:
                self.chat_send_input.setPlainText(text)
            # Перемещаем курсор в конец
            cursor = self.chat_send_input.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.chat_send_input.setTextCursor(cursor)

        self._voice_processing = False
        
    def send_message(self):
        text = self.chat_send_input.toPlainText()
        
        if not text:
            return
        BasicUtils.add_message("user", text)
        self.chat_send_input.clear()
        # Посылаем ЛОКАЛЬНЫЙ сигнал
        global_signals.message_sent.emit("user", text)

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

class Message(QWidget):
    def __init__(self, author: str, text: str, time: str = None):
        super().__init__()
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Используем QHBoxLayout для контроля ширины
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
            background-color: #D9D9D9;
            border-radius: 12px;
        """)
        
        # Устанавливаем максимальную ширину
        max_width = 500
        self.main_frame.setMaximumWidth(max_width)
        self.main_frame.setMinimumWidth(100)
        
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(12, 10, 12, 10)
        self.main_frame_lay.setSpacing(5)
        
        if author == "user":
            self.author = "Вы"
        else:
            self.author = author
    
        
        if time is None:
            self.time = datetime.now().strftime("%H:%M")
        else:
            self.time = time

        self.author_label = QLabel(self.author)
        self.author_label.setStyleSheet("""
            color: #666666;
            font-size: 12px;
            font-family: "Roboto";
            background-color: transparent;
            font-weight: bold;
        """)
        
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.text_label.setStyleSheet("""
            color: #000000;
            font-size: 14px;
            font-family: "Roboto";
            background-color: transparent;
            line-height: 1.4;
        """)
        
        self.time_label = QLabel(self.time)
        self.time_label.setStyleSheet("""   
            color: #999999;
            background-color: transparent;
            font-size: 10px;
            font-family: "Roboto";
        """)
        
        # Создаем горизонтальный layout для времени (чтобы прижать вправо)
        time_layout = QHBoxLayout()
        time_layout.addStretch()
        time_layout.addWidget(self.time_label)
        
        self.main_frame_lay.addWidget(self.author_label)
        self.main_frame_lay.addWidget(self.text_label)
        self.main_frame_lay.addLayout(time_layout)
        
        main_layout.addWidget(self.main_frame)
        main_layout.addStretch()  # Прижимаем сообщение влево

class DialogBox(QWidget):
    def __init__(self):
        super().__init__()
        # Подключение к сигналу будет сделано извне через set_message_handler
        try:
            global_signals.message_sent.disconnect(self.add_message)
        except Exception:
            pass
        global_signals.message_sent.connect(self.add_message)
        self._message_handler = None
        self.dialog_box_lay = QVBoxLayout(self)  
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Важно: позволяет контейнеру растягиваться
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            /* Стилизация скроллбара */
            QScrollBar:vertical {
                border: none;
                background-color: #E0E0E0;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #B0B0B0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)     
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
            """)
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        self.main_frame_lay.addStretch(10)

        self.scroll_area.setWidget(self.main_frame)
        self.dialog_box_lay.addWidget(self.scroll_area)

        self.load_history()

    def add_message(self, author: str, text: str, time: str = None):
        print(f"[DialogBox ID: {id(self)}] Добавлено сообщение")
        
        message = Message(author, text, time)
        alignment = Qt.AlignmentFlag.AlignLeft
        if author == "user":
            alignment = Qt.AlignmentFlag.AlignRight
        else:
            alignment = Qt.AlignmentFlag.AlignLeft
        count = self.main_frame_lay.count()
        self.main_frame_lay.insertWidget(count - 1, message, alignment=alignment)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
    
    def load_history(self):
        history = BasicUtils.load_chat_history()
        for message in history:
            self.add_message(message["author"], message["text"], message["time"])
        
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
        
        # Тень при наведении
        self._shadow = QGraphicsDropShadowEffect(self.side_panel_btn)
        self._shadow.setBlurRadius(20)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(4)
        self._shadow.setColor(QColor(0, 0, 0, 120))
        
        self.side_panel_btn.setGraphicsEffect(self._shadow)
        self._shadow.setEnabled(False)
        
        # Обработка наведения
        self.side_panel_btn.enterEvent = lambda e: self._shadow.setEnabled(True)
        self.side_panel_btn.leaveEvent = lambda e: self._shadow.setEnabled(False)

        
# ===========================================================
# КАСТОМНЫЙ ПЕРЕКЛЮЧАТЕЛЬ
# ===========================================================
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

        # Цвета
        self._bg_color_off = QColor("#B0B0B0")
        self._bg_color_on = QColor("#4CAF50")
        self._circle_color = QColor("#FFFFFF")

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
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QPainter, QPainterPath

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


class ToggleSwitchRow(QWidget):
    """Фрейм с меткой и переключателем для настроек"""

    toggled = pyqtSignal(bool)

    def __init__(self, text, parent=None, checked=False):
        super().__init__(parent)
        
        # Основной фрейм
        self.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.setFixedHeight(40)
        
        # Лайаут фрейма
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 15, 10)
        layout.setSpacing(10)
        
        # Текстовая метка
        self.label = QLabel(text)
        layout.addWidget(self.label, 1)
        
        # Переключатель
        self.toggle_switch = ToggleSwitch()
        self.toggle_switch.setChecked(checked)
        layout.addWidget(self.toggle_switch)
        
        # Подключаем сигнал
        self.toggle_switch.toggled.connect(self.toggled.emit)
    
    def isChecked(self):
        return self.toggle_switch.isChecked()
    
    def setChecked(self, state):
        self.toggle_switch.setChecked(state)


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

        available = BasicUtils.get_available_cameras()
        
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

        available_mics = BasicUtils.get_available_microphones()

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
        self.grid_lay.addWidget(self.speaker_frame, 3, 0)
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
        self.grid_lay.setRowStretch(4, 1)

        # Переключатель для голосового ввода
        self.toggle_row_for_voice = ToggleSwitchRow("Отправлять текст из голосового ввода сразу в чат:")
        self.grid_lay.addWidget(self.toggle_row_for_voice, 2, 0)

        # Загружаем настройки из файла
        self._load_settings()

        # Подключаем сигналы для сохранения настроек
        self.camera_dropbox.currentTextChanged.connect(self._on_camera_changed)
        self.microphone_dropbox.currentTextChanged.connect(self._on_microphone_changed)
        self.speaker_dropbox.currentTextChanged.connect(self._on_speaker_changed)
        self.toggle_row_for_voice.toggled.connect(self._on_toggle_changed)

    def _load_settings(self):
        """Загружает настройки из settings_config.json и применяет их к виджетам."""
        settings_config = BasicUtils.load_settings_config()
        
        # Восстанавливаем состояние переключателя
        voice_send_directly = settings_config.get("voice_send_directly", False)
        self.toggle_row_for_voice.setChecked(voice_send_directly)
        
        # Камера (по индексу)
        camera_index = settings_config.get("camera_index", 0)
        if 0 <= camera_index < self.camera_dropbox.count():
            self.camera_dropbox.setCurrentIndex(camera_index)
        
        # Микрофон (по индексу)
        mic_index = settings_config.get("microphone_index", 0)
        if 0 <= mic_index < self.microphone_dropbox.count():
            self.microphone_dropbox.setCurrentIndex(mic_index)
        
        # Диктор (по индексу)
        speaker_index = settings_config.get("speaker_index", 0)
        if 0 <= speaker_index < self.speaker_dropbox.count():
            self.speaker_dropbox.setCurrentIndex(speaker_index)

    def _on_camera_changed(self, text):
        """Сохраняет выбранную камеру."""
        index = self.camera_dropbox.currentIndex()
        BasicUtils.set_settings_config_value("camera_index", index)
        global_signals.settings_changed.emit({"camera": text})

    def _on_microphone_changed(self, text):
        """Сохраняет выбранный микрофон."""
        index = self.microphone_dropbox.currentIndex()
        BasicUtils.set_settings_config_value("microphone_index", index)
        global_signals.settings_changed.emit({"microphone": text})

    def _on_speaker_changed(self, text):
        """Сохраняет выбранного диктора."""
        index = self.speaker_dropbox.currentIndex()
        BasicUtils.set_settings_config_value("speaker_index", index)
        global_signals.settings_changed.emit({"speaker": text})

    def _on_toggle_changed(self, state):
        """Сохраняет состояние переключателя."""
        BasicUtils.set_settings_config_value("voice_send_directly", state)
        global_signals.settings_changed.emit({"voice_send_directly": state})



    def get_current_camera(self):
        return self.camera_dropbox.currentText()

    def get_current_microphone(self):
        return self.microphone_dropbox.currentText()

    def is_toggle_checked(self):
        """Возвращает состояние переключателя (True/False)"""
        return self.toggle_row_for_voice.isChecked()

    def get_current_speaker(self):
        return self.speaker_dropbox.currentText()

# ===========================================================
# ПРОФИЛЬ
# ===========================================================
class ProfileOption(QFrame):
    """
    Виджет строки профиля: Название | Значение | Кнопки управления.
    Поддерживает режимы: только чтение ↔ редактирование.
    """
    value_changed = pyqtSignal(str, str)  # name, new_value

    def __init__(self, name: str, value: str, can_edit: bool = False, 
                 table_name: str = None, columns: list = None, several_columns: bool = False, parent=None):
        super().__init__(parent)
        # имя таблицы, список затрагиваемых колон, признак нескольких колонок 
        # (если есть то потом всё разделяется, нужно указываеть всё в точном порядке)
        self.table_name = table_name
        self.columns = columns
        self.several_columns = several_columns

        self.setStyleSheet("""
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.text_qss = """
            color: #000000;
            font-size: 16px;
        """
        self.setFixedHeight(35)
        self._name = name
        self._current_value = value

        # Лэйаут
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(10, 5, 5, 10)
        self.lay.setSpacing(10)

        # Название (слева)
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(self.text_qss)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        self.lay.addWidget(self.name_label, 1)

        # Вертикальная линия-разделитель
        self.line = QFrame()
        self.line.setMaximumWidth(2)
        self.line.setFrameShape(QFrame.Shape.VLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.line.setStyleSheet("""color: #000000;
            background-color: #000000;""")
        self.lay.addWidget(self.line, Qt.AlignmentFlag.AlignLeft)
        
        # Значение (Label для отображения, QLineEdit для редактирования)
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(self.text_qss)
        self.value_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        self.value_edit = QLineEdit(value)
        self.value_edit.setStyleSheet(self.text_qss + "background: transparent; border: none;")
        self.value_edit.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)
        self.value_edit.setVisible(False)  # Скрыто по умолчанию
        self.lay.addWidget(self.value_label, 3)
        self.lay.addWidget(self.value_edit, 3)

        # Кнопка "Редактировать" (карандаш)
        if can_edit:
            self.btn_edit = QPushButton()
            self.btn_edit.setIcon(QIcon(icon_path("pencil.png")))
            self.btn_edit.setIconSize(QSize(20, 20))
            self.btn_edit.setFixedSize(25, 25)
            self.btn_edit.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border-radius: 15px;
                    color: white;
                    font-size: 16px;
                }
                QPushButton:hover { background-color: transparent; }
                QPushButton:pressed { background-color: transparent; }
            """)
            self.btn_edit.clicked.connect(self._start_editing)
            self.lay.addWidget(self.btn_edit)

            # Кнопка "Завершить" (галочка) — скрыта по умолчанию
            self.btn_save = QPushButton()
            self.btn_save.setIcon(QIcon(icon_path("accept.png")))
            self.btn_save.setIconSize(QSize(20, 20))
            self.btn_save.setFixedSize(25, 25)
            self.btn_save.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border-radius: 15px;
                    color: white;
                    font-size: 16px;
                }
                QPushButton:hover { background-color: transparent; }
                QPushButton:pressed { background-color: transparent; }
            """)
            self.btn_save.clicked.connect(self._finish_editing)
            self.btn_save.setVisible(False)
            self.lay.addWidget(self.btn_save)

    def _start_editing(self):
        """Переключает в режим редактирования."""
        self.value_label.setVisible(False)
        self.value_edit.setVisible(True)
        self.value_edit.setText(self._current_value)
        self.value_edit.setFocus()

        self.btn_edit.setVisible(False)
        self.btn_save.setVisible(True)

    def _finish_editing(self):
        """Завершает редактирование и сохраняет значение."""
        new_value = self.value_edit.text().strip()

        if not new_value:
            return  # Не сохраняем пустое значение

        self._current_value = new_value
        self.value_label.setText(self._current_value)
        self.value_label.setVisible(True)
        self.value_edit.setVisible(False)
        self.btn_edit.setVisible(True)
        self.btn_save.setVisible(False)


        # ============================================
        # ЗДЕСЬ ВЫПОЛНЯЮТСЯ ДЕЙСТВИЯ ПОСЛЕ СОХРАНЕНИЯ:
        # ============================================
        # КАК РАБОТАЕТ: 
        # Если у нас флаг того, что опция составная и содержит в себе несколько колонок для редактирования,
        # то мы перебираем все колонки и сохраняем в каждую по отдельности
        # при этом ОБЯЗАТЕЛЬНО количество значений в результате должно быть равно количеству колонок 
        self.id = 0
        if self.several_columns:
            new_value = new_value.split()
            updates = dict(zip(self.columns, new_value))
        else:
            updates = {self.columns[0] : new_value[0]}
        DATABASE_EDITOR.update_data(self.table_name, updates, self.id)
        global_signals.profile_updated.emit()

    def get_value(self) -> str:
        """Возвращает текущее значение."""
        return self._current_value


class Profile(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Профиль")
        self.side_panel_btn.setIcon(QIcon(icon_path("profile.png")))
        
        
        self.profile_lay = QVBoxLayout(self)
        self.profile_lay.setContentsMargins(0, 0, 0, 0)
        # Главная рамка
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet("""
            background-color: #FFFFFF;
            border-radius: 16px;
        """)
        self.profile_lay.addWidget(self.main_frame)
        
        # Главный лайаут
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        # Лайаут "шапки" профиля
        self.head_data_lay = QHBoxLayout()
        self.head_data_lay.setContentsMargins(0, 0, 0, 0)
        self.head_data_lay.setSpacing(10)

        self.photo_frame = QFrame()
        self.photo_frame.setStyleSheet(""" 
            background-color: #D3D3D3;
            border-radius: 12px;
        """)
        self.photo_frame.setFixedSize(150, 150)
        self.photo_frame_lay = QVBoxLayout(self.photo_frame)
        self.profile_picture = QLabel()
        self.profile_picture.setPixmap(QPixmap(icon_path("user.png")))
        self.profile_picture.setFixedSize(100, 100)
        self.profile_picture.setScaledContents(True)
        self.photo_frame.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.photo_frame_lay.addWidget(self.profile_picture, alignment=Qt.AlignmentFlag.AlignCenter)

        self.head_data_lay.addWidget(self.photo_frame, 1, Qt.AlignmentFlag.AlignLeft)
        self.photo_frame.setFixedWidth(150)
        self.head_data_label_lay = QVBoxLayout()
        self.head_data_label_lay.setContentsMargins(0, 0, 0, 0)
        self.head_data_label_lay.setSpacing(0)
        # sn_fn_patr - surname, firstname, patronymic - фамилия имя отчество
        self._surname = DATABASE_EDITOR.get_data("Users", "surname", 0)[0][0]
        self._firstname = DATABASE_EDITOR.get_data("Users", "firstname", 0)[0][0]
        self._patronymic = DATABASE_EDITOR.get_data("Users", "patronymic", 0)[0][0]
        self._sn_fn_patr = f"{self._surname} {self._firstname} {self._patronymic}"
        self._birthday = DATABASE_EDITOR.get_data("Users", "birthday", 0)[0][0]
        self._gender = DATABASE_EDITOR.get_data("Users", "gender", 0)[0][0]

        # СТРОГО указываем, в каком порядке вводятся данные: Ф И О, и обозначаем колонки
        self.sn_fn_patr =  ProfileOption("ФИО", self._sn_fn_patr if self._sn_fn_patr else 'Не указано', True,
                                         "Users", ["surname", "firstname", "patronymic"], True)
        self.birthday = ProfileOption("Дата рождения", self._birthday if self._birthday else 'Не указано', True, "Users", ["birthday"])
        self.gender = ProfileOption("Пол", self._gender if self._gender else 'Не указано', True, "Users", ["gender"])
 

        self.head_data_label_lay.addWidget(self.sn_fn_patr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.head_data_label_lay.addWidget(self.birthday, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.head_data_label_lay.addWidget(self.gender, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        self.head_data_lay.addLayout(self.head_data_label_lay)
        self.head_data_lay.addStretch(10)
        

        self.main_frame_lay.addLayout(self.head_data_lay)

        
        self._dysfunctions = DATABASE_EDITOR.get_data("Users", "dysfunctions", 0)[0][0]
        self.dysfunctions = ProfileOption("Нарушения", f"{self._dysfunctions if self._dysfunctions else 'Не указано'}", True, "Users",["dysfunctions"])
        self.main_frame_lay.addWidget(self.dysfunctions, Qt.AlignmentFlag.AlignLeft)

        self._adaptive = DATABASE_EDITOR.get_data("Users", "adaptation_status", 0)[0][0] 
        self.adaptive = ProfileOption("Степень адаптации системы", f"{self._adaptive if self._adaptive else 'Отсутствует'}", False)
        self.main_frame_lay.addWidget(self.adaptive, Qt.AlignmentFlag.AlignLeft)
        
        self._fatigue = None
        self.fatigue = ProfileOption("Усталость", f"{self._fatigue if self._fatigue else 'Отсутствует'}", False)
        self.main_frame_lay.addWidget(self.fatigue, Qt.AlignmentFlag.AlignLeft)


        
        self.main_frame_lay.addStretch(1)
# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 16px;
               }
        """)
        self.side_panel_btn.setText("Голосовой Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("microphone.png")))
        self.text_input_lay = QVBoxLayout(self)
        self.text_input_lay.setContentsMargins(0, 0, 0, 0)
        self.dialog_box = DialogBox()
        self.send_box = ChatSendBox()

        # Подключаем ЛОКАЛЬНЫЙ сигнал send_box к диалогу
       

        # Показываем кнопку микрофона (скрыта по умолчанию)
        # Кнопка уже подключена в ChatSendBox к toggle_voice_recording
        self.send_box.voice_btn.setVisible(True)

        self.text_input_lay.addWidget(self.dialog_box, 2)
        self.text_input_lay.addWidget(self.send_box, 1)


            

# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 16px;
               }
        """)
        self.side_panel_btn.setText("Текстовый Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("text.png"))) 
        self.text_input_lay = QVBoxLayout(self)
        self.text_input_lay.setContentsMargins(0, 0, 0, 0)
        self.dialog_box = DialogBox()
        self.send_box = ChatSendBox()
        # Подключаем ЛОКАЛЬНЫЙ сигнал send_box к диалогу
      

        self.text_input_lay.addWidget(self.dialog_box, 2)
        self.text_input_lay.addWidget(self.send_box, 1)

# ===========================================================
# ЖЕСТОВЫЙ ВВОД
# ===========================================================
class GesturesInput(ContentPageWidget):

    def __init__(self):
        super().__init__()
        
        self.side_panel_btn.setText("Жестовый Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("camera.png")))

        # Поток камеры (создаётся при старте)
        self.camera_thread = None

        # Вертикальный лайаут всей страницы
        self.chat_lay = QVBoxLayout(self)
        self.chat_lay.setContentsMargins(15, 15, 15, 15)
        self.chat_lay.setSpacing(10)

        # Чат===============================================================
        self.dialog_box = DialogBox()
        #===============================================================================
        
        # Разделение для демки с камеры и вводом текста
        self.bottom_lay = QHBoxLayout()
        self.bottom_lay.setSpacing(10)
        # Поле ввода
        self.send_box = ChatSendBox()
        # Подключаем ЛОКАЛЬНЫЙ сигнал send_box к диалогу

        self.chat_lay.addWidget(self.dialog_box, stretch=2)
        self.bottom_lay.addWidget(self.send_box, stretch=1)

        # Правая часть: превью камеры + кнопки управления
        self.camera_frame = QFrame()
        self.camera_frame.setStyleSheet("""
            QFrame {
                background-color: #D3D3D3;
                border-radius: 12px;
            }
        """)
        self.bottom_lay.addWidget(self.camera_frame, stretch=2)

        self.camera_lay = QVBoxLayout(self.camera_frame)
        self.camera_lay.setContentsMargins(10, 10, 10, 10)
        self.camera_lay.setSpacing(5)

        # Лейбл для отображения кадра (тоже скруглённые углы)
        self.camera_preview_label = QLabel("Нажмите «Старт» для запуска")
        self.camera_preview_label.setStyleSheet("""
            QLabel {
                background-color: #A8A8A8;
                border-radius: 8px;
            }
        """)
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_label.setMinimumSize(320, 240)
        self.camera_preview_label.setScaledContents(False)
        self.camera_lay.addWidget(self.camera_preview_label, stretch=1)

        # Кнопки старт/стоп снизу
        self.camera_btn_lay = QHBoxLayout()
        self.camera_btn_lay.setSpacing(10)

        self.start_btn = QPushButton("Старт")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-family: "Roboto";
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_btn.clicked.connect(self.start_camera)
        self.camera_btn_lay.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-family: "Roboto";
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)
        self.camera_btn_lay.addWidget(self.stop_btn)

        self.camera_lay.addLayout(self.camera_btn_lay)

        self.chat_lay.addLayout(self.bottom_lay)

    def start_camera(self):

        if self.camera_thread is not None and self.camera_thread.isRunning():
            return

        self.camera_thread = GestureCameraThread(camera_index=0)
        self.camera_thread.frame_ready.connect(self.on_frame_ready)
        self.camera_thread.status_ready.connect(self.on_status_ready)
        self.camera_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_camera(self):
        """Останавливает поток камеры."""
        if self.camera_thread is not None and self.camera_thread.isRunning():
            # Отключаем сигналы перед остановкой
            self.camera_thread.frame_ready.disconnect()
            self.camera_thread.status_ready.disconnect()
            self.camera_thread.stop()
            self.camera_thread = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        # Сбрасываем картинку, показываем заглушку
        self.camera_preview_label.clear()
        self.camera_preview_label.setText("Нажмите «Старт» для запуска")

    def _rounded_image(self, image: QImage, radius: int = 12) -> QImage:
        """Возвращает изображение со скруглёнными углами."""
        result = QImage(image.size(), QImage.Format.Format_ARGB32)
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, image.width(), image.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawImage(0, 0, image)
        painter.end()

        return result

    def on_frame_ready(self, q_image: QImage):
        """Слот для отображения кадра с камеры."""
        if q_image.isNull():
            return

        # Масштабируем изображение под размер лейбла
        label_size = self.camera_preview_label.size()
        scaled_image = q_image.scaled(
            label_size.width(),
            label_size.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        # Скругляем углы
        rounded = self._rounded_image(scaled_image, radius=8)
        pixmap = QPixmap.fromImage(rounded)
        self.camera_preview_label.setPixmap(pixmap)

    def on_status_ready(self, status: str):
        """Слот для отображения статуса жестов."""

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
