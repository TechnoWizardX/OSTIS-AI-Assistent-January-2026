from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QPushButton, QTextEdit,
                             QVBoxLayout, QWidget)

from src.gui.signals import ui_signals
from src.utils.chat_history import add_message
from src.utils.config_manager import set_settings_config_value
from src.utils.icons import set_theme_icon
from src.utils.logger import logger


class ChatSendBox(QWidget):
    """Виджет отправки сообщений."""
    # Сигналы для безопасной передачи текста из фоновых потоков
    gesture_text_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self._last_send_time = None
        self._voice_processing = False

        self._gesture_processing = False

        self.chats_send_box_lay = QVBoxLayout(self)
        self.main_frame = QFrame()
        self.main_frame.setObjectName("chatSendBoxFrame")
        self.chats_send_box_lay.addWidget(self.main_frame)
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        self.chat_send_input = QTextEdit()
        self.chat_send_input.setObjectName("chatSendInput")
        self.main_frame_lay.addWidget(self.chat_send_input, 1)
        
        # Горизонтальный layout для кнопок
        self.buttons_lay = QHBoxLayout()
        self.buttons_lay.setSpacing(10)
        
        
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.setFixedSize(130, 45)
        self.send_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        set_theme_icon(self.send_btn, "send.svg")
        self.buttons_lay.addStretch(1)
        
        self.buttons_lay.addWidget(self.send_btn)
        self.main_frame_lay.addLayout(self.buttons_lay)
        self.send_btn.clicked.connect(self.send_message)

        self.chat_send_input.installEventFilter(self)
        self.gesture_text_ready.connect(self.handle_gesture_command)
       

        # Для защиты от дублирования
        self._gesture_processing = False
        
    def addVoiceButton(self):
            self.voice_btn = QPushButton()
            self.voice_btn.setObjectName("checkableButton")
            set_theme_icon(self.voice_btn, "microphone.svg")
            self.voice_btn.setIconSize(QSize(25, 25))
            self.voice_btn.setCheckable(True)
            self.voice_btn.setFixedSize(45, 45)
            self.voice_btn.setVisible(False)  # Скрываем кнопку по умолчанию
            self.buttons_lay.addWidget(self.voice_btn)
    
            # Подключаем кнопку голоса к переключению записи
            self.voice_btn.clicked.connect(self.toggle_voice_recording)
            ui_signals.voice_message_received.connect(self.voice_text_recived)
        # Подключаем сигнал для безопасной обработки текста в главном потоке
    def showVoiceButton(self):
        self.voice_btn.setVisible(True)

    def toggle_voice_recording(self, checked: bool):
        """Переключение голосовой записи (вкл/выкл)"""
        if checked:
            set_settings_config_value("recording_enabled", True)
            ui_signals.voice_input_changed.emit(True)
        else:
            set_settings_config_value("recording_enabled", False)
            ui_signals.voice_input_changed.emit(False)
    def voice_text_recived(self, text: str):
        self.handle_voice_text(text)


    def handle_voice_text(self, text: str):
        """Обрабатывает распознанный текст (вызывается в главном потоке)"""
        # Защита от дублирования: игнорируем повторяющийся текст
        if self._voice_processing or not text.strip():
            return
        logger("ChatSendBox", "INFO", f"Распознан голосовой текст: {text}")
        # Проверяем состояние переключателя из настроек
        send_directly = False
        main_window = self.window()
        if hasattr(main_window, 'settings_page'):
            send_directly = main_window.settings_page.is_voice_toggle_checked()

        if send_directly:
            # Отправляем сразу в чат
            add_message("user", text)
            ui_signals.message_sent.emit("user", text)
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


    def handle_gesture_command(self, text: str):
        """Обрабатывает команду из жестового ввода (действие + объект)"""
        # Защита от дублирования
        if text == self._last_gesture_text or self._gesture_processing or not text.strip():
            return
        print(f"Gesture command received: {text}")
        self._gesture_processing = True
        self._last_gesture_text = text

        # Проверяем состояние переключателя из настроек
        send_directly = False
        main_window = self.window()
        if hasattr(main_window, 'settings_page'):
            send_directly = main_window.settings_page.is_gesture_toggle_checked()

        if send_directly:
            # Отправляем сразу в чат
            add_message("user", text)
            ui_signals.message_sent.emit("user", text)
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

        self._gesture_processing = False

    def send_message(self):
        """Отправка сообщения"""
        text = self.chat_send_input.toPlainText()
        
        if not text:
            return
        add_message("user", text)
        self.chat_send_input.clear()

        ui_signals.message_sent.emit("user", text)

    def eventFilter(self, obj, event):
        """Фильтр для отправки сообщений по нажатию Enter"""
        if obj == self.chat_send_input and event.type() == event.Type.KeyPress:
        # Проверяем, нажат ли Enter (обычный или на NumPad)
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Проверяем, НЕ зажат ли Shift (чтобы Shift+Enter делал новую строку)
                if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.send_message()
                    return True  # Возвращаем True, чтобы QTextEdit не вставил перенос строки
    
    # Для всех остальных событий используем стандартную обработку
        return super().eventFilter(obj, event)

           # прижимаем влево
    
        
