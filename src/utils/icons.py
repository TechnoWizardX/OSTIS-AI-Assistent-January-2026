import importlib
from pathlib import Path

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QAbstractButton, QApplication, QLabel

ICONS_DIR = Path(__file__).resolve().parents[1] / "resources" / "icons"


class ThemeIcons:
    _color = QColor("#000000")
    _cache: dict[str, QIcon] = {}

    @classmethod
    def set_theme_color(cls, color: str) -> None:
        new_color = QColor(color)
        if not new_color.isValid():
            raise ValueError(f"Invalid theme icon color: {color!r}")
        if new_color != cls._color:
            cls._color = new_color
            cls._cache.clear()
        cls.refresh()

    @classmethod
    def _source_icon(cls, filename: str) -> QIcon:
        try:
            resources = importlib.import_module("src.resources.resources")
        except ModuleNotFoundError as error:
            if error.name != "src.resources.resources":
                raise
            resources = None

        resource_icon = QIcon(f":/icons/{filename}")
        if not resource_icon.isNull():
            return resource_icon

        icon_paths = getattr(resources, "ICON_PATHS", {}) if resources else {}
        path = Path(icon_paths.get(filename, ICONS_DIR / filename))
        if not path.is_file():
            raise FileNotFoundError(f"Icon not found: {path}")
        return QIcon(str(path))

    @classmethod
    def _recolor(cls, pixmap: QPixmap) -> QPixmap:
        result = pixmap.copy()
        painter = QPainter(result)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(result.rect(), cls._color)
        painter.end()
        return result

    @classmethod
    def icon(cls, filename: str) -> QIcon:
        if filename not in cls._cache:
            source = cls._source_icon(filename).pixmap(QSize(64, 64))
            if source.isNull():
                raise ValueError(f"Unable to load icon: {filename}")
            cls._cache[filename] = QIcon(cls._recolor(source))
        return cls._cache[filename]

    @classmethod
    def pixmap(cls, filename: str, size: QSize) -> QPixmap:
        source = cls._source_icon(filename).pixmap(size)
        if source.isNull():
            raise ValueError(f"Unable to load icon: {filename}")
        return cls._recolor(source)

    @classmethod
    def refresh(cls) -> None:
        app = QApplication.instance()
        if app is None:
            return
        for widget in app.allWidgets():
            filename = widget.property("themeIcon")
            if filename and isinstance(widget, QAbstractButton):
                widget.setIcon(cls.icon(str(filename)))
            filename = widget.property("themePixmap")
            if filename and isinstance(widget, QLabel):
                widget.setPixmap(cls.pixmap(str(filename), widget.size()))


def set_theme_icon(widget: QAbstractButton, filename: str) -> None:
    widget.setProperty("themeIcon", filename)
    widget.setIcon(ThemeIcons.icon(filename))


def set_theme_pixmap(widget: QLabel, filename: str) -> None:
    widget.setProperty("themePixmap", filename)
    widget.setPixmap(ThemeIcons.pixmap(filename, widget.size()))
