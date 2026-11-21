"""Тулы управления окнами: состояние, прозрачность, привязка к краям."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="minimize_all_windows",
    description="Сворачивает все окна и показывает рабочий стол",
    keywords=["сверни", "свернуть", "окна", "рабочий стол"],
    examples=["сверни все окна"],
)
def minimize_all_windows(params: dict):
    ControlSystem.minimize_all_windows()


@tool(
    name="toggle_always_on_top",
    description="Переключает режим «поверх всех окон» для активного окна",
    keywords=["поверх", "окон", "всегда сверху", "закрепи окно"],
    examples=["сделай окно поверх всех"],
)
def toggle_always_on_top(params: dict):
    ControlSystem.toggle_always_on_top()


@tool(
    name="set_window_state",
    description="Меняет состояние активного окна: maximize, minimize, restore, close",
    params={"action": "maximize / minimize / restore / close"},
    keywords=["разверни", "сверни", "восстанови", "закрой окно", "на весь экран"],
    examples=["разверни окно на весь экран"],
)
def set_window_state(params: dict):
    ControlSystem.set_window_state(params.get("action", "restore"))


@tool(
    name="set_window_transparency",
    description="Устанавливает прозрачность активного окна (0 — невидимое, 255 — обычное)",
    params={"alpha": "уровень прозрачности от 0 до 255"},
    keywords=["прозрачность", "прозрачное", "окно", "непрозрачное"],
    examples=["сделай окно полупрозрачным"],
)
def set_window_transparency(params: dict):
    ControlSystem.set_window_transparency(params.get("alpha", 255))


@tool(
    name="snap_window",
    description="Прижимает активное окно к левой или правой половине экрана",
    params={"side": "left / right"},
    keywords=["прижми", "окно", "половина", "экрана", "слева", "справа", "размести"],
    examples=["прижми окно вправо"],
)
def snap_window(params: dict):
    ControlSystem.snap_window(params.get("side", "left"))
