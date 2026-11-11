import json
import logging
import re
from pathlib import Path

from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

THEMES_DIR = Path(__file__).resolve().parents[1] / "resources" / "themes"
STYLES_DIR = Path(__file__).resolve().parents[1] / "resources" / "styles"
BASE_STYLESHEET_PATH = STYLES_DIR / "base.qss"
THEME_NAMES = ("light", "dark", "twilight", "vs_code", "nord", "gruvbox")


class ThemeManager:
    current_theme = "light"
    colors: dict[str, str | int] = {}
    _base_stylesheet: str | None = None
    _compiled_stylesheets: dict[str, str] = {}

    @classmethod
    def _load_base_stylesheet(cls) -> str:
        if cls._base_stylesheet is None:
            cls._base_stylesheet = BASE_STYLESHEET_PATH.read_text(encoding="utf-8")
        return cls._base_stylesheet

    @classmethod
    def clear_cache(cls) -> None:
        """Сбрасывает кэш шаблона и собранных стилей (например, в тестах)."""
        cls._base_stylesheet = None
        cls._compiled_stylesheets.clear()

    @classmethod
    def load_theme(cls, name: str) -> tuple[dict[str, str | int], str]:
        if name not in THEME_NAMES:
            logger.warning("Unknown theme %r; using light", name)
            name = "light"

        colors_path = THEMES_DIR / f"{name}.json"
        colors = json.loads(colors_path.read_text(encoding="utf-8"))
        if not isinstance(colors, dict):
            raise ValueError(f"Theme colors must be a JSON object: {colors_path}")

        if name in cls._compiled_stylesheets:
            return colors, cls._compiled_stylesheets[name]

        stylesheet = cls._load_base_stylesheet()

        def replace_color(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in colors:
                raise KeyError(
                    f"Unknown theme color {key!r} in {BASE_STYLESHEET_PATH}"
                )
            return str(colors[key])

        compiled_stylesheet = re.sub(
            r"\{\{(\w+)\}\}", replace_color, stylesheet
        )
        unresolved = re.findall(r"\{\{(\w+)\}\}", compiled_stylesheet)
        if unresolved:
            raise KeyError(
                f"Unresolved theme colors {unresolved!r} in "
                f"{BASE_STYLESHEET_PATH}"
            )

        cls._compiled_stylesheets[name] = compiled_stylesheet
        return colors, compiled_stylesheet

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
