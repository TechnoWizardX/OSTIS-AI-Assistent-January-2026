from PySide6.QtMultimedia import QMediaDevices


def get_available_cameras() -> list:
    """Возвращает список камер через QMediaDevices.

    Мгновенно и без открытия устройств: не конфликтует с потоком камеры
    жестового ввода и не блокирует GUI (в отличие от cv2.VideoCapture).
    Порядок устройств соответствует порядку индексов cv2.VideoCapture.
    """
    return [device.description() for device in QMediaDevices.videoInputs()]


def get_available_microphones() -> list:
    microphones = QMediaDevices.audioInputs()
    mic_names = [microphone.description() for microphone in microphones]
    return mic_names
