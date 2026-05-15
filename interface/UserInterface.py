from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QGridLayout, QComboBox, QButtonGroup, QTextEdit, QLineEdit,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QTextBrowser, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QPainter, QPainterPath, QBitmap, QTextOption, QPen
import sys
import os
import math
from BasicUtils import BasicUtils, DataBaseEditor
from data.themes import THEMES, _COLOR_MAP
from datetime import datetime

# Базовый путь для иконок
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
DATABASE_EDITOR = DataBaseEditor()

CONFIG = BasicUtils.load_settings_config()
SELECTED_THEME = CONFIG.get("theme") or "light"
RECOGNITION_MODEL = CONFIG.get("recognition_model")

from GesturesInput.gestures import GestureCameraThread

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
    profile_updated = pyqtSignal() # Сигнал для передачи текста из голосового ввода
    message_sent = pyqtSignal(str, str)
    voice_input_changed = pyqtSignal(bool)
    voice_message_received = pyqtSignal(str)
    speaker_pressed = pyqtSignal(str)
    speaker_stop_all = pyqtSignal()        # сброс всех кнопок для воспроизведения
    speaker_stop_request = pyqtSignal()    # остановка воспроизведения
    speaker_finished = pyqtSignal()        # конец воспроизведения без вмешательства
    history_cleared = pyqtSignal()          # для обновления чатов после очистки
    clear_history_requested = pyqtSignal()  # запрос на очистку истории (отправляется в ядро)
    recommendation_ready = pyqtSignal(list, str)  # (список методов, текст для пользователя)
    openrouter_api_key_changed = pyqtSignal(str)  # Сигнал для изменения API ключа OpenRouter
    dysfunctions_saved = pyqtSignal()  # Сигнал о сохранении нарушений
    typing_started  = pyqtSignal()    # нейросеть начала думать
    typing_finished = pyqtSignal()    # нейросеть ответила
ui_signals = Signals()


# ==========================================================
# ИНДИКАТОР ПЕЧАТАНИЯ / ДУМАНИЯ НЕЙРОСЕТИ
# ==========================================================

class TypingDotsWidget(QWidget):
    """
    Анимированные три точки, имитирующие эффект печатания/думания.
    Точки поочерёдно пульсируют по яркости и подпрыгивают вверх-вниз (~60 FPS).
    """
    def __init__(self, dot_color: str = "#4CAF50", parent=None):
        super().__init__(parent)
        self._dot_color = QColor(dot_color)
        self._dot_count = 3
        self._phase = 0.0
        self._dot_radius = 5
        self._dot_spacing = 20
        self._min_alpha = 120
        self._max_alpha = 255
        self._jump_amplitude = 2  # амплитуда подпрыгивания в пикселях

        total_w = self._dot_count * self._dot_spacing
        total_h = self._dot_radius * 2 + 6 + self._jump_amplitude * 2
        self.setFixedSize(total_w, total_h)

        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._phase = 0.0
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.update()

    def set_color(self, hex_color: str):
        self._dot_color = QColor(hex_color)
        self.update()

    def apply_theme(self, theme: dict):
        """
        Применяет тему интерфейса — устанавливает цвет точек из темы.
        :param theme: словарь темы с ключом 'typing_dots'
        """
        dots_config = theme.get("typing_dots", {})
        dot_color = dots_config.get("color", "#4CAF50")
        self.set_color(dot_color)

    def _tick(self):
        self._phase = (self._phase + 0.06) % self._dot_count
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self._dot_radius
        base_cy = self.height() // 2
        for i in range(self._dot_count):
            dist = abs((self._phase - i + self._dot_count) % self._dot_count)
            dist = min(dist, self._dot_count - dist)
            brightness = math.cos(dist * math.pi / (self._dot_count - 0.5))
            brightness = max(0.0, brightness)
            alpha = int(self._min_alpha + (self._max_alpha - self._min_alpha) * brightness)
            color = QColor(self._dot_color.red(), self._dot_color.green(),
                           self._dot_color.blue(), alpha)
            
            # Вычисляем смещение по Y для эффекта подпрыгивания
            jump_offset = math.sin((self._phase - i) * math.pi) * self._jump_amplitude * brightness
            cy = base_cy + jump_offset
            
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(cx - self._dot_radius, cy - self._dot_radius,
                       self._dot_radius * 2, self._dot_radius * 2)
            )
            cx += self._dot_spacing
        painter.end()


class TypingIndicator(QWidget):
    """
    Пузырь «думания» нейросети с анимированными точками.
    Стилизован аналогично Message — органично встраивается в DialogBox.
    """
    def __init__(self, author_name: str = "IAMOS", frame_style: str = "",
                 label_style: str = "", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        outer_lay = QHBoxLayout(self)
        outer_lay.setContentsMargins(10, 5, 10, 5)
        outer_lay.setSpacing(5)

        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(frame_style)
        self.main_frame.setMinimumWidth(100)
        self.main_frame.setMaximumWidth(300)
        self.main_frame.setSizePolicy(QSizePolicy.Policy.MinimumExpanding,
                                      QSizePolicy.Policy.MinimumExpanding)

        frame_lay = QVBoxLayout(self.main_frame)
        frame_lay.setContentsMargins(12, 10, 12, 10)
        frame_lay.setSpacing(6)

        self.author_label = QLabel(author_name)
        self.author_label.setStyleSheet(label_style)
        frame_lay.addWidget(self.author_label)

        self.dots = TypingDotsWidget()
        frame_lay.addWidget(self.dots, alignment=Qt.AlignmentFlag.AlignLeft)

        outer_lay.addWidget(self.main_frame)
        outer_lay.addStretch()

    def start(self):
        self.dots.start()

    def stop(self):
        self.dots.stop()

    def _apply_theme(self, theme: dict):
        self.main_frame.setStyleSheet(theme.get("message_frame", ""))
        self.author_label.setStyleSheet(theme.get("message_author", ""))
        self.dots.apply_theme(theme)


#==========================================================
#Бегущая подсветка
#==========================================================
class RunningLineOverlay(QWidget):
    """
    Overlay-виджет для отрисовки бегущей линии по периметру кнопки.
    Цвет линии адаптируется к текущей теме интерфейса.
    """
    def __init__(self, parent, button, theme_name: str = "dark"):
        super().__init__(parent)
        self.button = button
        self.phase = 0
        self.theme_name = theme_name
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # Получаем параметры свечения из темы
        colors = _COLOR_MAP.get(theme_name, _COLOR_MAP["dark"])
        
        # Цвет и радиус свечения из темы
        glow_color_hex = colors.get("glow", "#00FF00")
        glow_blur = colors.get("glow_blur", 30)
        
        self.line_color = QColor(glow_color_hex)

        # Тень для линии — яркий эффект с параметрами из темы
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(glow_blur)
        self.glow_effect.setColor(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), 200))
        self.glow_effect.setXOffset(0)
        self.glow_effect.setYOffset(0)
        self.setGraphicsEffect(self.glow_effect)

    def paintEvent(self, event):
        """Рисует бегущую линию по периметру с скруглёнными углами."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Размеры кнопки
        w = self.width()
        h = self.height()
        margin = 2  # отступ для границы
        corner_radius = 12  # радиус скругления как у кнопки

        # Рисуем полный контур кнопки (скруглённый прямоугольник)
        path = QPainterPath()
        path.addRoundedRect(margin, margin, w - 2*margin, h - 2*margin, corner_radius, corner_radius)

        # Получаем длину контура
        perimeter = path.length()

        # Позиция бегущей линии
        line_length = perimeter * 0.35  # длина линии 35% от периметра
        start_pos = (self.phase % 4) * perimeter / 4

        # Рисуем линию вдоль контура с градиентом прозрачности
        num_segments = int(line_length)
        for i in range(num_segments):
            pos = (start_pos + i) % perimeter
            prev_pos = (start_pos + i - 1) % perimeter if i > 0 else pos

            # Градиент прозрачности: яркий центр, тусклые края
            dist_from_start = i / line_length
            # Используем синусоиду для плавного градиента
            alpha = int(255 * math.sin(dist_from_start * math.pi))

            point = path.pointAtPercent(pos / perimeter)
            prev_point = path.pointAtPercent(prev_pos / perimeter)

            # Рисуем сегмент линии с цветом из темы
            pen = QPen(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), alpha), 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)

            if i > 0:
                painter.drawLine(prev_point, point)

        painter.end()
        
class RecommendationGlowEffect:
    """
    Класс для управления анимированной 'бегущей' подсветкой по периметру кнопки.
    Создает overlay-виджет с бегущей линией и тенью поверх кнопки.
    """

    def __init__(self, button: QPushButton, theme_name: str = "dark"):
        self.button = button
        self.theme_name = theme_name
        self.overlay = None
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_position)
        self.phase = 0
        self.is_active = False

    def start(self):
        """Запускает анимацию бегущей линии."""
        if self.is_active:
            return
        self.is_active = True

        # Создаем overlay-виджет если ещё не создан
        if not self.overlay:
            self._create_overlay()

        self.overlay.show()
        self.animation_timer.start(16)  # ~60 FPS для плавности

    def stop(self):
        """Останавливает анимацию и скрывает overlay."""
        self.is_active = False
        self.animation_timer.stop()
        if self.overlay:
            self.overlay.hide()

    def update_theme(self, theme_name: str):
        """Обновляет тему и пересоздает overlay с новым цветом."""
        self.theme_name = theme_name
        if self.overlay:
            # Скрываем старый overlay
            self.overlay.hide()
            # Пересоздаем overlay с новой темой
            self._create_overlay()
            # Если анимация была активна, показываем новый overlay
            if self.is_active:
                self.overlay.show()

    def _create_overlay(self):
        """Создает overlay-виджет для отрисовки бегущей линии."""
        self.overlay = RunningLineOverlay(self.button.parent(), self.button, self.theme_name)
        self.overlay.setGeometry(self.button.geometry())
        self.overlay.raise_()

    def _update_position(self):
        """Обновляет позицию бегущей линии."""
        if not self.is_active or not self.overlay:
            return

        self.phase += 0.03  # Медленнее для плавности

        # Синхронизируем overlay с позицией и размером кнопки
        self.overlay.setGeometry(self.button.geometry())
        self.overlay.raise_()

        # Обновляем фазу для отрисовки
        self.overlay.phase = self.phase
        self.overlay.update()  # Вызываем перерисовку


# ===========================================================
# ГЛАВНЫЙ ИНТЕРФЕЙС
# ===========================================================
class UserInterface(QMainWindow):
    """Основной интерфейс приложения."""
    def __init__(self, api_key = ""):
        super().__init__()
        BasicUtils.logger("UserInterface", "INFO", "Инициализация интерфейса")

        self._theme = THEMES[SELECTED_THEME]

        self.setWindowTitle("IAMOS")
        self.setGeometry(100, 100, 820, 690)
        self.setMinimumSize(700, 525)
        self.setStyleSheet(self._theme["main_window"])
        # Основное окно
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        # Основной лайаут: размещает боковую панель и панель контента горизонтально
        self.main_lay = QHBoxLayout(self.main_widget)
        self.main_lay.setContentsMargins(10, 10, 10, 10)
        self.main_lay.setSpacing(10)


        self.settings_page = Settings(api_key)
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
        self.clear_history_btn.setFixedSize(160, 40)
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

        self.main_lay.addWidget(self.side_panel, 2)
        self.main_lay.addWidget(self.content_panel, 7)
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
        saved_methods = BasicUtils.get_settings_config_value("recommended_methods")
        # Если методы не сохранены или пустые — показываем все кнопки
        if not saved_methods:
            BasicUtils.logger("UserInterface", "INFO", "Нет сохранённых методов — показываем все кнопки")
            return

        self._recommended_methods = saved_methods
        BasicUtils.logger("UserInterface", "INFO", f"Загружено {len(saved_methods)} сохранённых методов: {saved_methods}")

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
        BasicUtils.set_settings_config_value("theme", theme_name)

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
        if isinstance(page, (VoiceInput, TextInput, GesturesInput)):
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
        BasicUtils.logger("IAMOS", "INFO", "Завершение работы")
        super().closeEvent(event)

    def _on_recommendation_ready(self, methods: list, text: str):
        """
        Обработка рекомендации: запускает анимацию бегущей линии по периметру кнопки.
        Если методы пустые — показываются все кнопки (рекомендации нет).
        :param methods: список рекомендуемых методов (voice, gesture, text, tts)
        :param text: текст рекомендации для отображения в профиле
        """
        # Сохраняем рекомендуемые методы в конфиг
        BasicUtils.set_settings_config_value("recommended_methods", methods)
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


# ==========================================================
# Виджет отправки сообщений (текстовое поле)
# ==========================================================
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
            main_layout.addStretch()                                   # прижимаем влево
    
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
#==========================================================
#Основание для панелей контента
#==========================================================
class ContentPageWidget(QWidget):
    """Основание для панелей контента"""
    def __init__(self):
        super().__init__()

        self.side_panel_btn = QPushButton()
        self.side_panel_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_2"])
        self.settings_text_qss = THEMES[SELECTED_THEME]["settings_text"]
        self.dropbox_qss = THEMES[SELECTED_THEME]["settings_combobox"]
        self.side_panel_btn.setMinimumSize(160, 60)

        # состояние кнопки при нажатии
        self.side_panel_btn.setCheckable(True)

        # единый размер иконок
        self._icon_size = QSize(25, 25)

        self.side_panel_btn.setIconSize(self._icon_size)

        # Тень при наведении — создаём без родителя, чтобы не удалялся
        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setBlurRadius(20)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(4)
        self._shadow.setColor(QColor(0, 0, 0, 120))

        self.side_panel_btn.setGraphicsEffect(self._shadow)
        self._shadow.setEnabled(False)

        # Обработка наведения — с проверкой существования эффекта
        def on_enter(e):
            if hasattr(self, '_shadow') and self._shadow:
                self._shadow.setEnabled(True)
        def on_leave(e):
            if hasattr(self, '_shadow') and self._shadow:
                self._shadow.setEnabled(False)
        
        self.side_panel_btn.enterEvent = on_enter
        self.side_panel_btn.leaveEvent = on_leave

    def _apply_theme(self, theme: dict):
        """Обновляет стили кнопки боковой панели."""
        self.side_panel_btn.setStyleSheet(theme["btn_2"])
        self.settings_text_qss = theme["settings_text"]
        self.dropbox_qss = theme["settings_combobox"]

     
        
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
        
        # Цвета из темы
        _t = THEMES[SELECTED_THEME]["toggle_switch"]
        self._bg_color_off = QColor(_t["bg_off"])
        self._bg_color_on = QColor(_t["bg_on"])
        self._circle_color = QColor(_t["circle"])
        
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

    def _apply_theme(self, theme: dict):
        """Обновляет цвета переключателя."""
        ts = theme["toggle_switch"]
        self._bg_color_off = QColor(ts["bg_off"])
        self._bg_color_on = QColor(ts["bg_on"])
        self._circle_color = QColor(ts["circle"])
        self.update()


class ToggleSwitchRow(QWidget):
    """Фрейм с меткой и переключателем для настроек"""

    toggled = pyqtSignal(bool)

    def __init__(self, text, parent=None, checked=False):
        super().__init__(parent)

        # Основной лайаут
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # фрейм для переключателя
        self.toggle_frame = QFrame()
        self.toggle_frame.setStyleSheet(THEMES[SELECTED_THEME]["toggle_switch_row"])
        self.toggle_frame.setFixedHeight(40)
        main_layout.addWidget(self.toggle_frame)

        # лайаут фрейма переключателя
        self.toggle_frame_lay = QHBoxLayout(self.toggle_frame)
        self.toggle_frame_lay.setContentsMargins(10, 5, 15, 10)
        self.toggle_frame_lay.setSpacing(10)

        # Текстовая метка
        self.label = QLabel(text)
        self.label.setStyleSheet(THEMES[SELECTED_THEME]["toggle_switch_row_label"])
        self.toggle_frame_lay.addWidget(self.label, 1)

        # Переключатель
        self.toggle_switch = ToggleSwitch()
        self.toggle_frame_lay.addWidget(self.toggle_switch)

        # Подключаем сигнал
        self.toggle_switch.toggled.connect(self.toggled.emit)

    def isChecked(self):
        return self.toggle_switch.isChecked()

    def setChecked(self, state):
        self.toggle_switch.setChecked(state)

    def _apply_theme(self, theme: dict):
        """Обновляет стили фрейма и метки."""
        self.toggle_frame.setStyleSheet(theme["toggle_switch_row"])
        self.label.setStyleSheet(theme["toggle_switch_row_label"])
        self.toggle_switch._apply_theme(theme)


class ToggleSwitchState:
    """Класс для сохранения и загрузки состояния переключателя"""
    
    def __init__(self, config_key):
        self.config_key = config_key
    
    def save(self, state):
        """Сохраняет состояние переключателя в конфиг"""
        BasicUtils.set_settings_config_value(self.config_key, state)
        ui_signals.settings_changed.emit({self.config_key: state})
    
    def load(self):
        """Загружает состояние переключателя из конфига"""
        settings_config = BasicUtils.load_settings_config()
        return settings_config.get(self.config_key, False)


# ===========================================================
# РАЗДЕЛИТЕЛЬ СЕКЦИЙ НАСТРОЕК
# ===========================================================
class SettingsSectionLabel(QWidget):
    """Минималистичный заголовок-разделитель для группировки настроек.
    Рисует тонкую цветную полосу слева и текст метки."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        # Тонкий вертикальный акцент-прямоугольник
        self._accent = QFrame()
        self._accent.setFixedSize(3, 16)
        self._accent.setStyleSheet(THEMES[SELECTED_THEME]["accent"])
        lay.addWidget(self._accent, 0, Qt.AlignmentFlag.AlignVCenter)

        # Текстовая метка
        self._label = QLabel(text)
        self._label.setStyleSheet(THEMES[SELECTED_THEME]["settings_section_label"])
        lay.addWidget(self._label, 1)

        # Горизонтальная разделительная линия
        self._line = QFrame()
        self._line.setFrameShape(QFrame.Shape.HLine)
        self._line.setFixedHeight(1)
        self._line.setStyleSheet(THEMES[SELECTED_THEME]["border"])
        lay.addWidget(self._line, 6)

    def _apply_theme(self, theme: dict):
        self._accent.setStyleSheet(theme["accent"])
        self._label.setStyleSheet(theme["settings_section_label"])
        self._line.setStyleSheet(theme["border"])


# ===========================================================
# НАСТРОЙКИ
# ===========================================================
class Settings(ContentPageWidget):
    def __init__(self, api_key = ""):
        
        super().__init__()

        self.available_voices = BasicUtils.get_settings_config_value("available_silero_voices")
        self.available_voices_reversed = BasicUtils.get_settings_config_value("available_silero_voices_reversed")
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

        available = BasicUtils.get_available_cameras()
        
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

        available_mics = BasicUtils.get_available_microphones()

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
        settings_config = BasicUtils.load_settings_config()

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
        BasicUtils.set_settings_config_value("camera_index", index)
        ui_signals.settings_changed.emit({"camera": text})

    def _on_microphone_changed(self, text):
        """Сохраняет выбранный микрофон."""
        index = self.microphone_dropbox.currentIndex()
        BasicUtils.set_settings_config_value("microphone_index", index)
        ui_signals.settings_changed.emit({"microphone": text})

    def _on_speaker_changed(self, text):
        """Сохраняет выбранного диктора."""
        BasicUtils.set_settings_config_value("tts_voice", self.available_voices[text])
        ui_signals.settings_changed.emit({"tts_voice": self.available_voices[text]})

    def _on_theme_changed(self, theme_name: str):
        """Сохраняет выбранную тему."""
        BasicUtils.set_settings_config_value("theme", theme_name)
        ui_signals.settings_changed.emit({"theme": theme_name})

    def _apply_theme(self, theme: dict):
        """Обновляет все стили страницы настроек."""
        super()._apply_theme(theme)
        # Получаем имя текущей темы для доступа к цветам
        theme_name = BasicUtils.get_settings_config_value("theme") or "light"
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

        self.setStyleSheet(THEMES[SELECTED_THEME]["profile_option_frame"])
        self.text_qss = THEMES[SELECTED_THEME]["profile_text"]
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
        self.line.setStyleSheet(THEMES[SELECTED_THEME]["profile_line"])
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
            updates = {self.columns[0]: new_value}
        DATABASE_EDITOR.update_data(self.table_name, updates, self.id)
        ui_signals.profile_updated.emit()

    def get_value(self) -> str:
        """Возвращает текущее значение."""
        return self._current_value

    def _apply_theme(self, theme: dict):
        """Обновляет стили строки профиля."""
        self.setStyleSheet(theme["profile_option_frame"])
        self.text_qss = theme["profile_text"]
        self.name_label.setStyleSheet(theme["profile_text"])
        self.value_label.setStyleSheet(theme["profile_text"])
        self.value_edit.setStyleSheet(theme["profile_text"] + "background: transparent; border: none;")
        self.line.setStyleSheet(theme["profile_line"])


class RecommendationBadge(QFrame):
    """
    Виджет плашки рекомендаций с вертикальным расположением:
    - Заголовок сверху
    - Разделительная линия
    - Текст рекомендации снизу
    """
    def __init__(self, title: str = "Рекомендация по вводу/выводу", 
                 recommendation_text: str = "Не определено", parent=None):
        super().__init__(parent)
        
        self.setStyleSheet(THEMES[SELECTED_THEME]["profile_option_frame"])
        self.text_qss = THEMES[SELECTED_THEME]["profile_text"]
        
        # Убираем фиксированную высоту, позволяем растягиваться
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        
        # Вертикальный лэйаут
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(10, 8, 10, 8)
        self.lay.setSpacing(8)
        
        # Заголовок сверху
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(self.text_qss + "font-weight: bold;")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.lay.addWidget(self.title_label)
        
        # Горизонтальная разделительная линия
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.line.setStyleSheet(THEMES[SELECTED_THEME]["profile_line"])
        self.lay.addWidget(self.line)
        
        # Текст рекомендации снизу
        self.recommendation_label = QLabel(recommendation_text)
        self.recommendation_label.setStyleSheet(self.text_qss)
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.lay.addWidget(self.recommendation_label)
        
        # Сохраняем текущее значение для совместимости
        self._current_value = recommendation_text
    
    def set_recommendation(self, text: str):
        """Обновляет текст рекомендации."""
        self.recommendation_label.setText(text)
        self._current_value = text
    
    def get_value(self) -> str:
        """Возвращает текущее значение рекомендации."""
        return self._current_value
    
    def _apply_theme(self, theme: dict):
        """Обновляет стили плашки."""
        self.setStyleSheet(theme["profile_option_frame"])
        self.text_qss = theme["profile_text"]
        self.title_label.setStyleSheet(theme["profile_text"] + "font-weight: bold;")
        self.recommendation_label.setStyleSheet(theme["profile_text"])
        self.line.setStyleSheet(theme["profile_line"])

class DysfunctionsProfileOption(QFrame):
    value_changed = pyqtSignal(str)
    dysfunctions_saved = pyqtSignal()  # Сигнал о сохранении нарушений

    # Общий стиль кнопок-иконок (карандаш, галочка, шеврон)
    _BTN_STYLE = """
        QPushButton { background-color: transparent; border-radius: 15px; }
        QPushButton:hover { background-color: transparent; }
        QPushButton:pressed { background-color: transparent; }
    """

    def __init__(
        self,
        value: str,
        table_name: str = "Users",
        column: str = "dysfunctions",
        row_id: int = 0,
        parent=None
    ):
        super().__init__(parent)

        self.table_name = table_name
        self.column = column
        self.row_id = row_id
        self._current_value = value or ""
        self._full_text = self._current_value
        self._is_expanded = False
        self._is_editing = False

        # Минимальная высота текстового поля в свёрнутом состоянии
        self._collapsed_height = 30

        self.setStyleSheet(THEMES[SELECTED_THEME]["profile_option_frame"])
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(10, 8, 10, 8)
        self.main_lay.setSpacing(6)

        # ── ЗАГОЛОВОК ──────────────────────────────────────────────
        self.header_lay = QHBoxLayout()
        self.header_lay.setContentsMargins(0, 0, 0, 0)
        self.header_lay.setSpacing(6)

        self.name_label = QLabel("Нарушения")
        self.name_label.setStyleSheet(THEMES[SELECTED_THEME]["profile_text"])
        self.header_lay.addWidget(self.name_label)
        self.header_lay.addStretch(1)

        # Шеврон (свернуть / развернуть)
        self.btn_chevron = QPushButton()
        self.btn_chevron.setIcon(QIcon(icon_path("chevron-down.png")))
        self.btn_chevron.setIconSize(QSize(18, 18))
        self.btn_chevron.setFixedSize(25, 25)
        self.btn_chevron.setStyleSheet(self._BTN_STYLE)
        self.btn_chevron.clicked.connect(self._toggle_expand)

        # Карандаш
        self.btn_edit = QPushButton()
        self.btn_edit.setIcon(QIcon(icon_path("pencil.png")))
        self.btn_edit.setIconSize(QSize(20, 20))
        self.btn_edit.setFixedSize(25, 25)
        self.btn_edit.setStyleSheet(self._BTN_STYLE)
        self.btn_edit.clicked.connect(self._start_editing)

        # Галочка (сохранить)
        self.btn_save = QPushButton()
        self.btn_save.setIcon(QIcon(icon_path("accept.png")))
        self.btn_save.setIconSize(QSize(20, 20))
        self.btn_save.setFixedSize(25, 25)
        self.btn_save.setVisible(False)
        self.btn_save.setStyleSheet(self._BTN_STYLE)
        self.btn_save.clicked.connect(self._finish_editing)

        # Отмена (крестик) — появляется только при редактировании
        self.btn_cancel = QPushButton()
        cancel_icon = QIcon(icon_path("cancel.png")) if os.path.exists(icon_path("cancel.png")) else QIcon()
        self.btn_cancel.setIcon(cancel_icon)
        self.btn_cancel.setText("✕")
        self.btn_cancel.setIconSize(QSize(16, 16))
        self.btn_cancel.setFixedSize(25, 25)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setStyleSheet(self._BTN_STYLE + "QPushButton { font-size: 12px; color: #e57373; }")
        self.btn_cancel.clicked.connect(self._cancel_editing)

        self.header_lay.addWidget(self.btn_chevron)
        self.header_lay.addWidget(self.btn_edit)
        self.header_lay.addWidget(self.btn_save)
        self.header_lay.addWidget(self.btn_cancel)
        self.main_lay.addLayout(self.header_lay)

        # ── РАЗДЕЛИТЕЛЬ ────────────────────────────────────────────
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.line.setStyleSheet(THEMES[SELECTED_THEME]["profile_line"])
        self.main_lay.addWidget(self.line)

        # ── ТЕКСТОВОЕ ПОЛЕ ─────────────────────────────────────────
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self._get_display_text())
        self.text_edit.setReadOnly(True)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet(self._text_edit_style(THEMES[SELECTED_THEME]))
        self.main_lay.addWidget(self.text_edit)

        # Обновлять высоту при любом изменении контента
        self.text_edit.document().contentsChanged.connect(self._schedule_height_update)

        # Первичная установка высоты после рендера
        QTimer.singleShot(0, self._update_text_height)

    # ── СТИЛЬ ──────────────────────────────────────────────────────
    def _text_edit_style(self, theme: dict) -> str:
        base = """
            QTextEdit {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 4px 6px;
                font-size: 14px;
                font-family: "Roboto";
            }
            QTextEdit:focus { border: none; outline: none; }
        """
        color_rule = f"QTextEdit {{ {theme['profile_text']} }}"
        return base + color_rule + theme.get("scrollbar", "")

    # ── ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ─────────────────────────────────────
    def _get_display_text(self) -> str:
        """Текст для отображения с учётом текущего состояния."""
        if self._is_expanded or self._is_editing:
            return self._full_text if self._full_text else "Не указано"
        return self._get_truncated_text()

    def _get_truncated_text(self) -> str:
        """Первая строка текста, обрезанная по ширине виджета через QFontMetrics."""
        if not self._full_text or not self._full_text.strip():
            return "Не указано"

        text = self._full_text.strip()
        first_line = text.split('\n')[0]
        has_more = '\n' in text or len(text) > len(first_line)

        # Обрезка через QFontMetrics с учётом реальной ширины
        fm = self.text_edit.fontMetrics()
        available_width = max(self.text_edit.viewport().width() - 20, 100)
        elided = fm.elidedText(first_line, Qt.TextElideMode.ElideRight, available_width)

        # Добавляем «…» если есть ещё строки, а elidedText не добавил
        if has_more and not elided.endswith("…") and not elided.endswith("..."):
            elided = fm.elidedText(first_line + "…", Qt.TextElideMode.ElideRight, available_width)

        return elided

    def _compute_document_height(self) -> int:
        """Вычисляет высоту, необходимую для отображения текущего документа."""
        doc = self.text_edit.document()
        viewport_width = self.text_edit.viewport().width()
        if viewport_width > 0:
            doc.setTextWidth(viewport_width)
        # +12 — небольшой запас на padding
        return int(doc.size().height()) + 12

    # ── РАЗВЕРНУТЬ / СВЕРНУТЬ ──────────────────────────────────────
    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded

        if self._is_expanded:
            self.btn_chevron.setIcon(QIcon(icon_path("chevron-up.png")))
            self.text_edit.setPlainText(self._full_text if self._full_text else "Не указано")
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.btn_chevron.setIcon(QIcon(icon_path("chevron-down.png")))
            self.text_edit.setPlainText(self._get_truncated_text())
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._update_text_height()

    # ── РЕДАКТИРОВАНИЕ ─────────────────────────────────────────────
    def _start_editing(self):
        self._is_editing = True
        self._edit_backup = self._full_text  # сохраняем для отмены

        # Разворачиваем, если свёрнуто
        if not self._is_expanded:
            self._is_expanded = True
            self.btn_chevron.setIcon(QIcon(icon_path("chevron-up.png")))

        self.text_edit.setPlainText(self._full_text if self._full_text else "")
        self.text_edit.setReadOnly(False)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.setFocus()

        # Курсор в конец
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)

        self.btn_edit.setVisible(False)
        self.btn_save.setVisible(True)
        self.btn_cancel.setVisible(True)

        self._update_text_height()

    def _finish_editing(self):
        new_value = self.text_edit.toPlainText().strip()
        self._is_editing = False

        self._full_text = new_value
        self._current_value = new_value if new_value else "Не указано"

        self.text_edit.setReadOnly(True)
        self.btn_edit.setVisible(True)
        self.btn_save.setVisible(False)
        self.btn_cancel.setVisible(False)

        # Показываем правильный текст
        if self._is_expanded:
            self.text_edit.setPlainText(self._full_text if self._full_text else "Не указано")
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_edit.setPlainText(self._get_truncated_text())

        DATABASE_EDITOR.update_data(self.table_name, {self.column: new_value}, self.row_id)
        ui_signals.profile_updated.emit()
        self.value_changed.emit(new_value)
        self.dysfunctions_saved.emit()  # Сигнал о сохранении нарушений
        self._update_text_height()

    def _cancel_editing(self):
        """Отменяет редактирование, восстанавливая предыдущий текст."""
        self._is_editing = False
        self._full_text = self._edit_backup

        self.text_edit.setReadOnly(True)
        self.btn_edit.setVisible(True)
        self.btn_save.setVisible(False)
        self.btn_cancel.setVisible(False)

        if self._is_expanded:
            self.text_edit.setPlainText(self._full_text if self._full_text else "Не указано")
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.text_edit.setPlainText(self._get_truncated_text())

        self._update_text_height()

    # ── УПРАВЛЕНИЕ ВЫСОТОЙ ─────────────────────────────────────────
    def _schedule_height_update(self):
        QTimer.singleShot(0, self._update_text_height)

    def _update_text_height(self):
        if not self.text_edit:
            return

        if self._is_expanded or self._is_editing:
            # Высота по содержимому документа (не по родителю!)
            doc_h = self._compute_document_height()
            target = max(self._collapsed_height, doc_h)
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            # Свёрнуто — одна строка
            fm = self.text_edit.fontMetrics()
            target = fm.height() + 16  # высота одной строки + padding
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.text_edit.setMinimumHeight(target)
        self.text_edit.setMaximumHeight(target)

        self.updateGeometry()
        if self.parentWidget():
            self.parentWidget().updateGeometry()

    def resizeEvent(self, event):
        
        super().resizeEvent(event)
        # При изменении ширины текст может переноситься иначе — пересчитываем
        self._schedule_height_update()

    # ── ПУБЛИЧНЫЕ МЕТОДЫ ───────────────────────────────────────────
    def get_value(self) -> str:
        return self._current_value

    def set_value(self, value: str):
        """Программно обновляет значение без записи в БД."""
        self._full_text = value or ""
        self._current_value = self._full_text if self._full_text else "Не указано"
        self.text_edit.setPlainText(self._get_display_text())
        self._update_text_height()

    def _apply_theme(self, theme: dict):
        self.setStyleSheet(theme["profile_option_frame"])
        self.name_label.setStyleSheet(theme["profile_text"])
        self.line.setStyleSheet(theme["profile_line"])
        self.text_edit.setStyleSheet(self._text_edit_style(theme))

class Profile(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Профиль")
        self.side_panel_btn.setIcon(QIcon(icon_path("profile.png")))
        
        
        self.profile_lay = QVBoxLayout(self)
        self.profile_lay.setContentsMargins(0, 0, 0, 0)
        # Главная рамка
        self.main_frame = QFrame()
        self.main_frame.setStyleSheet(THEMES[SELECTED_THEME]["dialog_frame"])
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
        self.photo_frame.setStyleSheet(THEMES[SELECTED_THEME]["profile_photo_frame"])
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
        def _safe_get(table, column):
            result = DATABASE_EDITOR.get_data(table, column, 0)
            return result[0][0] if result and result[0] and result[0][0] else None

        self._surname = _safe_get("Users", "surname")
        self._firstname = _safe_get("Users", "firstname")
        self._patronymic = _safe_get("Users", "patronymic")
        self._sn_fn_patr = f"{self._surname} {self._firstname} {self._patronymic}" if any([self._surname, self._firstname, self._patronymic]) else None
        self._birthday = _safe_get("Users", "birthday")
        self._gender = _safe_get("Users", "gender")

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

        self._dysfunctions = _safe_get("Users", "dysfunctions")

        self.dysfunctions = DysfunctionsProfileOption(
            value=self._dysfunctions if self._dysfunctions else "Не указано",
            table_name="Users",
            column="dysfunctions",
            row_id=0
        )

        self.main_frame_lay.addWidget(self.dysfunctions)

        self._adaptive = _safe_get("Users", "adaptation_status")
        self.adaptive = ProfileOption("Степень адаптации системы", f"{self._adaptive if self._adaptive else 'Отсутствует'}", False)
        self.main_frame_lay.addWidget(self.adaptive, Qt.AlignmentFlag.AlignLeft)
        
        self._fatigue = None
        
        self.fatigue = ProfileOption("Усталость", f"{self._fatigue if self._fatigue else 'Отсутствует'}", False)
        self.main_frame_lay.addWidget(self.fatigue, Qt.AlignmentFlag.AlignLeft)


        self.main_frame_lay.addStretch(1)

        # Создаём рекомендацию с новым виджетом RecommendationBadge
        self.recommendation = RecommendationBadge("Рекомендация по вводу/выводу", "Не определено")
        self.main_frame_lay.addWidget(self.recommendation, Qt.AlignmentFlag.AlignLeft)

        # Подключаем сигнал обновления (принимает только текст, игнорируя методы)
        ui_signals.recommendation_ready.connect(self._on_recommendation_ready)
        
        # Подключаем сигнал сохранения нарушений к глобальному сигналу
        self.dysfunctions.dysfunctions_saved.connect(lambda: ui_signals.dysfunctions_saved.emit())

        # Автоматический запрос рекомендации при запуске (через 300 мс)
        QTimer.singleShot(300, lambda: ui_signals.profile_updated.emit())

    def _on_recommendation_ready(self, methods: list, text: str):
        """Обновляет текст рекомендации (методы игнорируются, они обрабатываются в UserInterface)."""
        self.recommendation.set_recommendation(text)

    def _apply_theme(self, theme: dict):
        """Обновляет стили страницы профиля."""
        super()._apply_theme(theme)
        self.main_frame.setStyleSheet(theme["dialog_frame"])
        self.photo_frame.setStyleSheet(theme["profile_photo_frame"])
        self.recommendation._apply_theme(theme)
        for opt in [self.sn_fn_patr, self.birthday, self.gender, self.dysfunctions, self.adaptive, self.fatigue]:
            opt._apply_theme(theme)


# ===========================================================
# ГОЛОСОВОЙ ВВОД
# ===========================================================
class VoiceInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(THEMES[SELECTED_THEME]["input_page"])
        self.side_panel_btn.setText("Голосовой Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("microphone.png")))
        self.text_input_lay = QVBoxLayout(self)
        self.text_input_lay.setContentsMargins(0, 0, 0, 0)
        self.dialog_box = DialogBox()
        self.send_box = ChatSendBox()
        self.send_box.addVoiceButton()
        # Подключаем ЛОКАЛЬНЫЙ сигнал send_box к диалогу
       

        # Показываем кнопку микрофона (скрыта по умолчанию)
        # Кнопка уже подключена в ChatSendBox к toggle_voice_recording
        self.send_box.voice_btn.setVisible(True)

        self.text_input_lay.addWidget(self.dialog_box, 2)
        self.text_input_lay.addWidget(self.send_box, 1)

    def _apply_theme(self, theme: dict):
        """Обновляет стили страницы голосового ввода."""
        super()._apply_theme(theme)
        self.setStyleSheet(theme["input_page"])
        self.dialog_box._apply_theme(theme)
        self.send_box._apply_theme(theme)


# ===========================================================
# ТЕКСТОВЫЙ ВВОД
# ===========================================================
class TextInput(ContentPageWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(THEMES[SELECTED_THEME]["input_page"])
        self.side_panel_btn.setText("Текстовый Ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("text.png"))) 
        self.text_input_lay = QVBoxLayout(self)
        self.text_input_lay.setContentsMargins(0, 0, 0, 0)
        self.dialog_box = DialogBox()
        self.send_box = ChatSendBox()
        # Подключаем ЛОКАЛЬНЫЙ сигнал send_box к диалогу
      

        self.text_input_lay.addWidget(self.dialog_box, 2)
        self.text_input_lay.addWidget(self.send_box, 1)

    def _apply_theme(self, theme: dict):
        """Обновляет стили страницы текстового ввода."""
        super()._apply_theme(theme)
        self.setStyleSheet(theme["input_page"])
        self.dialog_box._apply_theme(theme)
        self.send_box._apply_theme(theme)


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
        self.chat_lay.setContentsMargins(0, 0, 0, 0)
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
        self.camera_frame.setStyleSheet(THEMES[SELECTED_THEME]["gestures_camera_frame"])
        self.bottom_lay.addWidget(self.camera_frame, stretch=1)

        self.camera_lay = QVBoxLayout(self.camera_frame)
        self.camera_lay.setContentsMargins(10, 10, 10, 10)
        self.camera_lay.setSpacing(5)

        # Лейбл для отображения кадра (тоже скруглённые углы)
        self.camera_preview_label = QLabel("Нажмите «Старт» для запуска")
        self.camera_preview_label.setStyleSheet(THEMES[SELECTED_THEME]["camera_preview_label"])
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_label.setMinimumSize(320, 240)
        self.camera_preview_label.setScaledContents(False)
        self.camera_lay.addWidget(self.camera_preview_label, stretch=1)

        # Кнопки старт/стоп снизу
        self.camera_btn_lay = QHBoxLayout()
        self.camera_btn_lay.setSpacing(10)

        self.start_btn = QPushButton("Старт")
        self.start_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_3"])
        self.start_btn.clicked.connect(self.start_camera)
        self.camera_btn_lay.addWidget(self.start_btn)   

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setStyleSheet(THEMES[SELECTED_THEME]["btn_4"])
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)
        self.camera_btn_lay.addWidget(self.stop_btn)

        self.camera_lay.addLayout(self.camera_btn_lay)

        self.chat_lay.addLayout(self.bottom_lay)

    def _apply_theme(self, theme: dict):
        """Обновляет стили страницы жестового ввода."""
        super()._apply_theme(theme)
        self.setStyleSheet(theme["input_page"])
        self.dialog_box._apply_theme(theme)
        self.send_box._apply_theme(theme)
        self.camera_frame.setStyleSheet(theme["gestures_camera_frame"])
        self.camera_preview_label.setStyleSheet(theme["camera_preview_label"])
        self.start_btn.setStyleSheet(theme["btn_3"])
        self.stop_btn.setStyleSheet(theme["btn_4"])

    def start_camera(self):

        if self.camera_thread is not None and self.camera_thread.isRunning():
            return

        # Сбрасываем защиту от дублирования при каждом запуске
        self.send_box._last_gesture_text = ""
        self.send_box._gesture_processing = False

        self.camera_thread = GestureCameraThread(camera_index=0)
        self.camera_thread.frame_ready.connect(self.on_frame_ready)
        self.camera_thread.status_ready.connect(self.on_status_ready)
        self.camera_thread.command_ready.connect(lambda cmd: self.send_box.gesture_text_ready.emit(cmd))
        self.camera_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_camera(self):
        """Останавливает поток камеры."""
        if self.camera_thread is not None and self.camera_thread.isRunning():
            # Отключаем сигналы перед остановкой
            self.camera_thread.frame_ready.disconnect()
            self.camera_thread.status_ready.disconnect()
            self.camera_thread.command_ready.disconnect()
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

    def _apply_theme(self, theme: dict):
        """Обновляет стили страницы жестов."""
        super()._apply_theme(theme)
        self.dialog_box._apply_theme(theme)
        self.send_box._apply_theme(theme)
        self.camera_frame.setStyleSheet(theme["gestures_camera_frame"])
        self.camera_preview_label.setStyleSheet(theme["camera_preview_label"])
        self.start_btn.setStyleSheet(theme["btn_3"])
        self.stop_btn.setStyleSheet(theme["btn_4"])
    
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