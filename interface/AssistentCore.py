import cv2
import pyaudio
def get_available_cameras():
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

def get_available_microphones():
    
    return []