import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCharts import (QChart, QChartView, QBarSet, QBarSeries, 
                              QBarCategoryAxis, QValueAxis, QAbstractBarSeries)

class TimeTrackerChart(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Использование времени за день")
        self.resize(900, 600)

        # 1. Создаем наборы данных (столбцы) с кастомными цветами
        set_work = QBarSet("Работа / Учеба")
        set_work.append(8.5)
        set_work.setColor(QColor("#00adb5"))  # Бирюзовый

        set_sleep = QBarSet("Сон")
        set_sleep.append(7.0)
        set_sleep.setColor(QColor("#3f51b5"))  # Синий

        set_hobby = QBarSet("Хобби / Отдых")
        set_hobby.append(3.0)
        set_hobby.setColor(QColor("#ff5722"))  # Коралловый

        set_sport = QBarSet("Спорт")
        set_sport.append(1.5)
        set_sport.setColor(QColor("#4caf50"))  # Зеленый

        set_other = QBarSet("Рутина / Дорога")
        set_other.append(4.0)
        set_other.setColor(QColor("#795548"))  # Коричневый

        # 2. Объединяем наборы в серию
        series = QBarSeries()
        series.append(set_work)
        series.append(set_sleep)
        series.append(set_hobby)
        series.append(set_sport)
        series.append(set_other)

        # Исправлено для PySide6: Включаем метки и задаем позицию снаружи столбца
        series.setLabelsVisible(True)
        series.setLabelsPosition(QAbstractBarSeries.LabelsPosition.LabelsOutsideEnd)

        # 3. Настраиваем сам чарт
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Распределение времени за 24 часа (в часах)")
        chart.setTheme(QChart.ChartThemeDark)  # Включаем красивую темную тему
        chart.setAnimationOptions(QChart.SeriesAnimations)  # Плавная анимация

        # 4. Настройка оси X (Категории) - Исправлено для PySide6 (прямой флаг Qt)
        axis_x = QBarCategoryAxis()
        axis_x.append(["Сегодня"])  
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        # 5. Настройка оси Y (Значения) - Исправлено для PySide6 (прямой флаг Qt)
        axis_y = QValueAxis()
        axis_y.setRange(0, 10)  
        axis_y.setLabelFormat("%d ч")
        axis_y.setGridLineColor(QColor("#444444"))  
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        # Настройка легенды
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        # 6. Виджет отображения
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        self.setCentralWidget(chart_view)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TimeTrackerChart()
    window.show()
    sys.exit(app.exec())
