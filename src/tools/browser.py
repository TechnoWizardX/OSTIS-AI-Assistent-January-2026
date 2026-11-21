"""Тулы браузера: открытие сайтов и вкладок."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="open_site",
    description="Открывает сайт по адресу в браузере по умолчанию",
    params={"url": "адрес сайта, например youtube.com"},
    keywords=["открой", "сайт", "браузер", "ссылка", "зайди", "страница", "интернет"],
    examples=["открой youtube.com", "зайди на сайт погоды"],
    core=True,
)
def open_site(params: dict):
    ControlSystem.open_site(params.get("url", ""))


@tool(
    name="close_current_tab",
    description="Закрывает текущую вкладку браузера",
    keywords=["закрой", "вкладка", "браузер", "таб"],
    examples=["закрой вкладку"],
)
def close_current_tab(params: dict):
    ControlSystem.close_current_tab()
