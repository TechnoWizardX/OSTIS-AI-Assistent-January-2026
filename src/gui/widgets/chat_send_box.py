from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QTextEdit, QPushButton, QHBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from data.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from gui.main_window import icon_path
from src.utils.BasicUtils import BasicUtils
from gui.signals import ui_signals
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
            BasicUtils.set_settings_config_value("recording_enabled", True)
            ui_signals.voice_input_changed.emit(True)
        else:
            BasicUtils.set_settings_config_value("recording_enabled", False)
            ui_signals.voice_input_changed.emit(False)
    def voice_text_recived(self, text: str):
        self.handle_voice_text(text)


    def handle_voice_text(self, text: str):
        """Обрабатывает распознанный текст (вызывается в главном потоке)"""
        # Защита от дублирования: игнорируем повторяющийся текст
        if self._voice_processing or not text.strip():
            return
        BasicUtils.logger("ChatSendBox", "INFO", f"Распознан голосовой текст: {text}")
        # Проверяем состояние переключателя из настроек
        send_directly = False
        main_window = self.window()
        if hasattr(main_window, 'settings_page'):
            send_directly = main_window.settings_page.is_voice_toggle_checked()

        if send_directly:
            # Отправляем сразу в чат
            BasicUtils.add_message("user", text)
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
            BasicUtils.add_message("user", text)
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
        BasicUtils.add_message("user", text)
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

class DialogBox(QWidget):
    """Чат (здесь отображаются сообщения)"""
    def __init__(self):
        super().__init__()
        # Подключение к сигналу будет сделано извне через set_message_handler
        try:
            ui_signals.message_sent.disconnect(self.add_message)
        except Exception:
            pass
        ui_signals.message_sent.connect(self.add_message)
        ui_signals.history_cleared.connect(self.reload_history)
        ui_signals.typing_started.connect(self.show_typing_indicator)
        ui_signals.typing_finished.connect(self.hide_typing_indicator)
        self._typing_indicator = None
        self._message_handler = None
        self.dialog_box_lay = QVBoxLayout(self)  
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Важно: позволяет контейнеру растягиваться
        self.scroll_area.setStyleSheet(
            THEMES[SELECTED_THEME]["chat_scroll_area"] + THEMES[SELECTED_THEME]["scrollbar"]
        )     
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(THEMES[SELECTED_THEME]["dialog_frame"])
        self.main_frame_lay = QVBoxLayout(self.main_frame)
        self.main_frame_lay.setContentsMargins(10, 10, 10, 10)
        self.main_frame_lay.setSpacing(10)
        self.main_frame_lay.addStretch(10)

        self.scroll_area.setWidget(self.main_frame)
        self.dialog_box_lay.addWidget(self.scroll_area)

        self.load_history()

    def show_typing_indicator(self, author_name: str = "IAMOS"):
        """Показывает анимированный индикатор думания нейросети."""
        if self._typing_indicator is not None:
            return  # уже показан
        self._typing_indicator = TypingIndicator(
            author_name=author_name,
            frame_style=THEMES[SELECTED_THEME].get("message_frame", ""),
            label_style=THEMES[SELECTED_THEME].get("message_author", ""),
        )
        # Применяем тему сразу после создания
        self._typing_indicator._apply_theme(THEMES[SELECTED_THEME])
        count = self.main_frame_lay.count()
        self.main_frame_lay.insertWidget(count - 1, self._typing_indicator)
        self._typing_indicator.start()
        self._scroll_to_bottom()

    def hide_typing_indicator(self):
        """Скрывает и удаляет индикатор думания."""
        if self._typing_indicator is None:
            return
        self._typing_indicator.stop()
        self.main_frame_lay.removeWidget(self._typing_indicator)
        self._typing_indicator.deleteLater()
        self._typing_indicator = None

    def add_message(self, author: str, text: str, time: str = None):
        message = Message(author, text, time)
        count = self.main_frame_lay.count()
        self.main_frame_lay.insertWidget(count - 1, message)   # Без alignment
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        # Используем таймер, чтобы дать Qt время пересчитать размеры виджетов
        QTimer.singleShot(500, self._actual_scroll)

    def _actual_scroll(self):
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
    
    def load_history(self):
        """Загружает историю сообщений."""
        history = BasicUtils.load_chat_history()
        for message in history:
            self.add_message(message["author"], message["text"], message["time"])
    
    def reload_history(self):
        """Очищает текущие сообщения и перезагружает историю из файла"""
        # Удаляем все виджеты сообщений, оставляя только растяжку (последний элемент)
        while self.main_frame_lay.count() > 1:
            item = self.main_frame_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Загружаем историю заново
        self.load_history()        

    def _apply_theme(self, theme: dict):
        """Обновляет стили чата."""
        self.scroll_area.setStyleSheet(theme["chat_scroll_area"] + theme["scrollbar"])
        self.main_frame.setStyleSheet(theme["dialog_frame"])
        
        for i in range(self.main_frame_lay.count()):
            item = self.main_frame_lay.itemAt(i)
            widget = item.widget()

            # Проверяем, что это именно виджет сообщения (чтобы не трогать stretch)
            if isinstance(widget, Message):
                widget._apply_theme(theme)
            elif isinstance(widget, TypingIndicator):
                widget._apply_theme(theme)