from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap, QTextOption, QPen
import sys
import os
import math
from src.utils.database import DataBaseEditor
from src.utils.config import load_settings_config, set_settings_config_value, get_settings_config_value
from src.utils.logger import logger
from src.utils.devices import get_available_cameras, get_available_microphones
from .themes import THEMES, _COLOR_MAP
from .signals import ui_signals
# Базовый путь для иконок
from .widgets.chat_dialog import DialogBox
from .widgets.chat_send_box import ChatSendBox
from .widgets.glow_effects import RecommendationGlowEffect 
from .widgets.toggle_switch import ToggleSwitchRow, ToggleSwitchState
from .widgets.settings_section import SettingsSectionLabel

from .pages.gestures_page import GesturesPage
from .pages.voice_page import VoicePage
from .pages.text_page import TextPage
from .pages.settings_page import SettingsPage
from .pages.profile_page import ProfilePage
DATABASE_EDITOR = DataBaseEditor()

CONFIG = load_settings_config()
SELECTED_THEME = CONFIG.get("theme") or "light"
RECOGNITION_MODEL = CONFIG.get("recognition_model")

from src.GesturesInput.gestures import GestureCameraThread
from src.gui import icon_path


"""
====================================================
Правила(напоминание) наименования переменных и атрибутов
button - кнопка - btn
layout - лэйаут - lay
frame - рамка/фрейм - frame
Qt Style Sheets - стили qss - qss
"""
class UserInterface(QMainWindow):
    """Основной интерфейс приложения."""
    def __init__(self, api_key = ""):
        super().__init__()
        logger("UserInterface", "INFO", "Инициализация интерфейса")

        self._theme = THEMES[SELECTED_THEME]

        self.setWindowTitle("IAMOS")
        self.setGeometry(100, 100, 820, 690)
        self.setMinimumSize(700, 525)
        self.setStyleSheet(self._theme["main_window"])
        # Основное окно
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Основной лайаут: размещает боковую панель и панель контента горизонтально
        # Основной лайаут: обёртка с отступами
        self.main_lay = QHBoxLayout(self.main_widget)
        self.main_lay.setContentsMargins(10, 10, 10, 10)
        self.main_lay.setSpacing(0)

        # Сплиттер для изменения размера боковой панели и контента
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
            }
            QSplitter::handle:hover {
                background-color: transparent;
            }
            QSplitter::handle:pressed {
                background-color: transparent;
            }
        """)
        
        self.settings_page = SettingsPage(api_key)
        self.profile_page = ProfilePage()
        self.voice_input_page = VoicePage()
        self.text_input_page = TextPage()
        self.gestures_input_page = GesturesPage()
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
        self.side_panel.setStyleSheet(self._theme["side_panel"])
        

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

        # Растяжка – занимает всё свободное место между кнопками страниц и кнопкой очистки
        self.side_panel_lay.addStretch(1)

        # Кнопка очистки истории – будет в самом низу
        self.clear_history_btn = QPushButton("Очистить историю")
        self.clear_history_btn.setMinimumSize(55, 40)
        self.clear_history_btn.setCheckable(False)
        self.clear_history_btn.setIcon(QIcon(icon_path("delete.png")))
        self.clear_history_btn.setIconSize(QSize(25, 25))
        self.clear_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #9a0007;
            }
        """)
        self.clear_history_btn.clicked.connect(self._on_clear_history_clicked)
        self.clear_history_btn.setVisible(False)
        self.side_panel_lay.addWidget(self.clear_history_btn)

        self.main_splitter.addWidget(self.side_panel)
        self.main_splitter.addWidget(self.content_panel)
        self.main_splitter.setSizes([190, 630])          # начальные пропорции
        self.main_splitter.setStretchFactor(0, 0)        # боковая — не растягивается
        self.main_splitter.setStretchFactor(1, 1)        # контент — растягивается
        self.main_lay.addWidget(self.main_splitter)
        self.content_panel.setCurrentIndex(0)

        # Подключаемся на переключение страниц — останавливаем камеру при уходе с жестов
        self.content_panel.currentChanged.connect(self._on_page_changed)

        # Подписываемся на смену темы
        ui_signals.settings_changed.connect(self._on_settings_changed)

        # Подписываемся на рекомендации — подсвечиваем кнопки
        ui_signals.recommendation_ready.connect(self._on_recommendation_ready)

        # Сохраняем рекомендуемые методы и эффекты свечения
        self._recommended_methods = []
        self._glow_effects = {}
        self._method_to_button = {}
        
        # Инициализируем эффекты свечения после полной инициализации интерфейса
        QTimer.singleShot(100, self._init_glow_effects)
        
    def _on_clear_history_clicked(self):
        reply = QMessageBox.question(
            self, "Подтверждение", "Вы уверены, что хотите очистить всю историю сообщений?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ui_signals.clear_history_requested.emit()

    def _init_glow_effects(self):
        """Инициализирует эффекты свечения для кнопок после загрузки интерфейса."""
        self._method_to_button = {
            "voice": self.voice_input_page.side_panel_btn,
            "gesture": self.gestures_input_page.side_panel_btn,
            "text": self.text_input_page.side_panel_btn,
        }
        # Сохраняем оригинальные стили кнопок и передаём текущую тему
        for method, btn in self._method_to_button.items():
            self._glow_effects[method] = RecommendationGlowEffect(btn, SELECTED_THEME)
            # Подключаемся на клик кнопки — останавливаем анимацию
            btn.clicked.connect(lambda checked, m=method: self._on_button_clicked(m))

        # Загружаем сохранённые методы из конфига и скрываем ненужные кнопки
        self._load_and_apply_saved_methods()

    def _on_button_clicked(self, method: str):
        """
        Обработка клика на кнопку — останавливает анимацию.
        При переключении на другую страницу анимация возобновится.
        :param method: название метода (voice, gesture, text)
        """
        if method in self._glow_effects:
            self._glow_effects[method].stop()

    def _load_and_apply_saved_methods(self):
        """Загружает сохранённые методы из конфига и скрывает ненужные кнопки."""
        saved_methods = get_settings_config_value("recommended_methods")
        # Если методы не сохранены или пустые — показываем все кнопки
        if not saved_methods:
            logger("UserInterface", "INFO", "Нет сохранённых методов — показываем все кнопки")
            return

        self._recommended_methods = saved_methods
        logger("UserInterface", "INFO", f"Загружено {len(saved_methods)} сохранённых методов: {saved_methods}")

        # Скрываем кнопки, которых нет в сохранённых методах
        for method, btn in self._method_to_button.items():
            if method in saved_methods:
                btn.setVisible(True)
            else:
                btn.setVisible(False)

    def _on_settings_changed(self, changes: dict):
        """Реагируем на изменение настроек (в т.ч. темы)."""
        if "theme" in changes:
            self._apply_theme(changes["theme"])

    def _apply_theme(self, theme_name: str):
        """Применяет тему ко всему приложению."""
        global SELECTED_THEME
        self._theme_name = theme_name
        self._theme = THEMES[theme_name]
        SELECTED_THEME = theme_name  # Обновляем глобальную переменную
        set_settings_config_value("theme", theme_name)

        # Главное окно
        self.setStyleSheet(self._theme["main_window"])
        self.side_panel.setStyleSheet(self._theme["side_panel"])

        # Все страницы контента
        for page in self.content_pages:
            page._apply_theme(self._theme)

        # Переключатель настроек (цвета paintEvent)
        ts = self.settings_page.toggle_row_for_voice.toggle_switch
        ts._apply_theme(self._theme)
        ts2 = self.settings_page.toggle_row_for_gesture.toggle_switch
        ts2._apply_theme(self._theme)

        # Обновляем тему для эффектов свечения
        for method in self._method_to_button:
            if method in self._glow_effects:
                self._glow_effects[method].update_theme(theme_name)

    def change_theme(self, theme_name: str):
        """Публичный метод для смены темы извне."""
        self._apply_theme(theme_name)
        ui_signals.settings_changed.emit({"theme": theme_name})

    def _on_page_changed(self, index):
        """При переключении страницы: управление камерой и видимостью кнопки очистки."""
        page = self.content_panel.widget(index)

        # Показывать кнопку очистки только на страницах с чатом
        if isinstance(page, (VoicePage, TextPage, GesturesPage)):
            self.clear_history_btn.setVisible(True)
        else:
            self.clear_history_btn.setVisible(False)

        # Остановка камеры, если ушли со страницы жестов
        if page is not self.gestures_input_page:
            if self.gestures_input_page.camera_thread is not None:
                self.gestures_input_page.stop_camera()

        # Проверка: если текущая страница рекомендуется — запускаем/обновляем свечение
        self._update_button_glow_for_current_page(page)
        
        # Возобновляем анимацию для всех рекомендуемых кнопок (кроме той, на которую кликнули)
        self._resume_glow_for_recommended_pages()

    def _update_button_glow_for_current_page(self, page):
        """
        Проверяет, является ли текущая страница рекомендуемой, и обновляет свечение кнопки.
        Это позволяет подсветке работать без необходимости обновлять рекомендацию.
        """
        # Сопоставление страниц и методов
        page_to_method = {
            self.voice_input_page: "voice",
            self.gestures_input_page: "gesture",
            self.text_input_page: "text",
        }

        current_method = page_to_method.get(page)
        if not current_method:
            return

        # Если метод рекомендуется — включаем свечение
        if current_method in self._recommended_methods:
            if current_method in self._glow_effects:
                # Сбрасываем фазу анимации для красивого эффекта
                self._glow_effects[current_method].phase = 0
                self._glow_effects[current_method].start()

    def _resume_glow_for_recommended_pages(self):
        """
        Возобновляет анимацию для всех рекомендуемых кнопок.
        Вызывается при переключении страниц.
        """
        for method in self._recommended_methods:
            if method in self._glow_effects:
                # Перезапускаем анимацию
                self._glow_effects[method].phase = 0
                self._glow_effects[method].start()

    def closeEvent(self, event):
        """При закрытии окна — останавливаем камеру."""
        self.gestures_input_page.stop_camera()
        logger("IAMOS", "INFO", "Завершение работы")
        super().closeEvent(event)

    def _on_recommendation_ready(self, methods: list, text: str):
        """
        Обработка рекомендации: запускает анимацию бегущей линии по периметру кнопки.
        Если методы пустые — показываются все кнопки (рекомендации нет).
        :param methods: список рекомендуемых методов (voice, gesture, text, tts)
        :param text: текст рекомендации для отображения в профиле
        """
        # Сохраняем рекомендуемые методы в конфиг
        set_settings_config_value("recommended_methods", methods)
        # Сохраняем рекомендуемые методы локально
        self._recommended_methods = methods

        # Останавливаем все текущие анимации
        for method in self._glow_effects:
            self._glow_effects[method].stop()

        # Если методы пустые — показываем все кнопки (рекомендации нет)
        if not methods:
            for method, btn in self._method_to_button.items():
                btn.setVisible(True)
            return

        # Показываем/скрываем кнопки в зависимости от рекомендации
        for method, btn in self._method_to_button.items():
            if method in methods:
                btn.setVisible(True)
            else:
                btn.setVisible(False)
                # Если сейчас открыта скрытая страница — переключаемся на первую рекомендуемую
                page_to_method = {
                    self.voice_input_page: "voice",
                    self.gestures_input_page: "gesture",
                    self.text_input_page: "text",
                }
                current_page = self.content_panel.currentWidget()
                current_method = page_to_method.get(current_page)
                if current_method and current_method not in methods:
                    # Переключаемся на первый доступный рекомендуемый метод
                    for rec_method in methods:
                        if rec_method in self._method_to_button:
                            self._method_to_button[rec_method].click()
                            break

        # Запускаем анимацию для рекомендуемых методов
        for method in methods:
            if method in self._method_to_button:
                # Сбрасываем фазу анимации
                self._glow_effects[method].phase = 0
                self._glow_effects[method].start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = UserInterface()
    window.show()
    sys.exit(app.exec())