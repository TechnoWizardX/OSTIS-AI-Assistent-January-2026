import socket

from PyQt6.QtCore import QObject, pyqtSignal


class Signals(QObject):
    voice_message_recognized = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    intent_recognized = pyqtSignal(dict)
global_signals = Signals()


class BasicUtils:
    @staticmethod
    def has_internet():
        try:
            # Пытаемся подключиться к DNS Google
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
