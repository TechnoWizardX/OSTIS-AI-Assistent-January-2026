from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QTextEdit, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import QIcon, QTextOption
import os
from src.gui.themes import THEMES, _COLOR_MAP, SELECTED_THEME
from src.gui.signals import ui_signals
from src.gui import icon_path

from src.utils.database import DATABASE_EDITOR

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
