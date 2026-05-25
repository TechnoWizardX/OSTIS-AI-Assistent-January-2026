import cv2
import pyaudio
import json
from datetime import datetime
from pathlib import Path
import sqlite3
import re 
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtMultimedia import QMediaDevices
import socket
import os
from dotenv import load_dotenv
class Signals(QObject):
    voice_message_recognized = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    intent_recognized = pyqtSignal(dict)
global_signals = Signals()



SETTINGS_CONFIG_FILE = Path(__file__).parent / "data" / "settings_config.json"
SETTINGS_CONFIG_FILE.parent.mkdir(exist_ok=True)



DEFAULT_SETTINGS_CONFIG = {
    "theme": "light",
    "last_message_send": None,
    "recording_enabled": False,
    "camera_index": 0,
    "microphone_index": 0,
    "speaker_index": 0,
    "voice_send_directly": False
}
class BasicUtils:
    @staticmethod
    def has_internet():
        try:
            # Пытаемся подключиться к DNS Google
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

