import cv2
import pyaudio
import json
from datetime import datetime
from pathlib import Path

CHAT_FILE = Path(__file__).parent / "data" / "chat_history.json"
CHAT_FILE.parent.mkdir(exist_ok=True)


class BasicUtils:
    @staticmethod
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
    
    @staticmethod
    def get_available_microphones() -> list:
        return []
    
    
    @staticmethod
    def load_chat_history() -> list:
        if CHAT_FILE.exists():
            with open(CHAT_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        return []
    
    @staticmethod
    def save_chat_history(chat_history) -> None:
        with open(CHAT_FILE, "w", encoding="utf-8") as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)

    @staticmethod
    def add_message(author: str, message: str):
        history = BasicUtils.load_chat_history()
        history.append({
            "author": author,
            "text": message,
            "time": datetime.now().strftime("%H:%M"),
            "day": datetime.now().strftime("%D-%m-%Y")
        })
        BasicUtils.save_chat_history(history)

    def get_user_data() -> dict:
        pass