import re
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from src.utils.logger import logger
from src.utils.user_data import get_legacy_data_file, get_user_data_file

_USER_COLUMNS = {
    "id",
    "firstname",
    "surname",
    "patronymic",
    "gender",
    "birthday",
    "dysfunctions",
    "adaptation_status",
}


def _is_valid_database(path: Path) -> bool:
    try:
        with closing(sqlite3.connect(path)) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
            if result is None or result[0] != "ok":
                return False
            table = connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'Users'"
            ).fetchone()
            if table is None:
                return True
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(Users)")
            }
            return _USER_COLUMNS.issubset(columns)
    except sqlite3.DatabaseError:
        return False


def _backup_invalid_database(path: Path) -> None:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = path.with_name(f"{path.stem}.corrupt-{timestamp}{path.suffix}")
    path.replace(backup_path)
    logger(
        "DataBaseEditor",
        "ERROR",
        f"Invalid database preserved at {backup_path}; creating a fresh database.",
    )


class DataBaseEditor:
    def __init__(self, database_path: Path | None = None):
        self._configured_path = database_path
        self.database_path: Path | None = None
        self._initialized = False

    def _initialize_database(self) -> None:
        if self._initialized:
            return

        database_path = self._configured_path or get_user_data_file("database.db")
        database_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path = get_legacy_data_file("database.db")
        if not database_path.exists() and legacy_path.is_file():
            if _is_valid_database(legacy_path):
                shutil.copy2(legacy_path, database_path)
                logger(
                    "DataBaseEditor",
                    "INFO",
                    f"Migrated profile database from {legacy_path}",
                )
            else:
                logger(
                    "DataBaseEditor",
                    "ERROR",
                    f"Legacy database is invalid and was left untouched: "
                    f"{legacy_path}",
                )

        if database_path.exists() and not _is_valid_database(database_path):
            _backup_invalid_database(database_path)

        connection = sqlite3.connect(database_path)
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS Users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firstname TEXT,
                    surname TEXT,
                    patronymic TEXT,
                    gender TEXT,
                    birthday TEXT,
                    dysfunctions TEXT,
                    adaptation_status TEXT
                )
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO Users (
                    id, firstname, surname, patronymic, gender, birthday,
                    dysfunctions, adaptation_status
                ) VALUES (0, '', '', '', '', '', '', '')
                """
            )
            connection.commit()
        finally:
            connection.close()

        self.database_path = database_path
        self._initialized = True

    def _open_connection(self):
        self._initialize_database()
        self.connection = sqlite3.connect(self.database_path)

    def _close_connection(self):
        self.connection.close()

    def _set_cursor(self):
        self.cursor = self.connection.cursor()

    def _commit(self):
        self.connection.commit()

    def _is_safe_identifier(self, name: str) -> bool:
        """Validate a table or column identifier before using it in SQL."""
        if not re.fullmatch(r"[a-zA-Z0-9_]+", name):
            raise ValueError(
                f"Invalid SQL identifier {name!r}; use letters, digits, or _."
            )
        return True

    def insert_data(
        self,
        id: int,
        firstname: str,
        surname: str,
        patronymic: str,
        gender: str,
        birthday: str,
        dysfunctions: str,
        adaptation_status: str,
    ):
        self._open_connection()
        try:
            self._set_cursor()
            logger(
                "DataBaseEditor",
                "INFO",
                f"Adding profile data for user id={id}",
            )
            self.cursor.execute(
                """
                INSERT INTO Users (
                    id, firstname, surname, patronymic, gender, birthday,
                    dysfunctions, adaptation_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id,
                    firstname,
                    surname,
                    patronymic,
                    gender,
                    birthday,
                    dysfunctions,
                    adaptation_status,
                ),
            )
            self._commit()
        finally:
            self._close_connection()

    def update_data(self, table_name: str, updates: dict, id: int):
        self._is_safe_identifier(table_name)
        if not updates:
            return
        for column in updates:
            self._is_safe_identifier(column)

        set_clause = ", ".join(f"{column} = ?" for column in updates)
        values = list(updates.values()) + [id]

        self._open_connection()
        try:
            self._set_cursor()
            logger(
                "DataBaseEditor",
                "INFO",
                f"Updating {table_name} row with id={id}: {set_clause}",
            )
            self.cursor.execute(
                f"UPDATE {table_name} SET {set_clause} WHERE id = ?",
                values,
            )
            self._commit()
        finally:
            self._close_connection()

    def delete_data(self, table_name: str, id: int):
        self._is_safe_identifier(table_name)
        self._open_connection()
        try:
            self._set_cursor()
            logger(
                "DataBaseEditor",
                "INFO",
                f"Deleting from {table_name} row with id={id}",
            )
            self.cursor.execute(
                f"DELETE FROM {table_name} WHERE id = ?",
                (id,),
            )
            self._commit()
        finally:
            self._close_connection()

    def get_data(self, table_name: str, column_name: str, id: int) -> list:
        self._is_safe_identifier(table_name)
        self._is_safe_identifier(column_name)
        self._open_connection()
        try:
            self._set_cursor()
            logger(
                "DataBaseEditor",
                "INFO",
                f"Reading {column_name} from {table_name} for id={id}",
            )
            self.cursor.execute(
                f"SELECT {column_name} FROM {table_name} WHERE id = ?",
                (id,),
            )
            return self.cursor.fetchall()
        finally:
            self._close_connection()


DATABASE_EDITOR = DataBaseEditor()
