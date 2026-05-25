import sqlite3
import re
from .logger import logger
from pathlib import Path

DATABASE_FILE = Path(__file__).parent / "data" / "database.db"
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
        self._ensure_default_user()
        self._commit()
        self._close_connection()

    def _ensure_default_user(self):
        """Создаёт запись пользователя с id=0, если она не существует."""
        self.cursor.execute("SELECT id FROM Users WHERE id = ?", (0,))
        if not self.cursor.fetchone():
            self.cursor.execute(
                "INSERT INTO Users (id, firstname, surname, patronymic, gender, birthday, dysfunctions, adaptation_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (0, "", "", "", "", "", "", "")
            )
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
        logger("DataBaseEditor", "INFO", f"Добавление данных в базу данных: {id}, {firstname}, {surname}, {patronymic}, {gender}, {birthday}, {dysfunctions}, {adaptation_status}")
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
        logger("DataBaseEditor", "INFO", f"Обновление данных в базе данных: \n Таблица {table_name} \n Параметры {set_clause} \n ID: {id}")
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
        logger("DataBaseEditor", "INFO", f"Удаление данных в базе данных: \n Таблица {table_name} \n ID: {id}")
        self.cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (id,))
        self._commit()
        self._close_connection()

    def get_data(self, table_name: str, column_name: str, id: int) -> list:
        self._is_safe_identifier(table_name)
        self._is_safe_identifier(column_name)
        self._open_connection()
        self._set_cursor()
        logger("DataBaseEditor", "INFO", f"Получение данных из базы данных: \n Таблица {table_name} \n Поле(столбец) {column_name} \n ID: {id}")
        self.cursor.execute(f"SELECT {column_name} FROM {table_name} WHERE id = ?", (id,))
        data = self.cursor.fetchall()
        self._close_connection()
        return data
    
DATABASE_EDITOR = DataBaseEditor()