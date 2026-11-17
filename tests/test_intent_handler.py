import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.services.ai_service import intent_handler


class LazyOpenAITests(unittest.TestCase):
    def test_module_does_not_import_openai(self):
        self.assertFalse(hasattr(intent_handler, "openai"))

    def test_handler_construction_does_not_create_the_client(self):
        handler = intent_handler.IntentHandler(api_key="test-key")

        self.assertIsNone(handler._online_client)

    def test_update_api_key_drops_the_cached_client(self):
        handler = intent_handler.IntentHandler(api_key="test-key")
        handler._online_client = MagicMock()

        handler.update_api_key("new-key")

        self.assertIsNone(handler._online_client)
        self.assertEqual(handler._api_key, "new-key")


class StartOllamaTests(unittest.TestCase):
    def setUp(self):
        self.handler = intent_handler.IntentHandler(api_key="test-key")

    def test_running_server_is_not_started_twice(self):
        connect = MagicMock()
        connect.return_value.__enter__.return_value = MagicMock()

        with (
            patch.object(intent_handler.socket, "create_connection", connect),
            patch.object(intent_handler.subprocess, "Popen") as popen,
        ):
            self.handler.start_ollama()

        connect.assert_called_once_with((intent_handler.OLLAMA_HOST, intent_handler.OLLAMA_PORT), timeout=0.5)
        popen.assert_not_called()
        self.assertIsNone(self.handler._ollama_process)

    def test_missing_server_is_started(self):
        with (
            patch.object(
                intent_handler.socket,
                "create_connection",
                side_effect=OSError("refused"),
            ),
            patch.object(
                intent_handler.shutil,
                "which",
                return_value="C:/fake/ollama.exe",
            ),
            patch.object(intent_handler.subprocess, "Popen") as popen,
        ):
            self.handler.start_ollama()

        popen.assert_called_once()
        self.assertIsNotNone(self.handler._ollama_process)
        self.handler._ollama_process = None

    def test_missing_server_without_ollama_installed(self):
        with (
            patch.object(
                intent_handler.socket,
                "create_connection",
                side_effect=OSError("refused"),
            ),
            patch.object(intent_handler.shutil, "which", return_value=None),
            patch.object(intent_handler.subprocess, "Popen") as popen,
        ):
            self.handler.start_ollama()

        popen.assert_not_called()
        self.assertIsNone(self.handler._ollama_process)
        self.assertFalse(self.handler._ollama_available)


if __name__ == "__main__":
    unittest.main()
