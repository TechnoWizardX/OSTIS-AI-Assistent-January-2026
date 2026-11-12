"""Фоновый учёт времени, проведённого в активном окне.

Опрос активного окна выполняется раз в 5 секунд в главном потоке.
Накопленное время раз в минуту записывается в таблицу ``Users_app_usage``.
Время простоя без ввода мыши или клавиатуры не учитывается.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import date

from PySide6.QtCore import QObject, QTimer, Signal

from src.utils.database import DATABASE_EDITOR, DataBaseEditor
from src.utils.logger import logger

try:
    import psutil
    import win32api
    import win32gui
    import win32process

    _WIN32_API_AVAILABLE = sys.platform == "win32"
except ImportError:  # pragma: no cover - зависит от окружения
    psutil = None
    win32api = None
    win32gui = None
    win32process = None
    _WIN32_API_AVAILABLE = False


POLL_INTERVAL_MS = 5000
FLUSH_INTERVAL_SECONDS = 60.0
IDLE_THRESHOLD_SECONDS = 120.0
MAX_TICK_JUMP_SECONDS = 10.0


def _foreground_process_name() -> str | None:
    """Имя процесса активного окна без ``.exe``, в нижнем регистре."""
    if not _WIN32_API_AVAILABLE:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return None
        if pid == os.getpid():
            return "iamos"
        name = psutil.Process(pid).name().strip()
        if name.lower().endswith(".exe"):
            name = name[:-4]
        return name.lower() or None
    except Exception:
        # Окно могло закрыться между вызовами WinAPI — это нормально.
        return None


def _system_idle_seconds() -> float:
    """Сколько секунд прошло с последнего ввода пользователя."""
    if not _WIN32_API_AVAILABLE:
        return 0.0
    try:
        last_input = win32api.GetLastInputInfo()
        elapsed_ms = win32api.GetTickCount() - last_input
        return max(elapsed_ms, 0) / 1000.0
    except Exception:
        return 0.0


class UsageTracker(QObject):
    """Пишет статистику активного окна в ``Users_app_usage``."""

    usage_flushed = Signal(str)  # ISO-дата, за которую записаны данные

    def __init__(
        self,
        user_id: int = 0,
        database: DataBaseEditor | None = None,
        app_provider=_foreground_process_name,
        idle_provider=_system_idle_seconds,
        tick_interval_ms: int = POLL_INTERVAL_MS,
        flush_interval_seconds: float = FLUSH_INTERVAL_SECONDS,
        idle_threshold_seconds: float = IDLE_THRESHOLD_SECONDS,
        max_tick_jump_seconds: float = MAX_TICK_JUMP_SECONDS,
    ):
        super().__init__()
        self._user_id = user_id
        self._database = database or DATABASE_EDITOR
        self._app_provider = app_provider
        self._idle_provider = idle_provider
        self._flush_interval_seconds = flush_interval_seconds
        self._idle_threshold_seconds = idle_threshold_seconds
        self._max_tick_jump_seconds = max_tick_jump_seconds

        self._pending: dict[str, float] = {}
        self._pending_date = date.today()
        self._last_tick = time.monotonic()
        self._last_flush = self._last_tick

        self._timer = QTimer(self)
        self._timer.setInterval(tick_interval_ms)
        self._timer.timeout.connect(self._on_tick)

    # --- публичный API ---
    def start(self) -> None:
        if self._timer.isActive():
            return
        now = time.monotonic()
        self._last_tick = now
        self._last_flush = now
        self._pending_date = date.today()
        self._timer.start()
        logger(
            "UsageTracker",
            "INFO",
            f"Учёт использования приложений запущен "
            f"(интервал {self._timer.interval()} мс)",
        )

    def stop(self) -> None:
        was_running = self._timer.isActive()
        if was_running:
            self._timer.stop()
        self._flush()
        if was_running:
            logger(
                "UsageTracker",
                "INFO",
                "Учёт использования приложений остановлен",
            )

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.start()
        else:
            self.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()

    # --- внутренняя логика ---
    def _on_tick(self) -> None:
        now = time.monotonic()
        # Защита от гигантского скачка после сна/гибернации.
        elapsed = min(
            max(now - self._last_tick, 0.0),
            self._max_tick_jump_seconds,
        )
        self._last_tick = now

        today = date.today()
        if today != self._pending_date:
            self._flush()
            self._pending_date = today

        if self._idle_provider() <= self._idle_threshold_seconds:
            app_name = self._app_provider()
            if app_name:
                self._pending[app_name] = (
                    self._pending.get(app_name, 0.0) + elapsed
                )

        if now - self._last_flush >= self._flush_interval_seconds:
            self._flush()

    def _flush(self) -> None:
        self._last_flush = time.monotonic()
        if not self._pending:
            return

        date_str = self._pending_date.isoformat()
        written = False
        for app_name, seconds in self._pending.items():
            if seconds <= 0:
                continue
            try:
                self._database.log_app_usage(
                    self._user_id,
                    app_name,
                    seconds / 3600.0,
                    date_str,
                )
                written = True
            except Exception as error:
                logger(
                    "UsageTracker",
                    "ERROR",
                    f"Не удалось сохранить статистику для {app_name}: {error}",
                )
        self._pending.clear()
        if written:
            self.usage_flushed.emit(date_str)


_usage_tracker: UsageTracker | None = None


def get_usage_tracker() -> UsageTracker:
    """Ленивый синглтон: QTimer можно создавать только после QApplication."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
