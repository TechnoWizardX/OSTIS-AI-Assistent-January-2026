# src/gui/pages/gestures_page.py

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPainterPath, QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel, QSplitter
from src.gui.pages.base_input_page import BaseInputPage
from src.gui.themes import THEMES
from src.utils.config import get_settings_config_value
from src.utils.logger import logger
from src.GesturesInput.gestures import GestureCameraThread   # оригинальный модуль жестов
from src.gui import icon_path

class GesturesPage(BaseInputPage):
    """
    Страница жестового ввода: чат, поле ввода и превью камеры с распознаванием жестов.
    """

    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Жестовый ввод")
        self.side_panel_btn.setIcon(QIcon(icon_path("camera.png")))

        self.camera_thread = None
        self._gesture_processing = False
        self._last_gesture_text = ""

        # Перестраиваем layout, добавляя камеру
        self._rebuild_layout()

    def _rebuild_layout(self):
        """
        Заменяет стандартный вертикальный сплиттер из BaseInputPage на новый,
        где внизу идут горизонтально send_box и камера.
        """
        # Удаляем старый layout, если есть
        if self.layout():
            self.layout().deleteLater()

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)

        # Верхняя часть: чат (dialog_box)
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chat_splitter.setHandleWidth(6)
        self.chat_splitter.setChildrenCollapsible(False)
        self.chat_splitter.setStyleSheet("""
            QSplitter::handle { background-color: transparent; border-radius: 3px; }
            QSplitter::handle:hover { background-color: transparent; }
        """)

        # Нижний горизонтальный блок: send_box + камера
        bottom_widget = QWidget()
        bottom_lay = QHBoxLayout(bottom_widget)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(10)

        # send_box – поле ввода (уже создан в BaseInputPage)
        bottom_lay.addWidget(self.send_box, stretch=1)

        # Камера и кнопки
        self.camera_frame = QFrame()
        self.camera_frame.setStyleSheet(THEMES[get_settings_config_value("theme")]["gestures_camera_frame"])
        bottom_lay.addWidget(self.camera_frame, stretch=1)

        camera_lay = QVBoxLayout(self.camera_frame)
        camera_lay.setContentsMargins(10, 10, 10, 10)
        camera_lay.setSpacing(5)

        self.camera_preview_label = QLabel("Нажмите «Старт» для запуска")
        self.camera_preview_label.setStyleSheet(THEMES[get_settings_config_value("theme")]["camera_preview_label"])
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_label.setMinimumSize(320, 240)
        self.camera_preview_label.setScaledContents(False)
        camera_lay.addWidget(self.camera_preview_label, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("Старт")
        self.start_btn.setStyleSheet(THEMES[get_settings_config_value("theme")]["btn_3"])
        self.start_btn.clicked.connect(self.start_camera)

        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setStyleSheet(THEMES[get_settings_config_value("theme")]["btn_4"])
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        camera_lay.addLayout(btn_layout)

        # Собираем сплиттер: чат сверху, bottom_widget снизу
        self.chat_splitter.addWidget(self.dialog_box)
        self.chat_splitter.addWidget(bottom_widget)
        self.chat_splitter.setSizes([400, 250])
        self.chat_splitter.setStretchFactor(0, 1)
        self.chat_splitter.setStretchFactor(1, 0)

        main_lay.addWidget(self.chat_splitter)
        self.setLayout(main_lay)

    # ---------- Управление камерой ----------
    def start_camera(self):
        if self.camera_thread is not None and self.camera_thread.isRunning():
            return

        # Сбрасываем защиту от дублирования
        self.send_box._last_gesture_text = ""
        self.send_box._gesture_processing = False

        camera_index = get_settings_config_value("camera_index", 0)
        self.camera_thread = GestureCameraThread(camera_index=camera_index)
        self.camera_thread.frame_ready.connect(self.on_frame_ready)
        self.camera_thread.status_ready.connect(self.on_status_ready)
        self.camera_thread.command_ready.connect(lambda cmd: self.send_box.gesture_text_ready.emit(cmd))
        self.camera_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_camera(self):
        if self.camera_thread is not None and self.camera_thread.isRunning():
            self.camera_thread.frame_ready.disconnect()
            self.camera_thread.status_ready.disconnect()
            self.camera_thread.command_ready.disconnect()
            self.camera_thread.stop()
            self.camera_thread = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.camera_preview_label.clear()
        self.camera_preview_label.setText("Нажмите «Старт» для запуска")

    def on_frame_ready(self, q_image: QImage):
        """Отображает кадр с камеры со скруглёнными углами."""
        if q_image.isNull():
            return
        label_size = self.camera_preview_label.size()
        scaled = q_image.scaled(label_size.width(), label_size.height(),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
        rounded = self._rounded_image(scaled, radius=8)
        self.camera_preview_label.setPixmap(QPixmap.fromImage(rounded))

    def on_status_ready(self, status: str):
        """Обработка статуса распознавания (опционально)."""
        # Можно выводить в консоль или строку состояния
        logger.debug(f"Статус жестов: {status}")

    @staticmethod
    def _rounded_image(image: QImage, radius: int = 12) -> QImage:
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

    # ---------- Применение темы ----------
    def _apply_theme(self, theme: dict):
        """Обновляет стили страницы жестов."""
        super()._apply_theme(theme)
        if hasattr(self, 'camera_frame'):
            self.camera_frame.setStyleSheet(theme["gestures_camera_frame"])
            self.camera_preview_label.setStyleSheet(theme["camera_preview_label"])
            self.start_btn.setStyleSheet(theme["btn_3"])
            self.stop_btn.setStyleSheet(theme["btn_4"])