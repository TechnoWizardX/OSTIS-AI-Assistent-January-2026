"""Тулы приложений: запуск, закрытие, перезагрузка."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="open_application",
    description="Открывает приложение по названию",
    params={"app_name": "название приложения, например chrome или notepad"},
    keywords=["открой", "запусти", "приложение", "программу", "включи"],
    examples=["открой калькулятор", "запусти браузер"],
    core=True,
)
def open_application(params: dict):
    ControlSystem.open_application(params.get("app_name", ""))


@tool(
    name="close_application",
    description="Закрывает приложение по названию",
    params={"app_name": "название приложения"},
    keywords=["закрой", "закрыть", "приложение", "программу"],
    examples=["закрой браузер"],
)
def close_application(params: dict):
    ControlSystem.close_application(params.get("app_name", ""))


@tool(
    name="reload_application",
    description="Перезагружает приложение: закрывает и запускает заново",
    params={"app_name": "название приложения"},
    keywords=["перезапусти", "перезагрузи", "переоткрой", "приложение"],
    examples=["перезапусти проводник"],
    # Внутри time.sleep(2) — выполняется вне UI-потока.
    blocking=True,
)
def reload_application(params: dict):
    ControlSystem.reload_application(params.get("app_name", ""))
