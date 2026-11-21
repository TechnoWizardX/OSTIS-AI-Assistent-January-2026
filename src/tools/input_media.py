"""Тулы ввода и медиа: вставка текста, управление плеером."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="insert_text",
    description="Вставляет текст в активное приложение, опционально после указанного слова или в указанное приложение",
    params={
        "text": "текст для вставки",
        "target_word": "слово, после которого вставить (необязательно)",
        "target_app": "приложение, куда переключиться перед вставкой (необязательно)",
    },
    keywords=["напиши", "вставь", "текст", "допиши"],
    examples=["напиши привет в блокнот"],
    # Работа с буфером обмена и паузы — вне UI-потока.
    blocking=True,
)
def insert_text(params: dict):
    ControlSystem.insert_text(
        params.get("text", ""),
        params.get("target_word"),
        params.get("target_app"),
    )


@tool(
    name="media_control",
    description="Управляет медиаплеером: play, pause, next, prev",
    params={"action": "play / pause / next / prev"},
    keywords=["музыка", "плеер", "включи", "пауза", "следующий", "прошлый", "трек"],
    examples=["включи следующий трек"],
)
def media_control(params: dict):
    ControlSystem.media_control(params.get("action", "play"))
