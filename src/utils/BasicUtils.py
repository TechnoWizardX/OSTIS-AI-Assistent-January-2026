import socket

from PySide6.QtCore import QObject, Signal


class Signals(QObject):
    voice_message_recognized = Signal(str)
    error_signal = Signal(str)
    intent_recognized = Signal(dict)
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
