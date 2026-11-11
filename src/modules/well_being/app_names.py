"""Человекочитаемые имена приложений и форматирование длительности."""

from __future__ import annotations

import re

APP_DISPLAY_NAMES: dict[str, str] = {
    # Браузеры
    "chrome": "Google Chrome",
    "msedge": "Microsoft Edge",
    "firefox": "Firefox",
    "opera": "Opera",
    "brave": "Brave",
    "yandex": "Яндекс Браузер",
    # Разработка
    "code": "Visual Studio Code",
    "pycharm64": "PyCharm",
    "idea64": "IntelliJ IDEA",
    "webstorm64": "WebStorm",
    "sublime_text": "Sublime Text",
    "notepad++": "Notepad++",
    # Система
    "explorer": "Проводник",
    "notepad": "Блокнот",
    "calc": "Калькулятор",
    "mspaint": "Paint",
    "snippingtool": "Ножницы",
    "taskmgr": "Диспетчер задач",
    "control": "Панель управления",
    # Общение
    "telegram": "Telegram",
    "discord": "Discord",
    "whatsapp": "WhatsApp",
    "zoom": "Zoom",
    "teams": "Microsoft Teams",
    "ms-teams": "Microsoft Teams",
    "skype": "Skype",
    # Офис
    "word": "Microsoft Word",
    "winword": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpnt": "PowerPoint",
    "outlook": "Microsoft Outlook",
    "onenote": "OneNote",
    # Медиа и прочее
    "steam": "Steam",
    "steamwebhelper": "Steam",
    "spotify": "Spotify",
    "vlc": "VLC",
    "obs64": "OBS Studio",
    "photoshop": "Adobe Photoshop",
    "illustrator": "Adobe Illustrator",
    "figma": "Figma",
    "iamos": "IAMOS",
}


def display_name(app_name: str) -> str:
    """Преобразует имя процесса (`chrome`, `code.exe`) в подпись для интерфейса."""
    key = app_name.strip().lower()
    if key.endswith(".exe"):
        key = key[:-4]
    if key in APP_DISPLAY_NAMES:
        return APP_DISPLAY_NAMES[key]

    readable = re.sub(r"[_-]+", " ", key).strip()
    if not readable:
        return "Неизвестное приложение"
    return " ".join(word.capitalize() for word in readable.split())


def format_duration(hours: float) -> str:
    """Форматирует часы в строку вида «2 ч 15 мин»."""
    total_minutes = int(round(max(hours, 0.0) * 60))
    if total_minutes <= 0:
        return "0 мин"
    whole_hours, minutes = divmod(total_minutes, 60)
    if whole_hours and minutes:
        return f"{whole_hours} ч {minutes} мин"
    if whole_hours:
        return f"{whole_hours} ч"
    return f"{minutes} мин"
