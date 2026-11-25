"""Тулы файлов и папок: папки пользователя, заметки, скриншоты, корзина."""
from src.tools.base import tool
from src.utils.system_control import ControlSystem


@tool(
    name="open_directory",
    description="Открывает папку пользователя: downloads, documents, desktop, pictures",
    params={"path_type": "downloads / documents / desktop / pictures"},
    keywords=["открой", "папку", "загрузки", "документы", "рабочий", "стол", "изображения"],
    examples=["открой папку загрузок"],
)
def open_directory(params: dict):
    ControlSystem.open_directory(params.get("path_type", "desktop"))


@tool(
    name="create_quick_note",
    description="Создаёт текстовый файл-заметку на рабочем столе",
    params={"content": "текст заметки", "filename": "имя файла, по умолчанию note.txt"},
    keywords=["заметка", "запиши", "создай", "файл", "напоминание"],
    examples=["запиши заметку купить хлеб"],
)
def create_quick_note(params: dict):
    ControlSystem.create_quick_note(
        params.get("content", ""),
        params.get("filename", "note.txt"),
    )

@tool(
    name="delete_quick_note",
    description="Удаляет текстовый файл-заметку с рабочего стола",
    params={"filename": "имя файла, по умолчанию note.txt"},
    keywords=["удали", "заметка", "заметку", "файл", "очисти", "убери"],
    examples=["удали заметку", "удали файл note.txt с рабочего стола"],
)
def delete_quick_note(params: dict):
    ControlSystem.delete_quick_note(
        params.get("filename", "note.txt"),
    )


@tool(
    name="take_screenshot",
    description="Делает скриншот экрана и сохраняет в папку снимков",
    params={"name": "имя файла; по умолчанию генерируется автоматически"},
    keywords=["скриншот", "скрин", "снимок", "экрана"],
    examples=["сделай скриншот"],
)
def take_screenshot(params: dict):
    ControlSystem.take_screenshot(params.get("name"))


@tool(
    name="empty_recycle_bin",
    description="Очищает корзину",
    keywords=["очисти", "корзина", "мусор"],
    examples=["очисти корзину"],
)
def empty_recycle_bin(params: dict):
    ControlSystem.empty_recycle_bin()
