import json
import logging
import re
from pathlib import Path

from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

THEMES_DIR = Path(__file__).resolve().parents[1] / "resources" / "themes"
THEME_NAMES = ("light", "dark", "twilight", "vs_code", "nord", "gruvbox")


class ThemeManager:
    current_theme = "light"
    colors: dict[str, str | int] = {}

    @classmethod
    def load_theme(cls, name: str) -> tuple[dict[str, str | int], str]:
        if name not in THEME_NAMES:
            logger.warning("Unknown theme %r; using light", name)
            name = "light"

        colors_path = THEMES_DIR / f"{name}.json"
        stylesheet_path = THEMES_DIR / f"{name}.qss"
        colors = json.loads(colors_path.read_text(encoding="utf-8"))
        stylesheet = stylesheet_path.read_text(encoding="utf-8")
        if not isinstance(colors, dict):
            raise ValueError(f"Theme colors must be a JSON object: {colors_path}")

        def replace_color(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in colors:
                raise KeyError(f"Unknown theme color {key!r} in {stylesheet_path}")
            return str(colors[key])

        return colors, re.sub(r"\{\{(\w+)\}\}", replace_color, stylesheet)

    @classmethod
    def apply_theme(cls, name: str) -> None:
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("Cannot apply a theme before QApplication is created")

        colors, stylesheet = cls.load_theme(name)
        if name not in THEME_NAMES:
            name = "light"

        cls.current_theme = name
        cls.colors = colors
        app.setStyleSheet(stylesheet)

        from src.utils.icons import ThemeIcons

        ThemeIcons.set_theme_color(str(colors["text_1"]))

    @classmethod
    def get_color(cls, name: str) -> str | int:
        if not cls.colors:
            colors, _ = cls.load_theme(cls.current_theme)
            cls.colors = colors
        return cls.colors[name]
