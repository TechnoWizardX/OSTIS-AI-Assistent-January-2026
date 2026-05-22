import os
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources/icons")
def icon_path(filename):
    """Возвращает абсолютный путь к иконке"""
    return os.path.join(ICONS_DIR, filename)