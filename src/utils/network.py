"""src/utils/network.py

Утилиты для проверки сетевого подключения.

Проверка — TCP-соединение с хостом (десятки миллисекунд) вместо полного
HTTP-запроса; результат кэшируется на несколько секунд, поэтому функцию
можно вызывать из UI-потока.

Для фонового мониторинга с сигналами Qt используйте
src.core.network_monitor.NetworkChecker.
"""

import socket
import threading
import time
from urllib.parse import urlsplit

_DEFAULT_URL = "https://1.1.1.1"
_DEFAULT_TIMEOUT = 1.0
_CACHE_TTL = 5.0

_cache_lock = threading.Lock()
_cache: dict[tuple[str, int], tuple[float, bool]] = {}


def _endpoint(url: str) -> tuple[str, int]:
    """Возвращает (host, port), которые нужно проверить для ``url``."""
    parsed = urlsplit(url if "//" in url else f"//{url}")
    host = parsed.hostname or "1.1.1.1"
    port = parsed.port or (80 if parsed.scheme == "http" else 443)
    return host, port


def _probe(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def has_internet(url: str = _DEFAULT_URL, timeout: float = _DEFAULT_TIMEOUT) -> bool:
    """Возвращает True, если есть доступ в интернет.

    Проверяет TCP-соединение с хостом из ``url`` (~30 мс вместо ~1 с у
    ``requests.get``). Результат кэшируется на ``_CACHE_TTL`` секунд, так что
    повторные вызовы (например, при каждой отправке сообщения) не блокируют
    интерфейс.
    """
    key = _endpoint(url)
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None and now - cached[0] < _CACHE_TTL:
            return cached[1]

    online = _probe(key[0], key[1], timeout)

    with _cache_lock:
        _cache[key] = (now, online)
    return online


def clear_cache() -> None:
    """Сбрасывает кэш статуса (для тестов и ручной перепроверки сети)."""
    with _cache_lock:
        _cache.clear()
