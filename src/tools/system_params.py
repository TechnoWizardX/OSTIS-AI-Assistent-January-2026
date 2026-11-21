"""Тулы системных параметров: яркость и громкость."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="set_brightness",
    description="Устанавливает яркость экрана в процентах",
    params={"level": "яркость в процентах от 0 до 100"},
    keywords=["яркость", "ярче", "темнее", "экран", "тусклее"],
    examples=["сделай экран ярче", "убавь яркость"],
)
def set_brightness(params: dict):
    ControlSystem.set_brightness(params.get("level", 50))


@tool(
    name="set_volume",
    description="Устанавливает громкость звука в процентах",
    params={"level": "громкость в процентах от 0 до 100"},
    keywords=["громкость", "громче", "тише", "звук"],
    examples=["сделай громче", "поставь громкость на 30"],
    core=True,
)
def set_volume(params: dict):
    ControlSystem.set_volume(params.get("level", 50))
