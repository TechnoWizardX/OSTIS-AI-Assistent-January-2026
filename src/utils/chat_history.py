import atexit
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from src.utils.logger import logger
from src.utils.user_data import get_legacy_data_file, get_user_data_file

_LEGACY_HISTORY_FILE = "chat_history.json"
_HISTORY_DATABASE_FILE = "chat_history.sqlite3"
_MIGRATION_MARKER_FILE = ".chat_history_migration_complete"

# Общее долгоживущее соединение: открывается один раз за процесс и
# защищается блокировкой (запись идёт и из GUI-потока, и из IntentWorker).
_connection: sqlite3.Connection | None = None
_connection_lock = threading.Lock()


def _database_path() -> Path:
    return get_user_data_file(_HISTORY_DATABASE_FILE)


def close_connection() -> None:
    """Закрывает общее соединение (для корректного завершения и тестов)."""
    global _connection
    with _connection_lock:
        if _connection is not None:
            try:
                _connection.close()
            except sqlite3.Error as error:
                logger("ChatHistory", "WARNING", f"Ошибка закрытия соединения: {error}")
            _connection = None


atexit.register(close_connection)


def _get_connection() -> sqlite3.Connection:
    """Возвращает общее соединение, при первом обращении инициализируя БД."""
    global _connection
    with _connection_lock:
        if _connection is None:
            _connection = _open_connection()
        return _connection


def _new_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), timeout=5, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def _open_connection() -> sqlite3.Connection:
    """Создаёт соединение и один раз за процесс проверяет целостность и схему."""
    migration_marker = get_user_data_file(_MIGRATION_MARKER_FILE)

    connection = _new_connection()
    try:
        check = connection.execute("PRAGMA quick_check").fetchone()
        if check is None or check[0] != "ok":
            raise sqlite3.DatabaseError("SQLite integrity check failed.")
        table = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'messages'"
        ).fetchone()
        if table is not None:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(messages)"
                )
            }
            expected = {
                "id",
                "role",
                "author",
                "content",
                "created_at",
                "display_time",
                "display_day",
            }
            if not expected.issubset(columns):
                raise sqlite3.DatabaseError(
                    "Chat history table has an incompatible schema."
                )
    except sqlite3.DatabaseError as error:
        try:
            connection.close()
        except sqlite3.Error:
            pass
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = _database_path()
        backup_path = path.with_name(
            f"{path.stem}.corrupt-{timestamp}{path.suffix}"
        )
        path.replace(backup_path)
        logger(
            "ChatHistory",
            "ERROR",
            f"Invalid history database preserved at {backup_path}; "
            f"creating a fresh database: {error}",
        )
        connection = _new_connection()

    migration_complete = True
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            display_time TEXT NOT NULL,
            display_day TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    migrated = connection.execute(
        "SELECT value FROM metadata WHERE key = 'legacy_history_migrated'"
    ).fetchone()
    if migrated is None:
        has_messages = connection.execute("SELECT 1 FROM messages LIMIT 1").fetchone()
        if migration_marker.exists() or has_messages is not None:
            connection.execute(
                "INSERT INTO metadata (key, value) "
                "VALUES ('legacy_history_migrated', '1')"
            )
        else:
            migration_complete = _migrate_legacy_history(connection)
    connection.commit()
    if migration_complete:
        migration_marker.touch(exist_ok=True)
    return connection


def _legacy_timestamp(message: dict) -> str:
    time_value = message.get("time")
    day_value = message.get("day")
    if isinstance(time_value, str) and isinstance(day_value, str):
        day_candidates = [day_value]
        day_candidates.extend(day_value.split("-"))
        for day_candidate in day_candidates:
            for date_format in (
                "%d-%m-%Y",
                "%m/%d/%y",
                "%m-%d-%Y",
                "%Y-%m-%d",
            ):
                try:
                    date = datetime.strptime(day_candidate, date_format).date()
                    time = datetime.strptime(time_value, "%H:%M").time()
                    return datetime.combine(date, time).astimezone().isoformat(
                        timespec="seconds"
                    )
                except ValueError:
                    continue
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _insert_message(
    connection: sqlite3.Connection,
    author: str,
    text: str,
    timestamp: str,
    display_time: str,
    display_day: str,
) -> None:
    role = "user" if author == "user" else "assistant"
    connection.execute(
        """
        INSERT INTO messages (
            role, author, content, created_at, display_time, display_day
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (role, author, text, timestamp, display_time, display_day),
    )


def _migrate_legacy_history(connection: sqlite3.Connection) -> bool:
    legacy_file = get_legacy_data_file(_LEGACY_HISTORY_FILE)
    if not legacy_file.is_file():
        connection.execute(
            "INSERT INTO metadata (key, value) VALUES ('legacy_history_migrated', '1')"
        )
        return True

    try:
        with legacy_file.open("r", encoding="utf-8") as file:
            history = json.load(file)
        if not isinstance(history, list):
            raise ValueError("Legacy history must contain a JSON list.")

        migrated_messages = []
        for index, message in enumerate(history):
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("author"), str)
                or not isinstance(message.get("text"), str)
            ):
                raise ValueError(
                    f"Legacy history entry {index} has an invalid shape."
                )

            timestamp = _legacy_timestamp(message)
            display_time = message.get("time")
            display_day = message.get("day")
            if not isinstance(display_time, str):
                display_time = datetime.fromisoformat(timestamp).strftime("%H:%M")
            if not isinstance(display_day, str):
                display_day = datetime.fromisoformat(timestamp).strftime("%D-%m-%Y")
            migrated_messages.append(
                (
                    message["author"],
                    message["text"],
                    timestamp,
                    display_time,
                    display_day,
                )
            )

        for author, text, timestamp, display_time, display_day in migrated_messages:
            _insert_message(
                connection,
                author,
                text,
                timestamp,
                display_time,
                display_day,
            )
        logger(
            "ChatHistory",
            "INFO",
            f"Migrated {len(history)} messages from {legacy_file}",
        )
        connection.execute(
            "INSERT INTO metadata (key, value) "
            "VALUES ('legacy_history_migrated', '1')"
        )
        return True
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        logger(
            "ChatHistory",
            "ERROR",
            f"Could not migrate history from {legacy_file}; the original was "
            f"left untouched: {error}",
        )
        return False


def _history_entry(row: sqlite3.Row) -> dict[str, str]:
    return {
        "author": row["author"],
        "text": row["content"],
        "time": row["display_time"],
        "day": row["display_day"],
    }


def load_chat_history() -> list[dict[str, str]]:
    connection = _get_connection()
    with _connection_lock:
        rows = connection.execute(
            """
            SELECT author, content, display_time, display_day
            FROM messages
            ORDER BY id ASC
            """
        ).fetchall()
    return [_history_entry(row) for row in rows]


def load_recent_chat_history(limit: int = 5) -> list[dict[str, str]]:
    """Load only the most recent messages, preserving chronological order."""
    if limit < 0:
        raise ValueError("History limit must not be negative.")

    connection = _get_connection()
    with _connection_lock:
        rows = connection.execute(
            """
            SELECT author, content, display_time, display_day
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_history_entry(row) for row in reversed(rows)]


def format_chat_history(history_list: list, limit: int = 5) -> str:
    """Format the most recent messages for the AI context."""
    recent = history_list[-limit:]
    lines = []
    for message in recent:
        author = "Пользователь" if message["author"] == "user" else "Ассистент"
        lines.append(f"{author}: {message['text']}")
    return "\n".join(lines) if lines else "История пуста"


def clear_chat_history() -> None:
    """Delete all stored messages without removing the migration marker."""
    connection = _get_connection()
    with _connection_lock, connection:
        connection.execute("DELETE FROM messages")


def add_message(author: str, message: str) -> None:
    if not isinstance(author, str):
        raise TypeError("Message author must be a string.")
    if not isinstance(message, str):
        raise TypeError("Message content must be a string.")

    now = datetime.now().astimezone()
    connection = _get_connection()
    with _connection_lock, connection:
        _insert_message(
            connection,
            author,
            message,
            now.isoformat(timespec="seconds"),
            now.strftime("%H:%M"),
            now.strftime("%D-%m-%Y"),
        )
