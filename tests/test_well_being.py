"""Тесты модуля «Благополучие»."""

import os
import sys
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.gui.pages.well_being_page import WellBeingPage
from src.gui.widgets.well_being import (
    AppUsageList,
    MetricCard,
    WellBeingChart,
)
from src.modules.well_being.app_names import (
    format_axis_hours,
    format_duration,
)
from src.modules.well_being.demo_data import load_demo_week
from src.modules.well_being.usage_tracker import UsageTracker
from src.utils.database import DATABASE_EDITOR, DataBaseEditor


class FakeDB:
    def __init__(self):
        self.rows = []

    def log_app_usage(self, user_id, app_name, hours, date_str):
        self.rows.append((user_id, app_name, hours, date_str))


class WellBeingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _editor(self) -> DataBaseEditor:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return DataBaseEditor(Path(tmp.name) / "database.sqlite3")

    def test_format_duration(self):
        self.assertEqual(format_duration(0.0), "0 мин")
        self.assertEqual(format_duration(1 / 3600), "<1 мин")
        self.assertEqual(format_duration(30 / 3600), "<1 мин")
        self.assertEqual(format_duration(60 / 3600), "1 мин")
        self.assertEqual(format_duration(1.25), "1 ч 15 мин")

    def test_format_axis_hours(self):
        self.assertEqual(format_axis_hours(0.0), "—")
        self.assertEqual(format_axis_hours(1 / 3600), "<1м")
        self.assertEqual(format_axis_hours(30 / 3600), "<1м")
        self.assertEqual(format_axis_hours(60 / 3600), "1м")
        self.assertEqual(format_axis_hours(0.5), "30м")
        self.assertEqual(format_axis_hours(2.0), "2")

    def test_graph_and_metric_values_animate(self):
        chart = WellBeingChart()
        chart.set_usage(
            ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            [2.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            0,
        )
        QTest.qWait(100)
        self.assertTrue(any(value > 0 for value in chart._canvas._display_totals))
        canvas = chart._canvas
        animation_time = canvas._data_animation.currentTime()
        displayed_heights = list(canvas._display_heights)
        chart.set_usage(
            ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            [2.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            0,
        )
        self.assertGreaterEqual(
            canvas._data_animation.currentTime(), animation_time
        )
        chart.set_usage(
            ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            [4.0, 2.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            0,
        )
        self.assertEqual(canvas._display_heights, displayed_heights)
        QTest.qWait(500)
        self.assertEqual(
            chart._canvas._display_totals,
            [4.0, 2.0, 1.0, 0.0, 0.0, 0.0, 0.0],
        )

        card = MetricCard("Время")
        card.set_animated_value(4.0, lambda value: f"{value:.1f}")
        QTest.qWait(100)
        intermediate = float(card.value_text())
        self.assertGreater(intermediate, 0.0)
        self.assertLess(intermediate, 4.0)
        card.set_animated_value(2.0, lambda value: f"{value:.1f}")
        QTest.qWait(450)
        self.assertEqual(card.value_text(), "2.0")

    def test_app_list_reuses_rows_when_period_changes(self):
        app_list = AppUsageList()
        self.addCleanup(app_list.deleteLater)
        app_list.set_items(
            [("Code", 1.0, 0.5), ("Browser", 2.0, 0.5)],
            3.0,
        )
        code_row = app_list._rows["Code"]
        QTest.qWait(300)

        app_list.set_items(
            [("Browser", 1.0, 0.25), ("Code", 3.0, 0.75)],
            4.0,
        )

        self.assertIs(app_list._rows["Code"], code_row)
        self.assertEqual(app_list._row_order, ["Browser", "Code"])
        QTest.qWait(650)
        self.assertEqual(app_list.total_label.text(), format_duration(4.0))
        self.assertEqual(code_row.time_label.text(), format_duration(3.0))
        self.assertEqual(code_row.progress.value(), 750)

    def test_app_list_keeps_scroll_position_on_refresh(self):
        app_list = AppUsageList()
        app_list.resize(360, 180)
        app_list.show()
        self.addCleanup(app_list.deleteLater)
        items = [(f"App {index}", 1.0, 0.1) for index in range(12)]
        app_list.set_items(items, 12.0)
        QTest.qWait(50)

        scrollbar = app_list._scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        position = scrollbar.value()
        app_list.set_items(
            [(name, 2.0, 0.2) for name, _, _ in items],
            24.0,
        )

        self.assertGreater(position, 0)
        self.assertEqual(scrollbar.value(), position)

    def test_week_navigation_bounds(self):
        today = date(2026, 11, 27)
        self.assertEqual(
            WellBeingPage._week_for_offset(today, 0),
            (date(2026, 11, 23), date(2026, 11, 29)),
        )
        self.assertEqual(
            WellBeingPage._week_for_offset(today, -1),
            (date(2026, 11, 16), date(2026, 11, 22)),
        )
        self.assertEqual(
            WellBeingPage._week_for_offset(today, 1),
            (date(2026, 11, 30), date(2026, 12, 6)),
        )

    def test_daily_view_uses_selected_day_data(self):
        today = date.today()
        week_start, _ = WellBeingPage._current_week(today)
        selected_day = week_start + timedelta(days=1)
        rows = [
            (selected_day.isoformat(), "code", 2.2),
            (selected_day.isoformat(), "firefox", 0.3),
            ((selected_day + timedelta(days=2)).isoformat(), "telegram", 1.1),
        ]
        with patch(
            "src.gui.pages.well_being_page.get_settings_config_value",
            return_value=True,
        ), patch(
            "src.gui.pages.well_being_page.set_settings_config_value"
        ), patch(
            "src.gui.pages.well_being_page.load_demo_week", return_value=15
        ), patch.object(
            DATABASE_EDITOR, "get_user_apps_usage_daily", return_value=rows
        ):
            page = WellBeingPage()
            self.addCleanup(page.deleteLater)
            page.refresh()
            QTest.qWait(500)
            self.assertEqual(page.total_card.value_text(), "3 ч 36 мин")

            page.day_btn.click()
            self.assertEqual(page._period_mode, "day")
            page._day_offset = (selected_day - today).days
            page.refresh()
            QTest.qWait(500)

            self.assertEqual(
                page.range_label.text(),
                page._format_range(selected_day, selected_day),
            )
            self.assertEqual(page.total_card.value_text(), "2 ч 30 мин")
            self.assertEqual(page.average_card.value_text(), "2")
            self.assertEqual(
                page.app_list.title_label.text(), "Приложения за день"
            )
            page.demo_button.click()
            self.assertEqual(page._period_mode, "week")
            self.assertEqual(
                page.demo_status.text(), "Загружено тестовых записей: 15"
            )

    def test_demo_week_loader_is_idempotent_and_preserves_real_rows(self):
        editor = self._editor()
        week_start = date(2026, 11, 23)
        editor.log_app_usage(0, "code", 1.0, week_start.isoformat())

        self.assertEqual(load_demo_week(0, week_start, editor), 15)
        self.assertEqual(load_demo_week(0, week_start, editor), 15)

        week_end = (week_start + timedelta(days=6)).isoformat()
        rows = editor.get_user_apps_usage_daily(
            0, week_start.isoformat(), week_end
        )
        demo_rows = [row for row in rows if row[1].startswith("demo_")]
        self.assertEqual(len(demo_rows), 15)
        self.assertIn((week_start.isoformat(), "code", 1.0), rows)

    def test_daily_and_range_aggregation(self):
        editor = self._editor()
        editor.log_app_usage(0, "chrome", 1.0, "2026-11-10")
        editor.log_app_usage(0, "chrome", 0.5, "2026-11-11")
        editor.log_app_usage(0, "code", 2.0, "2026-11-11")
        editor.log_app_usage(1, "chrome", 9.0, "2026-11-11")

        daily = editor.get_user_apps_usage_daily(
            0, "2026-11-10", "2026-11-11"
        )
        self.assertEqual(
            daily,
            [
                ("2026-11-10", "chrome", 1.0),
                ("2026-11-11", "code", 2.0),
                ("2026-11-11", "chrome", 0.5),
            ],
        )

        totals = dict(
            editor.get_user_apps_usage_range(
                0, "2026-11-10", "2026-11-11"
            )
        )
        self.assertEqual(totals, {"chrome": 1.5, "code": 2.0})
        self.assertEqual(
            editor.get_user_usage_active_days(
                0, "2026-11-10", "2026-11-11"
            ),
            2,
        )

    def test_tracker_flushes_elapsed_time(self):
        database = FakeDB()
        tracker = UsageTracker(
            user_id=0,
            database=database,
            app_provider=lambda: "code",
            idle_provider=lambda: 0.0,
            flush_interval_seconds=0.0,
        )
        tracker._last_tick = time.monotonic() - 5.0
        tracker._on_tick()

        self.assertEqual(len(database.rows), 1)
        self.assertEqual(database.rows[0][1], "code")
        self.assertAlmostEqual(database.rows[0][2], 5.0 / 3600.0, places=4)

    def test_tracker_skips_idle_time(self):
        database = FakeDB()
        tracker = UsageTracker(
            user_id=0,
            database=database,
            app_provider=lambda: "code",
            idle_provider=lambda: 9999.0,
            flush_interval_seconds=0.0,
        )
        tracker._last_tick = time.monotonic() - 5.0
        tracker._on_tick()

        self.assertEqual(database.rows, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
