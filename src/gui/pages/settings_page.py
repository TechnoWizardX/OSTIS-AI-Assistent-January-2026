from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon

from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from src.gui.widgets.settings_section import SettingsSectionLabel
from src.gui.widgets.toggle_switch import ToggleSwitchRow, ToggleSwitchState
from src.gui import icon_path
from src.gui.signals import ui_signals

from src.utils.config import load_settings_config, set_settings_config_value, get_settings_config_value
from src.utils.devices import get_available_cameras, get_available_microphones
from src.utils.logger import logger
from .base_input_page import ContentPageWidget

class SettingsPage(ContentPageWidget):
    def __init__(self, api_key = ""):
        
        super().__init__()

        self.available_voices = get_settings_config_value("available_silero_voices")
        self.available_voices_reversed = get_settings_config_value("available_silero_voices_reversed")
        self.side_panel_btn.setText("Настройки")
        self.side_panel_btn.setIcon(QIcon(icon_path("settings.png")))
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.setSpacing(0)

        # Скролл-область для настроек
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(THEMES[SELECTED_THEME]["scrollbar"])
        self.main_lay.addWidget(self.scroll_area)

        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(THEMES[SELECTED_THEME]["dialog_frame"])
        # сетка-панель настроек
        self.scroll_area.setWidget(self.main_frame)
        self.grid_lay = QGridLayout(self.main_frame)
        self.grid_lay.setContentsMargins(10, 10, 10, 10)

        # ================================================
        # Блок переключателей (сверху)
        self._section_input = SettingsSectionLabel("Ввод")
        self.grid_lay.addWidget(self._section_input, 0, 0)

        # Переключатель для голосового ввода
        self.toggle_row_for_voice = ToggleSwitchRow("Отправлять текст из голосового ввода сразу в чат:")
        self.grid_lay.addWidget(self.toggle_row_for_voice, 1, 0)

        # Переключатель для жестового ввода
        self.toggle_row_for_gesture = ToggleSwitchRow("Отправлять текст из жестового ввода сразу в чат:")
        self.grid_lay.addWidget(self.toggle_row_for_gesture, 2, 0)

        self._section_ai = SettingsSectionLabel("Облачный ИИ")
        self.grid_lay.addWidget(self._section_ai, 3, 0)

        # Переключатель облачного ИИ
        self.use_onlie_model = ToggleSwitchRow("Использовать облачный ИИ (требуется API ключ)")
        self.grid_lay.addWidget(self.use_onlie_model, 4, 0)

        # Переключатель доступа к персональным данным
        self.online_model_allows = ToggleSwitchRow("Разрешить облачному ИИ доступ к персональным данным")
        self.grid_lay.addWidget(self.online_model_allows, 5, 0)

        # Переключатель озвучивания рекомендации
        self.tts_recommendation_toggle = ToggleSwitchRow("Озвучивать рекомендацию при её получении")
        self.grid_lay.addWidget(self.tts_recommendation_toggle, 6, 0)

        # Создаём объекты для сохранения состояний переключателей
        self.voice_toggle_state = ToggleSwitchState("voice_send_directly")
        self.gesture_toggle_state = ToggleSwitchState("gesture_send_directly")
        self.use_online_model_state = ToggleSwitchState("use_online_model")
        self.online_model_allows_state = ToggleSwitchState("allow_online_model_user_info")
        self.tts_recommendation_state = ToggleSwitchState("tts_recommendation_always")

        # ================================================
        self._section_devices = SettingsSectionLabel("Устройства")
        self.grid_lay.addWidget(self._section_devices, 7, 0)

        # фрейм для выбора камеры
        self.camera_frame = QFrame()
        self.camera_frame.setStyleSheet(THEMES[SELECTED_THEME]["settings_frame"])
        self.camera_frame.setFixedHeight(40)
        self.grid_lay.addWidget(self.camera_frame, 8, 0)
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

        
        self.microphone_frame = QFrame()
        self.microphone_frame.setStyleSheet(THEMES[SELECTED_THEME]["settings_frame"])
        self.microphone_frame.setFixedHeight(40)
        self.grid_lay.addWidget(self.microphone_frame, 9, 0)
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

        available_mics = get_available_microphones()

        if available_mics:
            self.microphone_dropbox.addItems(available_mics)
        else:
            self.microphone_dropbox.addItem("Нет доступных микрофонов")

        self.microphone_frame_lay.addWidget(self.microphone_label, 1)
        self.microphone_frame_lay.addWidget(self.microphone_dropbox, 1)


        self.speaker_frame = QFrame()
        self.speaker_frame.setStyleSheet(THEMES[SELECTED_THEME]["settings_frame"])
        self.speaker_frame.setFixedHeight(40)
        self.grid_lay.addWidget(self.speaker_frame, 10, 0)
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
        self.speaker_dropbox.addItems(list(self.available_voices.keys()))
        self.speaker_frame_lay.addWidget(self.speaker_label, 1)
        self.speaker_frame_lay.addWidget(self.speaker_dropbox, 1)

        

        # ================================================
        # Область тем
        self._section_themes = SettingsSectionLabel("Оформление")
        self.grid_lay.addWidget(self._section_themes, 11, 0)

        self.theme_frame = QFrame()
        self.theme_frame.setStyleSheet(THEMES[SELECTED_THEME]["settings_frame"])
        self.theme_frame_lay = QGridLayout(self.theme_frame)

        themes_list = [
            ("Светлая", "light"),
            ("Тёмная", "dark"),
            ("Twilight", "twilight"),
            ("VS Code", "vs_code"),
            ("Nord", "nord"),
            ("Gruvbox", "gruvbox"),
        ]
        self._theme_buttons = []
        for i, (label, theme_key) in enumerate(themes_list):
            row, col = divmod(i, 3)
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, k=theme_key: self._on_theme_changed(k))
            btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_theme"])
            self.theme_frame_lay.addWidget(btn, row, col)
            self._theme_buttons.append(btn)

        self.grid_lay.addWidget(self.theme_frame, 12, 0)
        # ================================================
        # API ключ
        self._section_api = SettingsSectionLabel("API")
        self.grid_lay.addWidget(self._section_api, 13, 0)

        self.api_frame = QFrame()
        self.api_frame.setStyleSheet(THEMES[SELECTED_THEME]["settings_frame"])
        self.api_frame_lay = QHBoxLayout(self.api_frame)

        self.api_label = QLabel("API Ключ")
        self.api_label.setStyleSheet(self.settings_text_qss)
        self.api_frame_lay.addWidget(self.api_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setText(api_key)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Введите sk-or-v1-...")
        self.api_key_input.setStyleSheet(THEMES[SELECTED_THEME]["settings_input"])
        self.api_frame_lay.addWidget(self.api_key_input)
        
        self.show_api_key = QPushButton()
        self.show_api_key.setFixedSize(30, 30)
        self.show_api_key.setCheckable(True)
        self.show_api_key.setIcon(QIcon(icon_path("hide.png")))
        self.show_api_key.setIconSize(QSize(20, 20))
        self.show_api_key.clicked.connect(self._toggle_api_key_visibility)
        self.show_api_key.setStyleSheet(THEMES[SELECTED_THEME]["btn_transparent"])

        self.api_frame_lay.addWidget(self.show_api_key)

        self.save_key_btn = QPushButton("Сохранить")
        self.save_key_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_1"])
        self.save_key_btn.clicked.connect(self._save_api_key)
        self.api_frame_lay.addWidget(self.save_key_btn)

        self.grid_lay.addWidget(self.api_frame, 14, 0)

        self.other_section = SettingsSectionLabel("Прочее")
        self.grid_lay.addWidget(self.other_section, 15, 0)
        self.auto_voice_toggle = ToggleSwitchRow("Автоматически озвучивать ответы ИИ")
        self.auto_voice_state = ToggleSwitchState("auto_tts")
        self.grid_lay.addWidget(self.auto_voice_toggle, 16, 0)

        self.grid_lay.setRowStretch(15, 1)
        # Загружаем настройки из файла
        self._load_settings()


        # Подключаем сигналы для сохранения настроек
        self.camera_dropbox.currentTextChanged.connect(self._on_camera_changed)
        self.microphone_dropbox.currentTextChanged.connect(self._on_microphone_changed)
        self.speaker_dropbox.currentTextChanged.connect(self._on_speaker_changed)
        self.toggle_row_for_voice.toggled.connect(self.voice_toggle_state.save)
        self.toggle_row_for_gesture.toggled.connect(self.gesture_toggle_state.save)
        self.use_onlie_model.toggled.connect(self.use_online_model_state.save)
        self.online_model_allows.toggled.connect(self.online_model_allows_state.save)
        self.tts_recommendation_toggle.toggled.connect(self.tts_recommendation_state.save)   
        self.auto_voice_toggle.toggled.connect(self.auto_voice_state.save)
    
    def _toggle_api_key_visibility(self):
        if self.show_api_key.isChecked():
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_api_key.setIcon(QIcon(icon_path("show.png")))
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_api_key.setIcon(QIcon(icon_path("hide.png")))

    def _save_api_key(self):
        new_key = self.api_key_input.text().strip()
        if new_key:
            ui_signals.openrouter_api_key_changed.emit(new_key)
            QMessageBox.information(self, "Успех", "API ключ сохранен и обновлен")

    def _load_settings(self):
        """Загружает настройки из settings_config.json и применяет их к виджетам."""
        settings_config = load_settings_config()

        # Восстанавливаем состояния переключателей
        self.toggle_row_for_voice.setChecked(self.voice_toggle_state.load())
        self.toggle_row_for_gesture.setChecked(self.gesture_toggle_state.load())
        self.use_onlie_model.setChecked(self.use_online_model_state.load())
        self.online_model_allows.setChecked(self.online_model_allows_state.load())
        self.tts_recommendation_toggle.setChecked(self.tts_recommendation_state.load())
        self.auto_voice_toggle.setChecked(self.auto_voice_state.load())
        # Камера (по индексу)
        camera_index = settings_config.get("camera_index", 0)
        if 0 <= camera_index < self.camera_dropbox.count():
            self.camera_dropbox.setCurrentIndex(camera_index)
        
        # Микрофон (по индексу)
        mic_index = settings_config.get("microphone_index", 0)
        if 0 <= mic_index < self.microphone_dropbox.count():
            self.microphone_dropbox.setCurrentIndex(mic_index)
        
        # Диктор (по индексу)
        speaker = settings_config.get("tts_voice", "xenia")
        self.speaker_dropbox.setCurrentText(self.available_voices_reversed[speaker])

        # Тема
        theme = settings_config.get("theme", "light")
        self._on_theme_changed(theme)

    def _on_camera_changed(self, text):
        """Сохраняет выбранную камеру."""
        index = self.camera_dropbox.currentIndex()
        set_settings_config_value("camera_index", index)
        ui_signals.settings_changed.emit({"camera": text})

    def _on_microphone_changed(self, text):
        """Сохраняет выбранный микрофон."""
        index = self.microphone_dropbox.currentIndex()
        set_settings_config_value("microphone_index", index)
        ui_signals.settings_changed.emit({"microphone": text})

    def _on_speaker_changed(self, text):
        """Сохраняет выбранного диктора."""
        set_settings_config_value("tts_voice", self.available_voices[text])
        ui_signals.settings_changed.emit({"tts_voice": self.available_voices[text]})

    def _on_theme_changed(self, theme_name: str):
        """Сохраняет выбранную тему."""
        set_settings_config_value("theme", theme_name)
        ui_signals.settings_changed.emit({"theme": theme_name})

    def _apply_theme(self, theme: dict):
        """Обновляет все стили страницы настроек."""
        super()._apply_theme(theme)
        # Получаем имя текущей темы для доступа к цветам
        theme_name = get_settings_config_value("theme") or "light"
        colors = _COLOR_MAP.get(theme_name, _COLOR_MAP["light"])
        
        self.main_frame.setStyleSheet(theme["dialog_frame"])
        self.scroll_area.setStyleSheet(theme["scrollbar"])
        for frame in [self.camera_frame, self.microphone_frame, self.speaker_frame, self.theme_frame, self.api_frame]:
            frame.setStyleSheet(theme["settings_frame"])
        for label in [self.camera_label, self.microphone_label, self.speaker_label, self.api_label]:
            label.setStyleSheet(self.settings_text_qss)
        for combo in [self.camera_dropbox, self.microphone_dropbox, self.speaker_dropbox]:
            combo.setStyleSheet(self.dropbox_qss)
        # Поле API-ключа с прозрачным фоном
        self.api_key_input.setStyleSheet(theme["settings_input"])
        self.toggle_row_for_voice._apply_theme(theme)
        self.toggle_row_for_gesture._apply_theme(theme)
        self.use_onlie_model._apply_theme(theme)
        self.online_model_allows._apply_theme(theme)
        self.tts_recommendation_toggle._apply_theme(theme)
        for section in [self._section_input, self._section_ai, self._section_devices,
                        self._section_themes, self._section_api]:
            section._apply_theme(theme)
        for btn in self._theme_buttons:
            btn.setStyleSheet(theme["btn_theme"])
        # Применяем тему к кнопкам API-ключа (без границ и фона)
        self.show_api_key.setStyleSheet(THEMES[SELECTED_THEME]["btn_transparent"])
        self.save_key_btn.setStyleSheet(theme["btn_1"])
        self.auto_voice_toggle._apply_theme(theme)
   
    def get_current_camera(self):
        return self.camera_dropbox.currentText()

    def get_current_microphone(self):
        return self.microphone_dropbox.currentText()

    def is_voice_toggle_checked(self):
        """Возвращает состояние переключателя голосового ввода (True/False)"""
        return self.toggle_row_for_voice.isChecked()

    def is_gesture_toggle_checked(self):
        """Возвращает состояние переключателя жестового ввода (True/False)"""
        return self.toggle_row_for_gesture.isChecked()
    
    def is_online_model_allowed(self):
        """Возвращает состояние переключателя разрешающего доступ облачному ИИ к персональным данным (True/False)"""
        return self.online_model_allows.isChecked()

    def is_online_model_used(self):
        """Возвращает состояние переключателя использования облачного ИИ (True/False)"""
        return self.use_onlie_model.isChecked()

    def is_tts_recommendation_checked(self):
        """Возвращает состояние переключателя 'Озвучивать рекомендацию всегда' (True/False)"""
        return self.tts_recommendation_toggle.isChecked()

    def get_current_speaker(self):
        return self.speaker_dropbox.currentText()