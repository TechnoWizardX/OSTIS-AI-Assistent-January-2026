import sys
import warnings

from PySide6.QtWidgets import QApplication

# Шум библиотек (torch/silero: invalid escape sequence и т.п.)
warnings.filterwarnings("ignore", category=SyntaxWarning)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("IAMOS")
    from src.core.assistant_core import run_core

    run_core()

if __name__ == "__main__":
    main()