from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy, QPushButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize, Qt
from datetime import datetime
from themes import THEMES, SELECTED_THEME, _COLOR_MAP
from gui.main_window import icon_path
from gui.signals import ui_signals
class Message(QWidget):
    def __init__(self, author: str, text: str, time: str = None):
        super().__init__()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)


        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(5)

        # Пузырёк сообщения (ширина подстраивается под текст)
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(THEMES[SELECTED_THEME]["message_frame"])
        self.main_frame.setMinimumWidth(100)
        self.main_frame.setMaximumWidth(500)
        self.main_frame.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(12, 10, 12, 10)
        frame_layout.setSpacing(5)
        
        # Имя автора
        display = "Вы" if author == "user" else author
        self.author_label = QLabel(display)
        self.author_label.setStyleSheet(THEMES[SELECTED_THEME]["message_author"])
        frame_layout.addWidget(self.author_label)

        # Текст
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(THEMES[SELECTED_THEME]["message_text"])
        self.text_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        frame_layout.addWidget(self.text_label)

        # Время
        time_str = time or datetime.now().strftime("%H:%M")
        self.time_label = QLabel(time_str)
        self.time_label.setStyleSheet(THEMES[SELECTED_THEME]["message_time"])
        bottom_lay = QHBoxLayout()
        self.copy_btn = QPushButton()
        self.copy_btn.setIcon(QIcon(icon_path("copy.png")))
        self.copy_btn.setIconSize(QSize(20, 20))
        self.copy_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_1"])
        self.copy_btn.setFixedSize(30, 30)
        self.copy_btn.clicked.connect(self.copy_text)
        bottom_lay.addWidget(self.copy_btn)
        bottom_lay.addStretch()
        bottom_lay.addWidget(self.time_label)
        frame_layout.addLayout(bottom_lay)

        # Кнопка озвучки (динамик)
        self.voice_btn = QPushButton()
        self.voice_btn.setFixedSize(40, 40)
        accent_color = _COLOR_MAP[SELECTED_THEME].get("accent", "#4CAF50")
        self.voice_btn.setStyleSheet(THEMES[SELECTED_THEME].get("btn_checkable", "") +
                                     f"QPushButton:checked {{ background-color: {accent_color}; }}")
        self.voice_btn.setIcon(QIcon(icon_path("speaker.png")))
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