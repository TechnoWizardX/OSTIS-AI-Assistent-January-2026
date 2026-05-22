from src.gui.main_window import UserInterface
from PyQt6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = UserInterface()
window.show()
sys.exit(app.exec())    