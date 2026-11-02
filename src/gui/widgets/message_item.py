from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy, QPushButton, QApplication
from PyQt6.QtCore import QSize, Qt
from datetime import datetime
from src.gui.signals import ui_signals
from src.utils.icons import set_theme_icon
class Message(QWidget):
    def __init__(self, author: str, text: str, time: str = None):
        super().__init__()
        self.setObjectName("message")

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)


        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)

        # Пузырёк сообщения (ширина подстраивается под текст)
        self.main_frame = QFrame()
        self.main_frame.setObjectName("messageFrame")
        self.main_frame.setMinimumWidth(100)
        self.main_frame.setMaximumWidth(500)
        self.main_frame.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(12, 10, 12, 10)
        frame_layout.setSpacing(5)
        
        # Имя автора
        display = "Вы" if author == "user" else author
        self.author_label = QLabel(display)
        self.author_label.setObjectName("messageAuthor")
        frame_layout.addWidget(self.author_label)

        # Текст
        self.text_label = QLabel(text)
        self.text_label.setObjectName("messageText")
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        frame_layout.addWidget(self.text_label)

        # Время
        time_str = time or datetime.now().strftime("%H:%M")
        self.time_label = QLabel(time_str)
        self.time_label.setObjectName("messageTime")
        bottom_lay = QHBoxLayout()
        self.copy_btn = QPushButton()
        self.copy_btn.setObjectName("copyButton")
        set_theme_icon(self.copy_btn, "copy.svg")
        self.copy_btn.setIconSize(QSize(20, 20))
        self.copy_btn.setFixedSize(30, 30)
        self.copy_btn.clicked.connect(self.copy_text)
        bottom_lay.addWidget(self.copy_btn)
        bottom_lay.addStretch()
        bottom_lay.addWidget(self.time_label)
        frame_layout.addLayout(bottom_lay)

        # Кнопка озвучки (динамик)
        self.voice_btn = QPushButton()
        self.voice_btn.setObjectName("checkableButton")
        self.voice_btn.setFixedSize(40, 40)
        set_theme_icon(self.voice_btn, "speaker.svg")
        self.voice_btn.setIconSize(QSize(25, 25))
        
        self.text_content = text                     # сохраняем текст
        self.is_playing = False                      # состояние воспроизведения
        self.voice_btn.setCheckable(True)            # кнопка может быть нажата
        self.voice_btn.clicked.connect(self._on_voice_clicked)

        # Подключаем глобальные сигналы
        ui_signals.speaker_stop_all.connect(self._reset_button)
        ui_signals.speaker_finished.connect(self._reset_button)

        # Расположение: для пользователя кнопка слева, для других — справа
        if author == "user":
            main_layout.addStretch()                                   # прижимаем вправо
            main_layout.addWidget(self.voice_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
            main_layout.addWidget(self.main_frame)
        else:
            main_layout.addWidget(self.main_frame)
            main_layout.addWidget(self.voice_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
            main_layout.addStretch()                   

    def copy_text(self):
        """Копирует текст сообщения в буфер обмена."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_content)     

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
