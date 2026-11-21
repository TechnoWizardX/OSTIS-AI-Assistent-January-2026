"""Реестр тулов: ленивая авто-дискавери модулей src/tools и поиск по имени.

Тяжёлые импорты (AppOpener, pyautogui, win32) откладываются до первого интента.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import pkgutil

from src.tools.base import ToolSpec, _REGISTERED
from src.utils.logger import logger

# Инфраструктурные модули без тулов.
_NON_TOOL_MODULES = frozenset({"base", "registry", "retriever", "embeddings"})

_discovered = False


def discover_tools() -> None:
    """Импортирует модули тулов один раз; декоратор @tool заполняет реестр."""
    global _discovered
    if _discovered:
        return

    package = importlib.import_module("src.tools")
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name in _NON_TOOL_MODULES:
            continue
        importlib.import_module(f"src.tools.{module_info.name}")

    _discovered = True
    logger("ToolRegistry", "INFO", f"Зарегистрировано тулов: {len(_REGISTERED)}")


def get_all_tools() -> list[ToolSpec]:
    """Все зарегистрированные тулы (модули импортируются при первом вызове)."""
    discover_tools()
    return list(_REGISTERED.values())


def get_tool(name: str) -> ToolSpec | None:
    """Ищет тул по имени; неизвестное имя — не ошибка, вернём None."""
    discover_tools()
    return _REGISTERED.get(name)


def get_core_tools() -> list[ToolSpec]:
    """Универсальные тулы, которые всегда подставляются в промпт."""
    return [spec for spec in get_all_tools() if spec.core]


def catalog_signature() -> str:
    """Хеш каталога тулов — по нему инвалидируется кеш эмбеддингов."""
    payload = [
        {
            "name": spec.name,
            "description": spec.description,
            "params": [list(pair) for pair in spec.params],
            "keywords": list(spec.keywords),
            "examples": list(spec.examples),
        }
        for spec in sorted(get_all_tools(), key=lambda item: item.name)
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
