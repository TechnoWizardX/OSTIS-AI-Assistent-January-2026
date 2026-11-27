"""Виджеты вкладки «Благополучие»: карточки, недельный график и список за сегодня."""

from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
)
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
        self.setObjectName("wellBeingCard")
        self.setMinimumHeight(72)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("wellBeingCardTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("wellBeingCardValue")
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("wellBeingCardHint")
        self._displayed_number: float | None = None
        self._number_formatter: Callable[[float], str] | None = None
        self._number_animation = QVariantAnimation(self)
        self._number_animation.setDuration(420)
        self._number_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._number_animation.valueChanged.connect(
            self._update_animated_number
        )

        lay.addWidget(self.title_label)
        lay.addWidget(self.value_label)
        lay.addWidget(self.hint_label)

    def set_value(self, value: str, hint: str = "") -> None:
        self._number_animation.stop()
        self._displayed_number = None
        self._number_formatter = None
        self.value_label.setText(value)
        self.value_label.setToolTip(value)
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))

    def set_animated_value(
        self,
        value: float,
        formatter: Callable[[float], str],
        hint: str = "",
    ) -> None:
        if self._number_animation.state() == QVariantAnimation.State.Running:
            animation_value = self._number_animation.currentValue()
            current_value = (
                float(animation_value)
                if animation_value is not None
                else self._displayed_number or 0.0
            )
        else:
            current_value = self._displayed_number or 0.0

        self._number_animation.stop()
        self._number_formatter = formatter
        self._number_animation.setStartValue(current_value)
        self._number_animation.setEndValue(value)
        self.value_label.setToolTip(formatter(value))
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))
        if math.isclose(current_value, value, abs_tol=0.0001):
            self._update_animated_number(value)
            return
        self._number_animation.start()

    def _update_animated_number(self, value: object) -> None:
        if value is None or self._number_formatter is None:
            return
        numeric_value = float(value)
        self._displayed_number = numeric_value
        self.value_label.setText(self._number_formatter(numeric_value))

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
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        self.avatar = QLabel(name[:1].upper())
        self.avatar.setObjectName("wellBeingAppAvatar")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFixedSize(32, 32)
        lay.addWidget(self.avatar)

        details = QVBoxLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(3)

        self.name_label = QLabel(name)
        self.name_label.setObjectName("wellBeingAppName")
        self.name_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.name_label.setToolTip(name)

        self.progress = QProgressBar()
        self.progress.setObjectName("wellBeingAppProgress")
        self.progress.setRange(0, 1000)
        target_value = max(1, int(round(ratio * 1000)))
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        self._progress_animation = QPropertyAnimation(
            self.progress, b"value", self.progress
        )
        self._progress_animation.setDuration(600)
        self._progress_animation.setStartValue(0)
        self._progress_animation.setEndValue(target_value)
        self._progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._progress_animation.start()

        self.time_label = QLabel(format_duration(hours))
        self.time_label.setObjectName("wellBeingAppTime")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._displayed_hours = hours
        self._time_animation = QVariantAnimation(self)
        self._time_animation.setDuration(360)
        self._time_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._time_animation.valueChanged.connect(self._update_animated_time)

        details.addWidget(self.name_label)
        details.addWidget(self.progress)
        lay.addLayout(details, 1)
        lay.addWidget(self.time_label)

        self.setToolTip(f"{name}: {format_duration(hours)}")

    def update_usage(self, hours: float, ratio: float) -> None:
        progress_value = max(1, int(round(ratio * 1000)))
        current_progress = self.progress.value()
        self._progress_animation.stop()
        if current_progress == progress_value:
            self.progress.setValue(progress_value)
        else:
            self._progress_animation.setStartValue(current_progress)
            self._progress_animation.setEndValue(progress_value)
            self._progress_animation.start()

        current_hours = self._displayed_hours
        if self._time_animation.state() == QVariantAnimation.State.Running:
            animated_hours = self._time_animation.currentValue()
            if animated_hours is not None:
                current_hours = float(animated_hours)
        self._time_animation.stop()
        if math.isclose(current_hours, hours, abs_tol=0.0001):
            self._displayed_hours = hours
            self.time_label.setText(format_duration(hours))
        else:
            self._time_animation.setStartValue(current_hours)
            self._time_animation.setEndValue(hours)
            self._time_animation.start()
        self.setToolTip(f"{self.name_label.text()}: {format_duration(hours)}")

    def _update_animated_time(self, value: object) -> None:
        if value is None:
            return
        self._displayed_hours = float(value)
        self.time_label.setText(format_duration(self._displayed_hours))


class AppUsageList(QWidget):
    """Список приложений выбранного периода с полосами времени."""

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_label = QLabel("Приложения за неделю")
        self.title_label.setObjectName("wellBeingListTitle")
        self.total_label = QLabel("")
        self.total_label.setObjectName("wellBeingListTotal")
        self.total_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._displayed_total: float | None = None
        self._total_animation = QVariantAnimation(self)
        self._total_animation.setDuration(360)
        self._total_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._total_animation.valueChanged.connect(self._update_animated_total)

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
        self._rows: dict[str, AppUsageRow] = {}
        self._row_order: list[str] = []
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

        self._empty = QLabel("За этот период пока нет данных")
        self._empty.setObjectName("wellBeingAppEmpty")
        self._empty.setVisible(False)
        outer.addWidget(self._empty)

    def set_items(
        self,
        items: list[tuple[str, float, float]],
        today_total: float,
    ) -> None:
        if not items:
            self._total_animation.stop()
            self._displayed_total = None
            self.total_label.clear()
            self._replace_rows([])
            self._scroll.setVisible(False)
            self._empty.setVisible(True)
            return

        self._set_animated_total(today_total)
        self._scroll.setVisible(True)
        self._empty.setVisible(False)
        desired_names = [name for name, _, _ in items]
        for name, hours, ratio in items:
            row = self._rows.get(name)
            if row is None:
                row = AppUsageRow(name, hours, ratio, self._container)
                self._rows[name] = row
            else:
                row.update_usage(hours, ratio)
        self._replace_rows(desired_names)

    def _replace_rows(self, names: list[str]) -> None:
        if names == self._row_order:
            self._container.setMinimumHeight(
                sum(self._rows[name].height() for name in names)
                + self._lay.spacing() * max(len(names) - 1, 0)
            )
            return

        self._container.setUpdatesEnabled(False)
        try:
            while self._lay.count():
                item = self._lay.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.hide()

            visible_names = set(names)
            for name in tuple(self._rows):
                if name not in visible_names:
                    self._rows.pop(name).deleteLater()

            for name in names:
                row = self._rows[name]
                self._lay.addWidget(row)
                row.show()
            if names:
                self._lay.addStretch(1)
            self._row_order = list(names)
            self._container.setMinimumHeight(
                sum(self._rows[name].height() for name in names)
                + self._lay.spacing() * max(len(names) - 1, 0)
            )
        finally:
            self._container.setUpdatesEnabled(True)
        self._container.update()

    def _set_animated_total(self, total: float) -> None:
        current_total = self._displayed_total
        if self._total_animation.state() == QVariantAnimation.State.Running:
            animated_total = self._total_animation.currentValue()
            if animated_total is not None:
                current_total = float(animated_total)
        self._total_animation.stop()
        if current_total is None:
            self._displayed_total = total
            self.total_label.setText(format_duration(total))
        elif math.isclose(current_total, total, abs_tol=0.0001):
            self._displayed_total = total
            self.total_label.setText(format_duration(total))
        else:
            self._total_animation.setStartValue(current_total)
            self._total_animation.setEndValue(total)
            self._total_animation.start()

    def _update_animated_total(self, value: object) -> None:
        if value is None:
            return
        self._displayed_total = float(value)
        self.total_label.setText(format_duration(self._displayed_total))


class _WeekChartCanvas(QWidget):
    """Рисует анимированные столбцы по дням выбранной недели."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._day_labels: list[str] = []
        self._day_totals: list[float] = []
        self._display_totals: list[float] = []
        self._animation_start_totals: list[float] = []
        self._display_heights: list[float] = []
        self._animation_start_heights: list[float] = []
        self._target_heights: list[float] = []
        self._today_index: int | None = None
        self._highlight_label = "Сегодня"
        self._target_scale = 0.0
        self.setMinimumHeight(110)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._day_font = QFont("Roboto", 9)
        self._value_font = QFont("Roboto", 8)
        self._today_font = QFont("Roboto", 8)
        self._today_font.setBold(True)
        self._data_animation = QVariantAnimation(self)
        self._data_animation.setDuration(460)
        self._data_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._data_animation.valueChanged.connect(self._animate_data)
        self._data_animation.finished.connect(self._finish_data_animation)
        self._apply_theme()

    def set_data(
        self,
        day_labels: list[str],
        day_totals: list[float],
        today_index: int | None,
        highlight_label: str = "Сегодня",
    ) -> None:
        previous_values = list(self._display_totals)
        previous_heights = list(self._display_heights)
        previous_targets = self._day_totals
        target_totals = list(day_totals)
        self._day_labels = list(day_labels)
        self._today_index = today_index
        self._highlight_label = highlight_label
        if not target_totals:
            self._data_animation.stop()
            self._day_totals = []
            self._display_totals = []
            self._animation_start_totals = []
            self._display_heights = []
            self._animation_start_heights = []
            self._target_heights = []
            self._target_scale = 0.0
            self.update()
            return

        targets_unchanged = len(previous_targets) == len(target_totals) and all(
            math.isclose(previous, target, abs_tol=0.0001)
            for previous, target in zip(previous_targets, target_totals)
        )
        if targets_unchanged:
            self._day_totals = target_totals
            self._target_scale = max(target_totals)
            self._target_heights = self._normalized_heights(
                target_totals, self._target_scale
            )
            if self._data_animation.state() != QVariantAnimation.State.Running:
                self._display_totals = list(target_totals)
                self._display_heights = list(self._target_heights)
            self.update()
            return

        self._data_animation.stop()
        self._day_totals = target_totals
        self._target_scale = max(target_totals)
        self._target_heights = self._normalized_heights(
            target_totals, self._target_scale
        )
        self._animation_start_totals = [
            previous_values[index]
            if index < len(previous_values)
            else 0.0
            for index in range(len(target_totals))
        ]
        self._animation_start_heights = [
            previous_heights[index]
            if index < len(previous_heights)
            else 0.0
            for index in range(len(target_totals))
        ]
        if all(
            math.isclose(start, end, abs_tol=0.0001)
            for start, end in zip(
                self._animation_start_totals, target_totals
            )
        ):
            self._display_totals = list(target_totals)
            self._display_heights = list(self._target_heights)
        else:
            self._display_totals = list(self._animation_start_totals)
            self._display_heights = list(self._animation_start_heights)
            self._data_animation.setStartValue(0.0)
            self._data_animation.setEndValue(1.0)
            self._data_animation.start()
        self.update()

    def _animate_data(self, progress: object) -> None:
        if progress is None:
            return
        fraction = float(progress)
        self._display_totals = [
            start + (end - start) * fraction
            for start, end in zip(
                self._animation_start_totals, self._day_totals
            )
        ]
        self._display_heights = [
            start + (end - start) * fraction
            for start, end in zip(
                self._animation_start_heights, self._target_heights
            )
        ]
        self.update()

    def _finish_data_animation(self) -> None:
        self._display_totals = list(self._day_totals)
        self._display_heights = list(self._target_heights)
        self.update()

    @classmethod
    def _normalized_heights(
        cls, totals: list[float], max_hours: float
    ) -> list[float]:
        axis_max_hours = cls._axis_max_hours(max_hours)
        return [
            total / axis_max_hours if axis_max_hours else 0.0
            for total in totals
        ]

    @staticmethod
    def _axis_max_hours(max_hours: float) -> float:
        if max_hours < 1:
            scale = 60.0
            max_value = max_hours * scale
            if max_value <= 1:
                tick_interval = 0.2
            elif max_value <= 5:
                tick_interval = 1.0
            elif max_value <= 30:
                tick_interval = 5.0
            else:
                tick_interval = 10.0
        else:
            scale = 1.0
            max_value = max_hours
            if max_hours <= 2:
                tick_interval = 0.5
            elif max_hours <= 12:
                tick_interval = 2.0
            else:
                tick_interval = 5.0
        return (
            max(tick_interval, math.ceil(max_value / tick_interval) * tick_interval)
            / scale
        )

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
        totals = self._display_totals
        if not totals:
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

        max_hours = self._target_scale
        if max_hours < 1:
            scale = 60.0
            axis_title = "минуты"
            max_value = max_hours * scale
            if max_value <= 1:
                tick_interval = 0.2
                tick_decimals = 1
            elif max_value <= 5:
                tick_interval = 1.0
                tick_decimals = 0
            elif max_value <= 30:
                tick_interval = 5.0
                tick_decimals = 0
            else:
                tick_interval = 10.0
                tick_decimals = 0
        else:
            scale = 1.0
            axis_title = "часы"
            max_value = max_hours
            if max_hours <= 2:
                tick_interval = 0.5
                tick_decimals = 1
            elif max_hours <= 12:
                tick_interval = 2.0
                tick_decimals = 0
            else:
                tick_interval = 5.0
                tick_decimals = 0

        axis_max = max(
            tick_interval,
            math.ceil(max_value / tick_interval) * tick_interval,
        )
        axis_max_hours = axis_max / scale
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
                self._format_tick(value, tick_decimals),
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
            axis_title,
        )
        painter.restore()

        slot_width = plot.width() / 7
        bar_width = min(slot_width * 0.55, 44)

        for index, total in enumerate(totals[:7]):
            x_center = plot.left() + slot_width * (index + 0.5)
            bar_height = self._display_heights[index] * plot.height()
            if bar_height > 0:
                bar_height = max(2.0, bar_height)
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
            day_label = (
                self._day_labels[index]
                if index < len(self._day_labels)
                else ""
            )
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
                day_label,
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

            if is_today and self._highlight_label:
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
                    self._highlight_label,
                )

        painter.end()

    @staticmethod
    def _format_tick(value: float, decimals: int) -> str:
        if decimals:
            return f"{value:.{decimals}f}".replace(".", ",")
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
        highlight_label: str = "Сегодня",
    ) -> None:
        self._canvas.set_data(
            day_labels, day_totals, today_index, highlight_label
        )
        if self.has_data():
            self._stack.setCurrentWidget(self._canvas)
        else:
            self._show_empty()

    def apply_theme(self) -> None:
        self._canvas.apply_theme()

    def _show_empty(self) -> None:
        self._empty_label.setText(self._empty_message)
        self._stack.setCurrentWidget(self._empty_label)
