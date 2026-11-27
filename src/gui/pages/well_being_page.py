"""Вкладка «Благополучие»: использование приложений за текущую неделю."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from src.gui.pages.base_page import ContentPageWidget
from src.gui.signals import ui_signals
from src.gui.widgets.toggle_switch import ToggleSwitch
from src.gui.widgets.well_being import AppUsageList, MetricCard, WellBeingChart
from src.modules.well_being.app_names import display_name, format_duration
from src.modules.well_being.demo_data import load_demo_week
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
        self.frame_lay.setContentsMargins(14, 12, 14, 12)
        self.frame_lay.setSpacing(10)

        self._build_header()
        self._build_dashboard()

        self.app_list = AppUsageList()
        self.frame_lay.addWidget(self.app_list, 1)

        self.note_label = QLabel(
            "Статистика хранится локально и привязана к профилю."
        )
        self.note_label.setObjectName("wellBeingNote")
        self.frame_lay.addWidget(self.note_label)

        self._week_offset = 0
        self._day_offset = 0
        self._period_mode = "week"
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
        self.subtitle_label = QLabel("Использование приложений")
        self.subtitle_label.setObjectName("wellBeingSubtitle")

        text_lay.addWidget(self.title_label)
        text_lay.addWidget(self.subtitle_label)

        header.addLayout(text_lay)
        header.addStretch(1)
        self.period_group = QButtonGroup(self)
        self.period_group.setExclusive(True)
        self.day_btn = QPushButton("День")
        self.day_btn.setObjectName("wellBeingModeButton")
        self.day_btn.setCheckable(True)
        self.week_btn = QPushButton("Неделя")
        self.week_btn.setObjectName("wellBeingModeButton")
        self.week_btn.setCheckable(True)
        self.period_group.addButton(self.day_btn)
        self.period_group.addButton(self.week_btn)
        self.week_btn.setChecked(True)
        self.day_btn.toggled.connect(
            lambda checked: self._set_period_mode("day") if checked else None
        )
        self.week_btn.toggled.connect(
            lambda checked: self._set_period_mode("week") if checked else None
        )

        self.previous_btn = QPushButton()
        self.previous_btn.setObjectName("wellBeingNavButton")
        self.previous_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft)
        )
        self.previous_btn.setIconSize(QSize(16, 16))
        self.previous_btn.setToolTip("Предыдущий период")
        self.previous_btn.clicked.connect(self._show_previous_period)

        self.range_label = QLabel("")
        self.range_label.setObjectName("wellBeingRange")
        self.range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_btn = QPushButton()
        self.next_btn.setObjectName("wellBeingNavButton")
        self.next_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight)
        )
        self.next_btn.setIconSize(QSize(16, 16))
        self.next_btn.setToolTip("Следующий период")
        self.next_btn.clicked.connect(self._show_next_period)

        self.today_btn = QPushButton("Сегодня")
        self.today_btn.setObjectName("wellBeingNavButton")
        self.today_btn.clicked.connect(self._show_today)

        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("wellBeingNavButton")
        set_theme_icon(self.settings_btn, "settings.svg")
        self.settings_btn.setIconSize(QSize(16, 16))
        self.settings_btn.setToolTip("Настройки учёта")
        settings_menu = QMenu(self.settings_btn)
        settings_menu.setObjectName("wellBeingSettingsMenu")
        settings_panel = QFrame()
        settings_panel.setObjectName("wellBeingSettingsPanel")
        settings_panel.setFixedWidth(272)
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(12, 10, 12, 12)
        settings_layout.setSpacing(8)

        settings_title = QLabel("Учёт приложений")
        settings_title.setObjectName("wellBeingSettingsTitle")
        settings_description = QLabel(
            "Статистика хранится локально. Демо-загрузка заменяет только "
            "тестовые записи за текущую неделю."
        )
        settings_description.setObjectName("wellBeingSettingsDescription")
        settings_description.setWordWrap(True)

        tracking_row = QFrame()
        tracking_row.setObjectName("wellBeingSettingsRow")
        tracking_layout = QHBoxLayout(tracking_row)
        tracking_layout.setContentsMargins(10, 6, 10, 6)
        tracking_layout.setSpacing(8)
        tracking_label = QLabel("Вести учёт")
        tracking_label.setObjectName("wellBeingTrackingLabel")
        self.tracking_toggle = ToggleSwitch()
        self.tracking_toggle.setChecked(
            bool(get_settings_config_value("well_being_tracking_enabled"))
        )
        tracking_layout.addWidget(tracking_label, 1)
        tracking_layout.addWidget(self.tracking_toggle)
        self.tracking_toggle.toggled.connect(self._on_tracking_toggled)

        self.demo_button = QPushButton("Загрузить демо-неделю")
        self.demo_button.setObjectName("wellBeingDemoButton")
        self.demo_button.clicked.connect(self._load_demo_week)
        self.demo_status = QLabel("")
        self.demo_status.setObjectName("wellBeingDemoStatus")
        self.demo_status.setWordWrap(True)

        settings_layout.addWidget(settings_title)
        settings_layout.addWidget(settings_description)
        settings_layout.addWidget(tracking_row)
        settings_layout.addWidget(self.demo_button)
        settings_layout.addWidget(self.demo_status)
        settings_action = QWidgetAction(settings_menu)
        settings_action.setDefaultWidget(settings_panel)
        settings_menu.addAction(settings_action)
        self.settings_btn.setMenu(settings_menu)

        header.addWidget(self.day_btn)
        header.addWidget(self.week_btn)
        header.addWidget(self.previous_btn)
        header.addWidget(self.range_label)
        header.addWidget(self.next_btn)
        header.addWidget(self.today_btn)
        header.addWidget(self.settings_btn)
        self.frame_lay.addLayout(header)

    def _build_dashboard(self) -> None:
        self.dashboard_panel = QWidget()
        self.dashboard_panel.setObjectName("wellBeingDashboard")
        dashboard = QHBoxLayout(self.dashboard_panel)
        dashboard.setSpacing(10)

        self.chart_panel = QFrame()
        self.chart_panel.setObjectName("wellBeingPanel")
        chart_layout = QVBoxLayout(self.chart_panel)
        chart_layout.setContentsMargins(12, 10, 12, 8)
        chart_layout.setSpacing(4)

        self.chart_title = QLabel("Использование по дням")
        self.chart_title.setObjectName("wellBeingPanelTitle")
        chart_layout.addWidget(self.chart_title)

        self.chart = WellBeingChart()
        self.chart.setMinimumHeight(175)
        chart_layout.addWidget(self.chart, 1)
        dashboard.addWidget(self.chart_panel, 3)

        metrics = QVBoxLayout()
        metrics.setSpacing(8)
        self.total_card = MetricCard("Итого за неделю")
        self.average_card = MetricCard("В среднем за день")
        self.top_card = MetricCard("Самое используемое")
        for card in (self.total_card, self.average_card, self.top_card):
            metrics.addWidget(card, 1)
        dashboard.addLayout(metrics, 2)

        self.frame_lay.addWidget(self.dashboard_panel, 2)

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

    def _load_demo_week(self) -> None:
        today = date.today()
        week_start, _ = self._current_week(today)
        try:
            row_count = load_demo_week(self._user_id, week_start)
        except Exception as error:
            logger(
                "WellBeingPage",
                "ERROR",
                f"Не удалось загрузить демо-неделю: {error}",
            )
            self.demo_status.setText(
                "Не удалось загрузить демо-данные. Проверьте журнал ошибок."
            )
            return

        self.demo_status.setText(
            f"Загружено тестовых записей: {row_count}"
        )
        self._week_offset = 0
        self._day_offset = 0
        if self._period_mode == "day":
            self.week_btn.setChecked(True)
        else:
            self.refresh()

    # --- данные ---
    @staticmethod
    def _current_week(today: date) -> tuple[date, date]:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    @classmethod
    def _week_for_offset(
        cls, today: date, offset: int
    ) -> tuple[date, date]:
        start, end = cls._current_week(today)
        delta = timedelta(weeks=offset)
        return start + delta, end + delta

    def _set_period_mode(self, mode: str) -> None:
        self._period_mode = mode
        self._week_offset = 0
        self._day_offset = 0
        self.refresh()

    def _show_previous_period(self) -> None:
        if self._period_mode == "day":
            self._day_offset -= 1
        else:
            self._week_offset -= 1
        self.refresh()

    def _show_next_period(self) -> None:
        if self._period_mode == "day":
            self._day_offset += 1
        else:
            self._week_offset += 1
        self.refresh()

    def _show_today(self) -> None:
        self._week_offset = 0
        self._day_offset = 0
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        selected_date = (
            today + timedelta(days=self._day_offset)
            if self._period_mode == "day"
            else today + timedelta(weeks=self._week_offset)
        )
        if self._period_mode == "day":
            week_start, week_end = self._current_week(selected_date)
        else:
            week_start, week_end = self._week_for_offset(
                today, self._week_offset
            )
        start_str = week_start.isoformat()
        end_str = week_end.isoformat()
        period_offset = (
            self._day_offset
            if self._period_mode == "day"
            else self._week_offset
        )
        self.today_btn.setEnabled(period_offset != 0)

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

        total_hours = sum(day_totals)
        active_days = sum(1 for total in day_totals if total > 0)
        selected_items = [
            (name, values[selected_date.weekday()])
            for name, values in per_app.items()
            if values[selected_date.weekday()] > 0
        ]
        selected_items.sort(key=lambda item: item[1], reverse=True)
        selected_total = sum(hours for _, hours in selected_items)

        range_text = (
            self._format_range(selected_date, selected_date)
            if self._period_mode == "day"
            else self._format_range(week_start, week_end)
        )
        self.range_label.setText(range_text)

        if self._period_mode == "day":
            self.chart_title.setText("Неделя по дням")
            self.total_card.title_label.setText("Итого за день")
            self.total_card.set_animated_value(
                selected_total, format_duration
            )
            self.average_card.title_label.setText("Приложений")
            self.average_card.set_animated_value(
                float(len(selected_items)),
                lambda value: str(int(round(value))),
                "за день",
            )
            if selected_items:
                top_name, top_hours = selected_items[0]
                percent = top_hours / selected_total * 100
                self.top_card.title_label.setText("Самое используемое")
                self.top_card.set_value(
                    top_name,
                    f"{format_duration(top_hours)} · {percent:.0f}%",
                )
            else:
                self.top_card.set_value("—", "")
        else:
            self.chart_title.setText("Использование по дням")
            self.total_card.title_label.setText("Итого за неделю")
            self.total_card.set_animated_value(
                total_hours, format_duration
            )
            self.average_card.title_label.setText("В среднем за день")
            self.top_card.title_label.setText("Самое используемое")
            if active_days:
                average_hint = f"за {active_days} {self._days_word(active_days)}"
            else:
                average_hint = "нет данных"
            self.average_card.set_animated_value(
                total_hours / active_days if active_days else 0.0,
                format_duration,
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
            if self._period_mode == "day":
                chart_index = selected_date.weekday()
                highlight_label = (
                    "Сегодня" if selected_date == today else "Выбрано"
                )
            else:
                chart_index = (
                    selected_date.weekday()
                    if self._week_offset == 0
                    else None
                )
                highlight_label = "Сегодня" if chart_index is not None else ""
            self.chart.set_usage(
                _DAY_LABELS, day_totals, chart_index, highlight_label
            )
        else:
            if error_message:
                message = error_message
            elif self.tracking_toggle.isChecked():
                message = "Данные появятся через несколько минут после включения учёта."
            else:
                message = "Учёт использования приложений выключен. Включите его в настройках."
            self.chart.set_empty_message(message)
            self.chart.set_usage([], [], None)

        if self._period_mode == "day":
            self.app_list.title_label.setText("Приложения за день")
            period_rows = [
                (name, hours, hours / selected_total if selected_total else 0.0)
                for name, hours in selected_items
            ]
            self.app_list.set_items(period_rows, selected_total)
        else:
            self.app_list.title_label.setText("Приложения за неделю")
            weekly_rows = [
                (name, hours, hours / total_hours if total_hours else 0.0)
                for name, hours in ordered_apps
            ]
            self.app_list.set_items(weekly_rows, total_hours)

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
