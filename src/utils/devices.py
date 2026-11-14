import cv2
from PySide6.QtMultimedia import QMediaDevices


def get_available_cameras() -> list:
    cameras = []
    index = 0
    while True:
        cap = cv2.VideoCapture(index)
        try:
            available = bool(cap.read()[0])
        finally:
            cap.release()
        if not available:
            break
        cameras.append(f"Камера {index}")
        index += 1
    return cameras


def get_available_microphones() -> list:
    microphones = QMediaDevices.audioInputs()
    mic_names = [microphone.description() for microphone in microphones]
    return mic_names
