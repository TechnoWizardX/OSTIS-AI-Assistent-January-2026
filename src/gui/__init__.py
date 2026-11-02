import os

from src.utils.icons import ICONS_DIR


def icon_path(filename):
    """Возвращает абсолютный путь к иконке"""
    return os.path.join(str(ICONS_DIR), filename)