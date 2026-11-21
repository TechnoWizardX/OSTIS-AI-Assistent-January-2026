"""Тулы системной информации."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="get_system_stats",
    description="Возвращает нагрузку на систему: процент загрузки ЦП и ОЗУ",
    keywords=["нагрузка", "загрузка", "процессор", "память", "озу", "статус", "системы"],
    examples=["какая загрузка процессора"],
    # psutil.cpu_percent(interval=1) блокирует поток на секунду — вне UI-потока.
    blocking=True,
    core=True,
)
def get_system_stats(params: dict):
    ControlSystem.get_system_stats()
