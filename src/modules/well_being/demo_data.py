"""Fixture data for previewing the wellbeing dashboard."""

from __future__ import annotations

from datetime import date, timedelta

from src.utils.database import DATABASE_EDITOR, DataBaseEditor

_DEMO_WEEK = (
    (0, "demo_code", 2.0),
    (0, "demo_firefox", 0.5),
    (1, "demo_code", 2.5),
    (1, "demo_telegram", 1.1),
    (1, "demo_spotify", 0.3),
    (2, "demo_code", 1.8),
    (2, "demo_kb_studio", 0.7),
    (3, "demo_telegram", 1.4),
    (3, "demo_firefox", 0.6),
    (4, "demo_code", 3.0),
    (4, "demo_spotify", 0.5),
    (5, "demo_onlyoffice", 1.5),
    (5, "demo_spotify", 1.0),
    (6, "demo_firefox", 0.4),
    (6, "demo_telegram", 0.8),
)


def load_demo_week(
    user_id: int,
    week_start: date | None = None,
    database: DataBaseEditor | None = None,
) -> int:
    """Load an idempotent demo week, defaulting to the current Monday."""
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    editor = database or DATABASE_EDITOR
    return editor.replace_demo_app_usage_week(
        user_id, week_start, list(_DEMO_WEEK)
    )
