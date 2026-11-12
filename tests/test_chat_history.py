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
    def test_load_recent_chat_history_limits_rows_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            with (
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


if __name__ == "__main__":
    unittest.main()
