"""Тулы питания: сон, выключение, перезагрузка."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="os_sleep",
    description="Переводит компьютер в спящий режим",
    keywords=["спящий", "режим", "усни", "сон", "спать"],
    examples=["переведи компьютер в спящий режим"],
)
def os_sleep(params: dict):
    ControlSystem.os_sleep()


@tool(
    name="os_shutdown",
    description="Выключает компьютер через указанную задержку в секундах",
    params={"delay": "секунды до выключения, по умолчанию 60"},
    keywords=["выключи", "выключение", "компьютер", "пк", "заверши", "работу"],
    examples=["выключи компьютер через 5 минут"],
)
def os_shutdown(params: dict):
    ControlSystem.os_shutdown(params.get("delay", 60))


@tool(
    name="cancel_shutdown",
    description="Отменяет запланированное выключение или перезагрузку",
    keywords=["отмени", "выключение", "перезагрузку"],
    examples=["отмени выключение"],
)
def cancel_shutdown(params: dict):
    ControlSystem.cancel_shutdown()


@tool(
    name="os_restart",
    description="Перезагружает компьютер через указанную задержку в секундах",
    params={"delay": "секунды до перезагрузки, по умолчанию 0"},
    keywords=["перезагрузи", "ребутни", "перезапусти", "компьютер", "пк"],
    examples=["перезагрузи компьютер"],
)
def os_restart(params: dict):
    ControlSystem.os_restart(params.get("delay", 0))
