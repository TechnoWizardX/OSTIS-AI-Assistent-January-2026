import sys

from PySide6.QtWidgets import QApplication


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("IAMOS")
    from src.core.assistant_core import run_core

    run_core()

if __name__ == "__main__":
    main()