"""Тулы сети: Wi-Fi и режим полёта."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="disconnect_wifi",
    description="Разрывает соединение с текущей Wi-Fi сетью",
    keywords=["отключи", "вифай", "wifi", "wi-fi", "сеть", "интернет"],
    examples=["отключи wi-fi"],
)
def disconnect_wifi(params: dict):
    ControlSystem.disconnect_wifi()


@tool(
    name="connect_wifi",
    description="Подключается к сохранённой Wi-Fi сети по имени (SSID)",
    params={"ssid_name": "имя сети; если не указано — берётся сохранённое"},
    keywords=["подключи", "вифай", "wifi", "wi-fi", "сеть", "интернет"],
    examples=["подключись к wi-fi"],
)
def connect_wifi(params: dict):
    ControlSystem.connect_wifi(params.get("ssid_name"))


@tool(
    name="set_airplane_mode",
    description="Включает или выключает режим «в самолёте»",
    params={"state": "true — включить, false — выключить"},
    keywords=["самолет", "режим", "полета", "авиарежим"],
    examples=["включи режим полёта"],
)
def set_airplane_mode(params: dict):
    ControlSystem.set_airplane_mode(params.get("state", False))
