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
from src.utils.chat_history import add_message
from src.utils.logger import logger
from src.utils.config import set_settings_config_value

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
        self.main_frame.setStyleSheet(THEMES[SELECTED_THEME]["chat_send_box_frame"])
        self.chats_send_box_lay.addWidget(self.main_frame)
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        self.chat_send_input = QTextEdit()
        self.chat_send_input.setStyleSheet(
            THEMES[SELECTED_THEME]["chat_send_input"] + THEMES[SELECTED_THEME]["scrollbar"]
        )
        self.main_frame_lay.addWidget(self.chat_send_input, 1)
        
        # Горизонтальный layout для кнопок
        self.buttons_lay = QHBoxLayout()
        self.buttons_lay.setSpacing(10)
        
        
        self.send_btn = QPushButton("Отправить")
        self.send_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_1"])
        self.send_btn.setFixedSize(130, 45)
        self.send_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.send_btn.setIcon(QIcon(icon_path("send.png")))
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
            self.voice_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_checkable"])
            self.voice_btn.setIcon(QIcon(icon_path("microphone.png")))
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

    def _apply_theme(self, theme: dict):
        """Обновляет стили поля отправки."""
        self.main_frame.setStyleSheet(theme["chat_send_box_frame"])
        self.chat_send_input.setStyleSheet(theme["chat_send_input"] + theme["scrollbar"])
        if hasattr(self, 'voice_btn'):
            self.voice_btn.setStyleSheet(theme["btn_checkable"])
        self.send_btn.setStyleSheet(theme["btn_1"])


           # прижимаем влево
    
    def _on_voice_clicked(self):
        """Обработчик нажатия на кнопку динамика."""
        if self.is_playing:
            # Остановить текущее воспроизведение
            ui_signals.speaker_stop_request.emit()
            self._reset_button()
        else:
            # Сбросить все другие кнопки, затем запустить новое
            ui_signals.speaker_stop_all.emit()
            ui_signals.speaker_pressed.emit(self.text_content)
            self.is_playing = True
        self.voice_btn.setChecked(True)

    def _reset_button(self):
        """Возвращает кнопку в исходное неактивное состояние."""
        self.is_playing = False
        self.voice_btn.setChecked(False)        
        
    def _apply_theme(self, theme: dict):
        self.main_frame.setStyleSheet(theme["message_frame"])
        self.author_label.setStyleSheet(theme["message_author"])
        self.text_label.setStyleSheet(theme["message_text"])
        self.time_label.setStyleSheet(theme["message_time"])
        self.copy_btn.setStyleSheet(theme["btn_1"])
        if hasattr(self, 'voice_btn'):
            base_style = theme.get("btn_checkable", "")
            accent_color = _COLOR_MAP[SELECTED_THEME].get("accent", "#4CAF50")
            self.voice_btn.setStyleSheet(base_style + f"QPushButton:checked {{ background-color: {accent_color}; }}")    
    def copy_text(self):
        """Копирует текст сообщения в буфер обмена."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_content)

