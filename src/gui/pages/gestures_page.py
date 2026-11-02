# src/gui/pages/gestures_page.py

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                             QSplitter, QVBoxLayout, QWidget)

from src.GesturesInput.gestures import GestureCameraThread
from src.gui.pages.base_input_page import BaseInputPage
from src.utils.config import get_settings_config_value
from src.utils.icons import set_theme_icon


class GesturesPage(BaseInputPage):
    """
    Страница жестового ввода: чат, поле ввода и превью камеры с распознаванием жестов.
    """

    def __init__(self):
        super().__init__()
        self.side_panel_btn.setText("Жестовый ввод")
        set_theme_icon(self.side_panel_btn, "camera.svg")

        self.camera_thread = None
        self._gesture_processing = False
        self._last_gesture_text = ""

        self._rebuild_layout()

    def _rebuild_layout(self):
        """
        Перестраивает layout: берёт уже созданные виджеты из BaseInputPage
        (dialog_box, send_box) и добавляет к ним блок с камерой.
        """
        # 1. Отсоединяем виджеты от текущего родителя (старый сплиттер/layout)
        self.dialog_box.setParent(None)
        self.send_box.setParent(None)

        # 2. Полностью очищаем старый layout (без удаления самих виджетов)
        old_layout = self.layout()
        if old_layout is not None:
            # Извлекаем все элементы
            while old_layout.count():
                item = old_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)
            # Убираем сам layout — присваиваем временному объекту, чтобы Qt его удалил
            QWidget().setLayout(old_layout)

        # 3. Новый корневой layout
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # 4. Вертикальный сплиттер: чат сверху, нижний блок снизу
        self.chat_splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.chat_splitter.setObjectName("cameraSplitter")
        self.chat_splitter.setHandleWidth(6)
        self.chat_splitter.setChildrenCollapsible(False)

        # 5. Нижний блок: send_box слева, камера справа
        bottom_widget = QWidget(self.chat_splitter)
        bottom_lay = QHBoxLayout(bottom_widget)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(10)

        # send_box из базового класса
        self.send_box.setParent(bottom_widget)
        bottom_lay.addWidget(self.send_box, stretch=1)

        # Блок камеры
        self.camera_frame = QFrame(bottom_widget)
        self.camera_frame.setObjectName("gesturesCameraFrame")
        bottom_lay.addWidget(self.camera_frame, stretch=1)

        camera_lay = QVBoxLayout(self.camera_frame)
        camera_lay.setContentsMargins(10, 10, 10, 10)
        camera_lay.setSpacing(5)

        self.camera_preview_label = QLabel("Нажмите «Старт» для запуска", self.camera_frame)
        self.camera_preview_label.setObjectName("cameraPreviewLabel")
        self.camera_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_preview_label.setMinimumSize(320, 240)
        self.camera_preview_label.setScaledContents(False)
        camera_lay.addWidget(self.camera_preview_label, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("Старт", self.camera_frame)
        self.start_btn.setObjectName("accentButton")
        self.start_btn.clicked.connect(self.start_camera)

        self.stop_btn = QPushButton("Стоп", self.camera_frame)
        self.stop_btn.setObjectName("dangerButton")
        self.stop_btn.clicked.connect(self.stop_camera)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        camera_lay.addLayout(btn_layout)

        # 6. Собираем сплиттер
        self.dialog_box.setParent(self.chat_splitter)
        self.chat_splitter.addWidget(self.dialog_box)
        self.chat_splitter.addWidget(bottom_widget)
        self.chat_splitter.setSizes([400, 250])
        self.chat_splitter.setStretchFactor(0, 1)
        self.chat_splitter.setStretchFactor(1, 0)

        main_lay.addWidget(self.chat_splitter)

    # ---------- Управление камерой ----------

    def start_camera(self):
        if self.camera_thread is not None and self.camera_thread.isRunning():
            return

        self.send_box._last_gesture_text = ""
        self.send_box._gesture_processing = False

        camera_index = get_settings_config_value("camera_index")
        self.camera_thread = GestureCameraThread(camera_index=camera_index)
        self.camera_thread.frame_ready.connect(self.on_frame_ready)
        self.camera_thread.status_ready.connect(self.on_status_ready)
        self.camera_thread.command_ready.connect(
            lambda cmd: self.send_box.gesture_text_ready.emit(cmd)
        )
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
        scaled = q_image.scaled(
            label_size.width(), label_size.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        rounded = self._rounded_image(scaled, radius=8)
        self.camera_preview_label.setPixmap(QPixmap.fromImage(rounded))

    def on_status_ready(self, status: str):
        print(f"Статус жестов: {status}")

    @staticmethod
    def _rounded_image(image: QImage, radius: int = 12) -> QImage:
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
