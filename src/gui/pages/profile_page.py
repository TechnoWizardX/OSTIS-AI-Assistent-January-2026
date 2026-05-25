from PyQt6.QtWidgets import ( QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QFont, QIcon, QPixmap
from .base_page import ContentPageWidget
from src.gui import icon_path
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from src.gui.signals import ui_signals
from src.gui.widgets.options import ProfileOption, DysfunctionsProfileOption, RecommendationBadge
from src.utils.database import DATABASE_EDITOR


class ProfilePage(ContentPageWidget):
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
        for opt in [self.sn_fn_patr, self.birthday, self.gender, self.dysfunctions]:
            opt._apply_theme(theme)