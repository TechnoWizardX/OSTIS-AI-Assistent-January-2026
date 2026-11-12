import threading

from PySide6.QtCore import QThread, Signal

from src.utils.logger import logger
from src.utils.network import has_internet


class NetworkChecker(QThread):
    """Фоновый мониторинг интернет-соединения.

    Испускает ``connection_changed(bool)`` при каждой смене статуса.
    Используйте ``is_online()`` для синхронного опроса текущего состояния.
    """

    connection_changed = Signal(bool)

    def __init__(self, interval: int = 15, parent=None):
        super().__init__(parent)
        self._interval  = interval
        self._is_online = False
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def is_online(self) -> bool:
        """Возвращает последний известный статус подключения."""
        return self._is_online

    def stop(self):
        """Останавливает поток (безопасно вызывать из любого потока)."""
        self._stop_event.set()
        if self.isRunning() and QThread.currentThread() != self:
            self.wait()

    # ------------------------------------------------------------------
    # Внутренняя логика
    # ------------------------------------------------------------------

    def run(self):
        while not self._stop_event.is_set():
            new_status = self._check()
            if new_status != self._is_online:
                self._is_online = new_status
                self.connection_changed.emit(new_status)
                logger("NetworkChecker", "INFO", f"Online: {new_status}")
            if self._stop_event.wait(self._interval):
                break

    @staticmethod
    def _check() -> bool:
        return has_internet()