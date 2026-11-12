"""Вкладка «Благополучие»: использование приложений за текущую неделю."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.gui.pages.base_page import ContentPageWidget
from src.gui.signals import ui_signals
from src.gui.widgets.toggle_switch import ToggleSwitchRow
from src.gui.widgets.well_being import AppUsageList, MetricCard, WellBeingChart
from src.modules.well_being.app_names import display_name, format_duration
from src.modules.well_being.usage_tracker import get_usage_tracker
from src.utils.config_manager import (
    get_settings_config_value,
    set_settings_config_value,
)
from src.utils.database import DATABASE_EDITOR
from src.utils.icons import set_theme_icon
from src.utils.logger import logger

_DAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
_MONTHS_GENITIVE = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


class WellBeingPage(ContentPageWidget):
    """Метрики использования приложений текущего профиля за неделю."""

    def __init__(self, user_id: int = 0):
        super().__init__()
        self._user_id = user_id

        self.side_panel_btn.setText("Благополучие")
        set_theme_icon(self.side_panel_btn, "activity.svg")

        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(0, 0, 0, 0)
        self.main_frame = QFrame()
        self.main_frame.setObjectName("dialogFrame")
        self.main_lay.addWidget(self.main_frame)

        self.frame_lay = QVBoxLayout(self.main_frame)
        self.frame_lay.setContentsMargins(12, 8, 12, 8)
        self.frame_lay.setSpacing(5)

        self._build_header()
        self._build_controls()
        self._build_tracking()
        self._build_cards()

        self.chart = WellBeingChart()
        self.chart.setFixedHeight(140)
        self.frame_lay.addWidget(self.chart)

        self.app_list = AppUsageList()
        self.frame_lay.addWidget(self.app_list, 1)

        self.note_label = QLabel(
            "Статистика хранится локально и привязана к профилю."
        )
        self.note_label.setObjectName("wellBeingNote")
        self.frame_lay.addWidget(self.note_label)

        ui_signals.settings_changed.connect(self._on_settings_changed)
        ui_signals.app_usage_updated.connect(self._on_usage_updated)

    # --- построение интерфейса ---
    def _build_header(self) -> None:
        header = QHBoxLayout()
        header.setSpacing(8)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(0)

        self.title_label = QLabel("Благополучие")
        self.title_label.setObjectName("wellBeingTitle")
        self.subtitle_label = QLabel(
            "Использование приложений за текущую неделю"
        )
        self.subtitle_label.setObjectName("wellBeingSubtitle")

        text_lay.addWidget(self.title_label)
        text_lay.addWidget(self.subtitle_label)

        self.range_label = QLabel("")
        self.range_label.setObjectName("wellBeingSubtitle")
        self.range_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
        )

        header.addLayout(text_lay)
        header.addStretch(1)
        header.addWidget(self.range_label)
        self.frame_lay.addLayout(header)

    def _build_controls(self) -> None:
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.setMinimumHeight(30)
        self.refresh_btn.clicked.connect(self.refresh)

        controls.addWidget(self.refresh_btn)
        controls.addStretch(1)
        self.frame_lay.addLayout(controls)

    def _build_tracking(self) -> None:
        self.tracking_toggle = ToggleSwitchRow(
            "Учитывать использование приложений"
        )
        self.tracking_toggle.setChecked(
            bool(get_settings_config_value("well_being_tracking_enabled"))
        )
        self.frame_lay.addWidget(self.tracking_toggle)
        # Подключаемся после setChecked, чтобы не запускать трекер при создании.
        self.tracking_toggle.toggled.connect(self._on_tracking_toggled)

    def _build_cards(self) -> None:
        cards = QHBoxLayout()
        cards.setSpacing(8)

        self.total_card = MetricCard("Всего за неделю")
        self.average_card = MetricCard("В среднем за день")
        self.top_card = MetricCard("Больше всего времени")

        for card in (self.total_card, self.average_card, self.top_card):
            cards.addWidget(card, 1)
        self.frame_lay.addLayout(cards)

    # --- события ---
    def showEvent(self, event) -> None:
        super().showEvent(event)
        tracker = get_usage_tracker()
        if self.tracking_toggle.isChecked() and not tracker.is_running():
            tracker.start()
        self.refresh()

    def _on_settings_changed(self, changes: dict) -> None:
        if "theme" in changes:
            self.chart.apply_theme()

    def _on_usage_updated(self) -> None:
        if self.isVisible():
            self.refresh()

    def _on_tracking_toggled(self, enabled: bool) -> None:
        set_settings_config_value(
            "well_being_tracking_enabled", bool(enabled)
        )
        get_usage_tracker().set_enabled(bool(enabled))
        self.refresh()

    # --- данные ---
    @staticmethod
    def _current_week(today: date) -> tuple[date, date]:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    def refresh(self) -> None:
        today = date.today()
        week_start, week_end = self._current_week(today)
        start_str = week_start.isoformat()
        end_str = week_end.isoformat()

        error_message = None
        try:
            rows = DATABASE_EDITOR.get_user_apps_usage_daily(
                self._user_id, start_str, end_str
            )
        except Exception as error:
            logger(
                "WellBeingPage",
                "ERROR",
                f"Не удалось прочитать статистику: {error}",
            )
            rows = []
            error_message = "Не удалось прочитать статистику. Попробуйте обновить."

        day_index = {
            week_start + timedelta(days=offset): offset
            for offset in range(7)
        }
        day_totals = [0.0] * 7
        per_app: dict[str, list[float]] = {}

        for date_str, app_name, hours in rows:
            if hours <= 0:
                continue
            try:
                usage_date = date.fromisoformat(date_str[:10])
            except ValueError:
                logger(
                    "WellBeingPage",
                    "WARNING",
                    f"Некорректная дата в статистике: {date_str!r}",
                )
                continue
            offset = day_index.get(usage_date)
            if offset is None:
                continue
            name = display_name(app_name)
            per_app.setdefault(name, [0.0] * 7)[offset] += hours
            day_totals[offset] += hours

        app_totals = {
            name: sum(values) for name, values in per_app.items()
        }
        ordered_apps = sorted(
            app_totals.items(), key=lambda item: item[1], reverse=True
        )

        today_index = today.weekday()
        today_items = []
        for name, values in per_app.items():
            hours = values[today_index]
            if hours > 0:
                today_items.append((name, hours))
        today_items.sort(key=lambda item: item[1], reverse=True)
        today_total = sum(hours for _, hours in today_items)
        today_rows = [
            (
                name,
                hours,
                hours / today_total if today_total else 0.0,
            )
            for name, hours in today_items
        ]

        total_hours = sum(day_totals)
        active_days = sum(1 for total in day_totals if total > 0)

        range_text = self._format_range(week_start, week_end)
        self.range_label.setText(range_text)
        self.total_card.set_value(format_duration(total_hours), range_text)

        if active_days:
            average_hint = f"за {active_days} {self._days_word(active_days)}"
        else:
            average_hint = "нет данных"
        self.average_card.set_value(
            format_duration(total_hours / active_days if active_days else 0.0),
            average_hint,
        )

        if ordered_apps:
            top_name, top_hours = ordered_apps[0]
            percent = top_hours / total_hours * 100 if total_hours else 0
            self.top_card.set_value(
                top_name,
                f"{format_duration(top_hours)} · {percent:.0f}%",
            )
        else:
            self.top_card.set_value("—", "")

        if total_hours > 0:
            self.chart.set_usage(_DAY_LABELS, day_totals, today_index)
            self.app_list.set_items(today_rows, today_total)
            return

        if error_message:
            message = error_message
        elif self.tracking_toggle.isChecked():
            message = "Данные появятся через несколько минут после включения учёта."
        else:
            message = "Учёт использования приложений выключен. Включите его выше."
        self.chart.set_empty_message(message)
        self.chart.set_usage([], [], None)
        self.app_list.set_items([], 0.0)

    # --- форматирование ---
    @staticmethod
    def _days_word(count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return "день"
        if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
            return "дня"
        return "дней"

    @staticmethod
    def _format_range(start: date, end: date) -> str:
        if start == end:
            return f"{start.day} {_MONTHS_GENITIVE[start.month - 1]} {start.year}"

        if start.year == end.year and start.month == end.month:
            return (
                f"{start.day}–{end.day} "
                f"{_MONTHS_GENITIVE[start.month - 1]} {start.year}"
            )

        if start.year == end.year:
            return (
                f"{start.day} {_MONTHS_GENITIVE[start.month - 1]} – "
                f"{end.day} {_MONTHS_GENITIVE[end.month - 1]} {start.year}"
            )

        return (
            f"{start.day} {_MONTHS_GENITIVE[start.month - 1]} {start.year} – "
            f"{end.day} {_MONTHS_GENITIVE[end.month - 1]} {end.year}"
        )
