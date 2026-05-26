import time
import requests
from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.logger import logger


class NetworkChecker(QThread):
    """Фоновый мониторинг интернет-соединения.

    Испускает ``connection_changed(bool)`` при каждой смене статуса.
    Используйте ``is_online()`` для синхронного опроса текущего состояния.
    """

    connection_changed = pyqtSignal(bool)

    _CHECK_URL = "https://1.1.1.1"

    def __init__(self, interval: int = 15, parent=None):
        super().__init__(parent)
        self._interval  = interval
        self._is_online = False
        self._running   = True

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def is_online(self) -> bool:
        """Возвращает последний известный статус подключения."""
        return self._is_online

    def stop(self):
        """Останавливает поток (безопасно вызывать из любого потока)."""
        self._running = False
        self.wait()

    # ------------------------------------------------------------------
    # Внутренняя логика
    # ------------------------------------------------------------------

    def run(self):
        while self._running:
            new_status = self._check()
            if new_status != self._is_online:
                self._is_online = new_status
                self.connection_changed.emit(new_status)
                logger("NetworkChecker", "INFO", f"Online: {new_status}")
            time.sleep(self._interval)

    @staticmethod
    def _check() -> bool:
        try:
            requests.get(NetworkChecker._CHECK_URL, timeout=5)
            return True
        except Exception:
            return False