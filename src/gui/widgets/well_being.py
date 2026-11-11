"""Виджеты вкладки «Благополучие»: карточки, недельный график и список за сегодня."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_manager import ThemeManager
from src.modules.well_being.app_names import format_axis_hours, format_duration


class MetricCard(QFrame):
    """Карточка с заголовком, значением и пояснением."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsFrame")
        self.setMinimumHeight(68)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("wellBeingCardTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("wellBeingCardValue")
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("wellBeingCardHint")

        lay.addWidget(self.title_label)
        lay.addWidget(self.value_label)
        lay.addWidget(self.hint_label)

    def set_value(self, value: str, hint: str = "") -> None:
        self.value_label.setText(value)
        self.value_label.setToolTip(value)
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))

    def value_text(self) -> str:
        return self.value_label.text()

    def hint_text(self) -> str:
        return self.hint_label.text()


class AppUsageRow(QWidget):
    """Строка приложения: название, полоска доли, точное время."""

    def __init__(
        self,
        name: str,
        hours: float,
        ratio: float,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("wellBeingAppRow")
        self.setFixedHeight(52)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(3)

        self.name_label = QLabel(name)
        self.name_label.setObjectName("wellBeingAppName")

        self.progress = QProgressBar()
        self.progress.setObjectName("wellBeingAppProgress")
        self.progress.setRange(0, 1000)
        self.progress.setValue(max(1, int(round(ratio * 1000))))
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)

        self.time_label = QLabel(format_duration(hours))
        self.time_label.setObjectName("wellBeingAppTime")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        lay.addWidget(self.name_label)
        lay.addWidget(self.progress)
        lay.addWidget(self.time_label)

        self.setToolTip(f"{name}: {format_duration(hours)}")


class AppUsageList(QWidget):
    """Список приложений за сегодня с полосками относительно общего времени."""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_label = QLabel("Сегодня по приложениям")
        self.title_label.setObjectName("wellBeingListTitle")
        self.total_label = QLabel("")
        self.total_label.setObjectName("wellBeingListTotal")
        self.total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.total_label)
        outer.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("wellBeingAppScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setMinimumHeight(60)

        self._container = QWidget()
        self._container.setObjectName("wellBeingAppContainer")
        self._lay = QVBoxLayout(self._container)
        self._lay.setContentsMargins(0, 0, 4, 0)
        self._lay.setSpacing(2)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

        self._empty = QLabel("Сегодня пока нет данных")
        self._empty.setObjectName("wellBeingAppEmpty")
        self._empty.setVisible(False)
        outer.addWidget(self._empty)

    def set_items(
        self,
        items: list[tuple[str, float, float]],
        today_total: float,
    ) -> None:
        self._container.setMinimumHeight(0)
        while self._lay.count():
            item = self._lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

        self.total_label.setText(format_duration(today_total) if items else "")

        if not items:
            self._scroll.setVisible(False)
            self._empty.setVisible(True)
            return

        self._scroll.setVisible(True)
        self._empty.setVisible(False)
        rows = []
        for name, hours, ratio in items:
            row = AppUsageRow(name, hours, ratio)
            self._lay.addWidget(row)
            rows.append(row)
        self._lay.addStretch(1)
        self._container.setMinimumHeight(
            sum(row.height() for row in rows)
            + self._lay.spacing() * max(len(rows) - 1, 0)
        )
        self._scroll.verticalScrollBar().setValue(0)


class _WeekChartCanvas(QWidget):
    """Рисует столбцы по дням недели; сегодняшний столбец выделен."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_labels: list[str] = []
        self._day_totals: list[float] = []
        self._today_index: int | None = None
        self.setMinimumHeight(110)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._day_font = QFont("Roboto", 9)
        self._value_font = QFont("Roboto", 8)
        self._today_font = QFont("Roboto", 8)
        self._today_font.setBold(True)
        self._apply_theme()

    def set_data(
        self,
        day_labels: list[str],
        day_totals: list[float],
        today_index: int | None,
    ) -> None:
        self._day_labels = list(day_labels)
        self._day_totals = list(day_totals)
        self._today_index = today_index
        self.update()

    def apply_theme(self) -> None:
        self._apply_theme()
        self.update()

    def _apply_theme(self) -> None:
        self._text_color = QColor(str(ThemeManager.get_color("text_2")))
        self._muted_color = QColor(str(ThemeManager.get_color("text_3")))
        self._grid_color = QColor(str(ThemeManager.get_color("border_1")))
        self._line_color = QColor(str(ThemeManager.get_color("border_2")))
        self._bar_color = QColor(str(ThemeManager.get_color("accent_1")))
        self._today_color = QColor(str(ThemeManager.get_color("glow")))

    def paintEvent(self, event) -> None:
        if not self._day_totals:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        left = 46
        right = 10
        top = 8
        bottom = 62
        plot = QRectF(
            left,
            top,
            max(20, self.width() - left - right),
            max(20, self.height() - top - bottom),
        )

        max_hours = max(self._day_totals)
        if max_hours <= 2:
            tick_interval = 0.5
        elif max_hours <= 12:
            tick_interval = 2.0
        else:
            tick_interval = 5.0
        axis_max = max(
            tick_interval,
            math.ceil(max_hours / tick_interval) * tick_interval,
        )
        tick_count = int(round(axis_max / tick_interval)) + 1

        painter.setFont(self._value_font)
        for tick in range(tick_count):
            value = tick * tick_interval
            y = plot.bottom() - (value / axis_max) * plot.height()
            painter.setPen(self._grid_color)
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(self._muted_color)
            painter.drawText(
                QRectF(0, y - 8, left - 8, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._format_tick(value, tick_interval),
            )

        painter.setPen(QPen(self._line_color, 1))
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        painter.drawLine(
            QPointF(plot.left(), plot.top()), plot.bottomLeft()
        )

        painter.save()
        painter.translate(12, plot.center().y())
        painter.rotate(-90)
        painter.setPen(self._muted_color)
        painter.setFont(self._value_font)
        painter.drawText(
            QRectF(-40, -8, 80, 16),
            Qt.AlignmentFlag.AlignCenter,
            "часы",
        )
        painter.restore()

        slot_width = plot.width() / 7
        bar_width = min(slot_width * 0.55, 44)

        for index, total in enumerate(self._day_totals):
            x_center = plot.left() + slot_width * (index + 0.5)
            bar_height = (total / axis_max) * plot.height()
            if bar_height > 0:
                color = (
                    self._today_color
                    if index == self._today_index
                    else self._bar_color
                )
                rect = QRectF(
                    x_center - bar_width / 2,
                    plot.bottom() - bar_height,
                    bar_width,
                    bar_height,
                )
                path = QPainterPath()
                path.addRoundedRect(rect, 4, 4)
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPath(path)

            is_today = index == self._today_index
            painter.setFont(self._today_font if is_today else self._day_font)
            painter.setPen(self._today_color if is_today else self._text_color)
            painter.drawText(
                QRectF(
                    x_center - slot_width / 2,
                    plot.bottom() + 4,
                    slot_width,
                    14,
                ),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self._day_labels[index],
            )

            painter.setFont(self._value_font)
            painter.setPen(self._today_color if is_today else self._muted_color)
            painter.drawText(
                QRectF(
                    x_center - slot_width / 2,
                    plot.bottom() + 18,
                    slot_width,
                    14,
                ),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                format_axis_hours(total),
            )

            if is_today:
                painter.setFont(self._today_font)
                painter.setPen(self._today_color)
                painter.drawText(
                    QRectF(
                        x_center - slot_width / 2,
                        plot.bottom() + 32,
                        slot_width,
                        14,
                    ),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    "Сегодня",
                )

    @staticmethod
    def _format_tick(value: float, interval: float) -> str:
        if interval < 1:
            return f"{value:.1f}".replace(".", ",")
        return str(int(round(value)))


class WellBeingChart(QWidget):
    """Недельная диаграмма с пустым состоянием."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._empty_message = "Пока нет данных"
        self.setMinimumHeight(140)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._canvas = _WeekChartCanvas()
        self._empty_label = QLabel(self._empty_message)
        self._empty_label.setObjectName("wellBeingEmpty")
        self._empty_label.setWordWrap(True)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stack.addWidget(self._canvas)
        self._stack.addWidget(self._empty_label)
        self._show_empty()

    def sizeHint(self) -> QSize:
        return QSize(420, 200)

    def set_empty_message(self, message: str) -> None:
        self._empty_message = message
        self._empty_label.setText(message)

    def has_data(self) -> bool:
        return any(total > 0 for total in self._canvas._day_totals)

    def set_usage(
        self,
        day_labels: list[str],
        day_totals: list[float],
        today_index: int | None,
    ) -> None:
        self._canvas.set_data(day_labels, day_totals, today_index)
        if self.has_data():
            self._stack.setCurrentWidget(self._canvas)
        else:
            self._show_empty()

    def apply_theme(self) -> None:
        self._canvas.apply_theme()

    def _show_empty(self) -> None:
        self._empty_label.setText(self._empty_message)
        self._stack.setCurrentWidget(self._empty_label)
