import time
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class NetworkChecker(QThread):
    connection_changed = pyqtSignal(bool)

    def __init__(self, check_interval: int = 15):
        super().__init__()
        self.check_interval = check_interval
        self._is_online = False
        self._running = True

    def run(self):
        while self._running:
            try:
                # Лёгкий и быстрый пинг к надёжному DNS (Cloudflare)
                requests.get("https://1.1.1.1", timeout=5, headers={"User-Agent": "IAMOS/1.0"})
                new_status = True
            except Exception:
                new_status = False

            if new_status != self._is_online:
                self._is_online = new_status
                self.connection_changed.emit(self._is_online)

            time.sleep(self.check_interval)

    def is_online(self) -> bool:
        """Возвращает текущий статус (для синхронного вызова из ядра)"""
        return self._is_online

    def stop(self):
        self._running = False
        self.wait()