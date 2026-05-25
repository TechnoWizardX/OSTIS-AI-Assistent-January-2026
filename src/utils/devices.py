from PyQt6.QtMultimedia import QMediaDevices
import cv2
def get_available_cameras() -> list:
    cameras = []
    index = 0
    while True:
        cap = cv2.VideoCapture(index)
        if not cap.read()[0]:
            break
        else:
            cameras.append(f"Камера {index}")
        cap.release()
        index += 1
    return cameras


def get_available_microphones() -> list:
    microphones = QMediaDevices.audioInputs()
    mic_names = [microphone.description() for microphone in microphones]
    return mic_names