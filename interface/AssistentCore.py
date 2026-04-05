import cv2

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