import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import chat_history


class ChatHistoryTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        data_dir = Path(self._temp_dir.name)
        self.addCleanup(self._temp_dir.cleanup)
        self.addCleanup(chat_history.close_connection)

        for patcher in (
            patch.object(
                chat_history,
                "_database_path",
                return_value=data_dir / "chat_history.sqlite3",
            ),
            patch.object(
                chat_history,
                "get_user_data_file",
                side_effect=lambda name: data_dir / name,
            ),
            patch.object(
                chat_history,
                "get_legacy_data_file",
                side_effect=lambda name: data_dir / f"missing-{name}",
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_database_is_prepared_once_per_process(self):
        with patch.object(
            chat_history, "_prepare_database", wraps=chat_history._prepare_database
        ) as prepare:
            for index in range(3):
                chat_history.add_message("user", f"message {index}")
            chat_history.load_recent_chat_history(2)
            chat_history.load_chat_history_page(2, 0)
            chat_history.clear_chat_history()

        self.assertEqual(prepare.call_count, 1)

    def test_connection_is_reused_between_operations(self):
        chat_history.add_message("user", "first")
        connection = chat_history._connect()

        chat_history.add_message("user", "second")
        chat_history.load_recent_chat_history(1)

        self.assertIs(chat_history._connect(), connection)

    def test_wal_mode_is_enabled(self):
        chat_history.add_message("user", "first")

        mode = chat_history._connect().execute("PRAGMA journal_mode").fetchone()[0]

        self.assertEqual(mode.lower(), "wal")

    def test_close_connection_reopens_lazily(self):
        chat_history.add_message("user", "first")

        chat_history.close_connection()

        self.assertEqual(
            [message["text"] for message in chat_history.load_recent_chat_history(5)],
            ["first"],
        )

    def test_load_recent_chat_history_limits_rows_and_preserves_order(self):
        for index in range(1, 6):
            chat_history.add_message("user", f"message {index}")

        recent = chat_history.load_recent_chat_history(3)

        self.assertEqual(
            [message["text"] for message in recent],
            ["message 3", "message 4", "message 5"],
        )

    def test_load_recent_chat_history_rejects_negative_limit(self):
        with self.assertRaises(ValueError):
            chat_history.load_recent_chat_history(-1)

    def test_load_chat_history_page_returns_newest_page_in_order(self):
        for index in range(1, 71):
            chat_history.add_message("user", f"message {index}")

        newest = chat_history.load_chat_history_page(3, 0)
        older = chat_history.load_chat_history_page(3, 3)
        beyond_end = chat_history.load_chat_history_page(3, 100)

        self.assertEqual(
            [message["text"] for message in newest],
            ["message 68", "message 69", "message 70"],
        )
        self.assertEqual(
            [message["text"] for message in older],
            ["message 65", "message 66", "message 67"],
        )
        self.assertEqual(beyond_end, [])

    def test_load_chat_history_page_rejects_negative_values(self):
        with self.assertRaises(ValueError):
            chat_history.load_chat_history_page(-1, 0)
        with self.assertRaises(ValueError):
            chat_history.load_chat_history_page(1, -1)


if __name__ == "__main__":
    unittest.main()
