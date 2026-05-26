"""
Тест для проверки работы ядра (AssistentCore из core/assistant.py)
"""
import sys
import os


# Добавляем корень проекта в sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from src.utils.config import get_env_variable
from src.core.assistant import AssistentCore, run_core
from PyQt6.QtWidgets import QApplication

def run_core():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    api_key = get_env_variable("OPENROUTER_API_KEY")
    assistent = AssistentCore(api_key=api_key)
    # app.aboutToQuit.connect(assistent.intent_handler.shutdown_ollama)
    assistent.run()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_core()

