"""Проверки единого шаблона QSS и JSON-палитр тем.

Запуск без внешних зависимостей:
    python tests/test_themes.py
"""

import json
import os
import re
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication

from src.gui.theme_manager import (
    BASE_STYLESHEET_PATH,
    THEME_NAMES,
    THEMES_DIR,
    ThemeManager,
)


def _theme_colors(name: str) -> dict:
    path = THEMES_DIR / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"Theme palette must be a JSON object: {path}")
    return data


class ThemeManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        ThemeManager.clear_cache()

    def test_base_stylesheet_exists(self):
        self.assertTrue(BASE_STYLESHEET_PATH.is_file())
        self.assertTrue(BASE_STYLESHEET_PATH.read_text(encoding="utf-8").strip())

    def test_no_per_theme_stylesheets(self):
        self.assertEqual(list(THEMES_DIR.glob("*.qss")), [])

    def test_all_themes_load_without_placeholders(self):
        for name in THEME_NAMES:
            colors, stylesheet = ThemeManager.load_theme(name)
            self.assertIsInstance(colors, dict)
            self.assertTrue(stylesheet.strip())
            self.assertNotIn("{{", stylesheet)
            self.assertNotIn("}}", stylesheet)

    def test_all_palettes_have_same_keys(self):
        key_sets = {name: set(_theme_colors(name)) for name in THEME_NAMES}
        reference = key_sets[THEME_NAMES[0]]
        for name, keys in key_sets.items():
            self.assertEqual(keys, reference, name)

    def test_template_placeholders_exist_in_every_palette(self):
        template = BASE_STYLESHEET_PATH.read_text(encoding="utf-8")
        placeholders = set(re.findall(r"\{\{(\w+)\}\}", template))
        self.assertTrue(placeholders)

        for name in THEME_NAMES:
            colors = _theme_colors(name)
            self.assertLessEqual(placeholders, set(colors), name)
            for key in placeholders:
                self.assertNotIsInstance(
                    colors[key], (dict, list), f"{name}.{key}"
                )

    def test_unknown_theme_falls_back_to_light(self):
        colors, stylesheet = ThemeManager.load_theme("does-not-exist")
        self.assertEqual(colors, _theme_colors("light"))
        self.assertEqual(stylesheet, ThemeManager.load_theme("light")[1])

    def test_apply_all_themes(self):
        for name in THEME_NAMES:
            ThemeManager.apply_theme(name)
            self.assertEqual(ThemeManager.current_theme, name)
            self.assertTrue(QApplication.instance().styleSheet())


if __name__ == "__main__":
    unittest.main(verbosity=2)
