import cv2
import pyaudio
import json
from datetime import datetime
from pathlib import Path
import sqlite3
CHAT_FILE = Path(__file__).parent / "data" / "chat_history.json"
CHAT_FILE.parent.mkdir(exist_ok=True)

DATABASE_FILE = Path(__file__).parent / "data" / "database.db"
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


class DataBaseEditor():
    def __init__(self):
        self._open_connection()
        self._set_cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS Users
                             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            firstname TEXT, 
                            surname TEXT, 
                            patronymic TEXT,
                            gender TEXT,
                            birthday TEXT,
                            dysfunctions TEXT,
                            adaptation_status TEXT)""")
        self._commit()
        self._close_connection()
    def _open_connection(self):
        self.connection = sqlite3.connect(DATABASE_FILE)
    def _close_connection(self):
        self.connection.close()
    def _set_cursor(self):
        self.cursor = self.connection.cursor()
    
    def _commit(self):
        self.connection.commit()

    def insert_data(self, id: int, firstname: str, surname: str, patronymic: str, gender: str,
                     birthday: str, dysfunctions: str, adaptation_status: str):
        self._open_connection()
        self._set_cursor()
        
        self.cursor.execute("INSERT INTO Users (id, firstname, surname, patronymic, gender, birthday, dysfunctions, adaptation_status) VALUES (?,?, ?, ?, ?, ?, ?, ?)",
                            (id, firstname, surname, patronymic, gender, birthday, dysfunctions, adaptation_status))
        self._commit()
        self._close_connection()

    def update_data(self, table_name: str, updates: dict, id: int):

        if not updates:
            return 
        # Формируем SET-часть: "firstname=?, surname=?"
        set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
        
        # Собираем параметры: сначала значения, в конце ID
        values = list(updates.values()) + [id]

        self._open_connection()
        self._set_cursor()
        # Выполняем запрос с динамическим количеством параметров
        self.cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", values)
        self._commit()
        self._close_connection()

    def delete_data(self, table_name, id):
        self._open_connection()
        self._set_cursor()
        self.cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
        self._commit()
        self._close_connection()

    def get_data(self, table_name: str, column_name: str, id: int) -> list:
        self._open_connection()
        self._set_cursor()
        self.cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE id = ?", (id,))
        data = self.cursor.fetchall()
        self._close_connection()
        return data
    
test = DataBaseEditor()
