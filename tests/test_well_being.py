"""Тесты модуля «Благополучие»."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication

from src.modules.well_being.app_names import (
    format_axis_hours,
    format_duration,
)
from src.modules.well_being.usage_tracker import UsageTracker
from src.utils.database import DataBaseEditor


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
