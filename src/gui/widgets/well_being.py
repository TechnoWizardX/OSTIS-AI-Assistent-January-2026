"""Виджеты вкладки «Благополучие»: карточки, график и легенда."""

from __future__ import annotations

import math

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QStackedBarSeries,
    QValueAxis,
)
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from src.gui.theme_manager import ThemeManager
from src.modules.well_being.app_names import format_axis_hours, format_duration

APP_COLOR_PALETTE = (
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
)


def app_color(index: int) -> QColor:
    """Стабильный цвет приложения по его позиции в списке."""
    if index < len(APP_COLOR_PALETTE):
        return QColor(APP_COLOR_PALETTE[index])
    hue = int((index * 137.508) % 360)
    return QColor.fromHsv(hue, 190, 210)


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


class LegendChip(QFrame):
    """Компактный цветной чип приложения для нижней легенды."""

    def __init__(self, name: str, hours: float, color: QColor, parent=None):
        super().__init__(parent)
        self.setObjectName("wellBeingLegendChip")
        self.setFixedHeight(28)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 10, 2)
        lay.setSpacing(6)

        self.color_dot = QLabel()
        self.color_dot.setFixedSize(10, 10)
        self.color_dot.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 5px;"
        )

        self.name_label = QLabel(name)
        self.name_label.setObjectName("wellBeingLegendName")
        self.time_label = QLabel(format_duration(hours))
        self.time_label.setObjectName("wellBeingLegendTime")

        lay.addWidget(self.color_dot)
        lay.addWidget(self.name_label)
        lay.addWidget(self.time_label)

        self.setToolTip(f"{name}: {format_duration(hours)}")


class WellBeingLegend(QWidget):
    """Горизонтальная прокручиваемая полоска со всеми приложениями."""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("wellBeingLegendScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setFixedHeight(44)

        self._container = QWidget()
        self._container.setObjectName("wellBeingLegendContainer")
        self._container.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._container.setFixedHeight(28)
        self._lay = QHBoxLayout(self._container)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(8)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self._empty = QLabel("Нет данных за текущую неделю")
        self._empty.setObjectName("wellBeingLegendEmpty")
        self._empty.setVisible(False)
        outer.addWidget(self._empty)

    def set_items(self, items: list[tuple[str, float, QColor]]) -> None:
        self._container.setMinimumWidth(0)
        while self._lay.count():
            item = self._lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not items:
            self._scroll.setVisible(False)
            self._empty.setVisible(True)
            return

        self._scroll.setVisible(True)
        self._empty.setVisible(False)
        chips = []
        for name, hours, color in items:
            chip = LegendChip(name, hours, color)
            self._lay.addWidget(chip)
            chips.append(chip)
        self._lay.addStretch(1)
        self._container.setMinimumWidth(
            sum(chip.sizeHint().width() for chip in chips)
            + self._lay.spacing() * max(len(chips) - 1, 0)
        )
        self._scroll.horizontalScrollBar().setValue(0)


class WellBeingChart(QWidget):
    """Стопка часов по дням текущей недели с пустым состоянием."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_labels: list[str] = []
        self._day_totals: list[float] = []
        self._series_data: list[tuple[str, list[float], QColor]] = []
        self._empty_message = "Пока нет данных"

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(False)
        self._chart.setMargins(QMargins(2, 2, 2, 2))
        self._chart.legend().setVisible(False)
        self._chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)

        self._view = QChartView(self._chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setBackgroundBrush(QBrush(Qt.GlobalColor.transparent))
        self._view.setFrameShape(QFrame.Shape.NoFrame)
        self._view.setStyleSheet("background: transparent; border: none;")
        self._view.setContentsMargins(0, 0, 0, 0)

        self._empty_label = QLabel(self._empty_message)
        self._empty_label.setObjectName("wellBeingEmpty")
        self._empty_label.setWordWrap(True)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stack.addWidget(self._view)
        self._stack.addWidget(self._empty_label)

        self._apply_theme()
        self._show_empty()

    def set_empty_message(self, message: str) -> None:
        self._empty_message = message
        self._empty_label.setText(message)

    def has_data(self) -> bool:
        return any(total > 0 for total in self._day_totals)

    def set_usage(
        self,
        day_labels: list[str],
        day_totals: list[float],
        series_data: list[tuple[str, list[float], QColor]],
    ) -> None:
        self._day_labels = list(day_labels)
        self._day_totals = list(day_totals)
        self._series_data = [
            (name, list(values), color) for name, values, color in series_data
        ]
        if not self.has_data():
            self._show_empty()
            return
        self._render()
        self._stack.setCurrentWidget(self._view)

    def apply_theme(self) -> None:
        self._apply_theme()
        if self.has_data():
            self._render()

    # --- внутреннее ---
    def _show_empty(self) -> None:
        self._empty_label.setText(self._empty_message)
        self._stack.setCurrentWidget(self._empty_label)

    def _apply_theme(self) -> None:
        self._text_color = QColor(str(ThemeManager.get_color("text_2")))
        self._grid_color = QColor(str(ThemeManager.get_color("border_1")))
        self._line_color = QColor(str(ThemeManager.get_color("border_2")))
        self._axis_font = QFont("Roboto", 9)

    def _render(self) -> None:
        chart = self._chart
        for axis in chart.axes():
            chart.removeAxis(axis)
        chart.removeAllSeries()

        series = QStackedBarSeries()
        series.setBarWidth(0.72)
        series.setLabelsVisible(False)

        for name, values, color in self._series_data:
            bar_set = QBarSet(name)
            bar_set.append(values)
            bar_set.setColor(color)
            bar_set.setBorderColor(color)
            series.append(bar_set)

        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(
            [
                f"{label}\u00a0{format_axis_hours(total)}"
                for label, total in zip(self._day_labels, self._day_totals)
            ]
        )
        axis_x.setTruncateLabels(False)
        axis_x.setLabelsColor(self._text_color)
        axis_x.setLabelsFont(self._axis_font)
        axis_x.setGridLineVisible(False)
        axis_x.setLinePenColor(self._line_color)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        max_hours = max(self._day_totals) if self._day_totals else 1.0
        if max_hours <= 2:
            tick_interval = 0.5
            label_format = "%.1f"
        elif max_hours <= 12:
            tick_interval = 2.0
            label_format = "%.0f"
        else:
            tick_interval = 5.0
            label_format = "%.0f"
        axis_max = max(
            tick_interval,
            math.ceil(max_hours / tick_interval) * tick_interval,
        )

        axis_y = QValueAxis()
        axis_y.setRange(0, axis_max)
        axis_y.setTickInterval(tick_interval)
        axis_y.setTickCount(int(round(axis_max / tick_interval)) + 1)
        axis_y.setLabelFormat(label_format)
        axis_y.setLabelsColor(self._text_color)
        axis_y.setLabelsFont(self._axis_font)
        axis_y.setTitleText("часы")
        axis_y.setTitleBrush(self._text_color)
        axis_y.setTitleFont(QFont("Roboto", 8))
        axis_y.setGridLineColor(self._grid_color)
        axis_y.setLinePenColor(self._line_color)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
