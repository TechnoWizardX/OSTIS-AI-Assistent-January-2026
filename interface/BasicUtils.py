import cv2
import pyaudio
import json
from datetime import datetime
from pathlib import Path
import sqlite3
import re 
CHAT_FILE = Path(__file__).parent / "data" / "chat_history.json"
CHAT_FILE.parent.mkdir(exist_ok=True)

SETTINGS_CONFIG_FILE = Path(__file__).parent / "data" / "settings_config.json"
SETTINGS_CONFIG_FILE.parent.mkdir(exist_ok=True)

DATABASE_FILE = Path(__file__).parent / "data" / "database.db"

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
    def load_settings_config() -> dict:
        """Загружает настройки из settings_config.json. Если файла нет, создаёт с дефолтными значениями."""
        if SETTINGS_CONFIG_FILE.exists():
            with open(SETTINGS_CONFIG_FILE, "r", encoding="utf-8") as file:
                settings_config = json.load(file)
                # Дополняем отсутствующие ключи дефолтными значениями
                for key, value in DEFAULT_SETTINGS_CONFIG.items():
                    if key not in settings_config:
                        settings_config[key] = value
                return settings_config
        return DEFAULT_SETTINGS_CONFIG.copy()

    @staticmethod
    def save_settings_config(settings_config: dict) -> None:
        """Сохраняет настройки в settings_config.json."""
        with open(SETTINGS_CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(settings_config, file, ensure_ascii=False, indent=4)

    @staticmethod
    def get_settings_config_value(key: str):
        """Возвращает значение конкретного параметра из настроек."""
        settings_config = BasicUtils.load_settings_config()
        return settings_config.get(key, DEFAULT_SETTINGS_CONFIG.get(key))

    @staticmethod
    def set_settings_config_value(key: str, value):
        """Устанавливает и сохраняет значение параметра в настройках."""
        settings_config = BasicUtils.load_settings_config()
        settings_config[key] = value
        BasicUtils.save_settings_config(settings_config)
    
    
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

    def _is_safe_identifier(self, name: str) -> bool:
        """Проверяет, что имя таблицы или колонки не содержит опасных символов."""
        # Разрешаем только латинские буквы, цифры и подчеркивание
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            raise ValueError(f"Недопустимое имя идентификатора: '{name}'. Разрешены только a-z, A-Z, 0-9 и _")
        return True

    def insert_data(self, id: int, firstname: str, surname: str, patronymic: str, gender: str,
                     birthday: str, dysfunctions: str, adaptation_status: str):
        self._open_connection()
        self._set_cursor()
        
        self.cursor.execute("INSERT INTO Users (id, firstname, surname, patronymic, gender, birthday, dysfunctions, adaptation_status) VALUES (?,?, ?, ?, ?, ?, ?, ?)",
                            (id, firstname, surname, patronymic, gender, birthday, dysfunctions, adaptation_status))
        self._commit()
        self._close_connection()

    def update_data(self, table_name: str, updates: dict, id: int):
        self._is_safe_identifier(table_name)
        if not updates:
            return
        for col in updates.keys():
            self._is_safe_identifier(col)
            
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
        self._is_safe_identifier(table_name)
        self._open_connection()
        self._set_cursor()
        self.cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
        self._commit()
        self._close_connection()

    def get_data(self, table_name: str, column_name: str, id: int) -> list:
        self._is_safe_identifier(table_name)
        self._is_safe_identifier(column_name)
        self._open_connection()
        self._set_cursor()
        self.cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE id = ?", (id,))
        data = self.cursor.fetchall()
        self._close_connection()
        return data
    
test = DataBaseEditor()
