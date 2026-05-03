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

class Signals(QObject):
    voice_message_recognized = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    intent_recognized = pyqtSignal(dict)
global_signals = Signals()

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
        microphones = QMediaDevices.audioInputs()
        mic_names = [microphone.description() for microphone in microphones]
        return mic_names

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
    def has_internet():
        try:
            # Пытаемся подключиться к DNS Google
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False
    
    @staticmethod
    def load_chat_history() -> list:
        if CHAT_FILE.exists():
            with open(CHAT_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        return []
    @staticmethod
    def format_chat_history(history_list: list, limit: int = 5) -> str:
        """Превращает список словарей в строку: 'Автор: Текст'"""
        # Берем последние сообщения, чтобы не раздувать промпт
        recent = history_list[-limit:]
        lines = []
        for msg in recent:
            author = "Пользователь" if msg['author'] == "user" else "Ассистент"
            lines.append(f"{author}: {msg['text']}")
        
        return "\n".join(lines) if lines else "История пуста"
    @staticmethod
    def save_chat_history(chat_history) -> None:
        with open(CHAT_FILE, "w", encoding="utf-8") as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)
    
    @staticmethod
    def clear_chat_history() -> None:
        """Очищает файл истории чата (сохраняет пустой список)."""
        BasicUtils.save_chat_history([])        

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
    @staticmethod
    def logger(object : str, type : str = "INFO", message : str = "") -> None:
        """Логирование событий ядра
        Args:
            object (str): Объект, который вызвал событие
            type (str, optional): Тип события (INFO, WARNING, ERROR). Defaults to "INFO".
            message (str): Сообщение для логирования
        """
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{date}] [{type}] [{object}] {message}")


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
        BasicUtils.logger("DataBaseEditor", "INFO", f"Добавление данных в базу данных: {id}, {firstname}, {surname}, {patronymic}, {gender}, {birthday}, {dysfunctions}, {adaptation_status}")
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
        BasicUtils.logger("DataBaseEditor", "INFO", f"Обновление данных в базе данных: \n Таблица {table_name} \n Параметры {set_clause} \n ID: {id}")
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
        BasicUtils.logger("DataBaseEditor", "INFO", f"Удаление данных в базе данных: \n Таблица {table_name} \n ID: {id}")
        self.cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
        self._commit()
        self._close_connection()

    def get_data(self, table_name: str, column_name: str, id: int) -> list:
        self._is_safe_identifier(table_name)
        self._is_safe_identifier(column_name)
        self._open_connection()
        self._set_cursor()
        BasicUtils.logger("DataBaseEditor", "INFO", f"Получение данных из базы данных: \n Таблица {table_name} \n Поле(столбец) {column_name} \n ID: {id}")
        self.cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE id = ?", (id,))
        data = self.cursor.fetchall()
        self._close_connection()
        return data
    
test = DataBaseEditor()
