"""Базовые примитивы тулов: метаданные и декоратор регистрации."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolSpec:
    """Метаданные тула. Текстовые поля — по-русски: идут в промпт и в поиск."""

    name: str
    description: str
    # Пары (имя_параметра, описание) — кортеж вместо dict ради порядка.
    params: tuple[tuple[str, str], ...] = ()
    # Слова запроса пользователя, по которым ретривер находит тул.
    keywords: tuple[str, ...] = ()
    # Примеры фраз пользователя — подсказка для семантического поиска.
    examples: tuple[str, ...] = ()
    # Блокирует поток на секунды — выполнять вне UI-потока (BackgroundTaskRunner).
    blocking: bool = False
    # Всегда подставляется в промпт независимо от релевантности.
    core: bool = False
    func: Callable[[dict], None] | None = None


# Реестр живёт в base, а не в registry, чтобы не зациклить импорты:
# модули тулов импортируют только base.
_REGISTERED: dict[str, ToolSpec] = {}


def tool(
    name: str,
    description: str,
    params: dict[str, str] | None = None,
    keywords: list[str] | None = None,
    examples: list[str] | None = None,
    blocking: bool = False,
    core: bool = False,
) -> Callable:
    """Помечает функцию как тул и регистрирует её.

    Функция принимает params от модели; значения по умолчанию задаются
    внутри (раньше они были лямбдами в actions_mapping).
    """

    def decorator(func: Callable[[dict], None]) -> Callable[[dict], None]:
        if name in _REGISTERED:
            raise ValueError(f"Тул с именем {name!r} уже зарегистрирован")
        _REGISTERED[name] = ToolSpec(
            name=name,
            description=description,
            params=tuple((key, value) for key, value in (params or {}).items()),
            keywords=tuple(keywords or ()),
            examples=tuple(examples or ()),
            blocking=blocking,
            core=core,
            func=func,
        )
        return func

    return decorator
