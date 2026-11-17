"""Выполнение блокирующих задач вне UI-потока.

Задачи выполняются по одной в отдельном daemon-потоке, поэтому порядок
постановки сохраняется (например, «закрыть приложение» и «открыть его
снова»), а интерфейс не замирает на время ``time.sleep`` или опроса psutil.
"""

import queue
import threading
import time
from typing import Callable, Optional

from src.utils.logger import logger


class BackgroundTaskRunner:
    """Последовательный исполнитель фоновых задач."""

    def __init__(
        self,
        name: str = "background-tasks",
        on_error: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        self._queue: "queue.Queue[tuple[str, Callable[[], object]]]" = queue.Queue()
        self._condition = threading.Condition()
        self._pending = 0
        self._on_error = on_error
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._thread.start()

    @property
    def pending(self) -> int:
        """Сколько задач ещё не завершено."""
        with self._condition:
            return self._pending

    def submit(self, name: str, task: Callable[[], object]) -> None:
        """Ставит задачу в очередь; вызывается из UI-потока без блокировки."""
        with self._condition:
            self._pending += 1
        self._queue.put((name, task))

    def wait_for_all(self, timeout: Optional[float] = None) -> bool:
        """Ждёт завершения задач; возвращает False при истечении ``timeout``."""
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while self._pending:
                remaining = (
                    None if deadline is None else deadline - time.monotonic()
                )
                if remaining is not None and remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def _run(self) -> None:
        while True:
            name, task = self._queue.get()
            try:
                task()
            except Exception as error:
                logger(
                    "BackgroundTasks",
                    "ERROR",
                    f"Задача {name} завершилась ошибкой: {error}",
                )
                if self._on_error is not None:
                    try:
                        self._on_error(name, error)
                    except Exception as handler_error:
                        logger(
                            "BackgroundTasks",
                            "ERROR",
                            f"Обработчик ошибки задачи {name} упал: {handler_error}",
                        )
            finally:
                with self._condition:
                    self._pending -= 1
                    self._condition.notify_all()
                self._queue.task_done()
