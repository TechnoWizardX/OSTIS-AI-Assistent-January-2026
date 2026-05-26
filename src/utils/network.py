"""src/utils/network.py

Утилиты для проверки сетевого подключения.
Не содержит состояния — только чистые функции.

Для фонового мониторинга с сигналами Qt используйте
src.core.network_monitor.NetworkChecker.
"""

import requests


def has_internet(url: str = "https://1.1.1.1", timeout: int = 5) -> bool:
    """Возвращает True, если есть доступ в интернет."""
    try:
        requests.get(url, timeout=timeout)
        return True
    except Exception:
        return False