import json
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication

from src.core import assistant_core
from src.core.assistant_core import AssistentCore
from src.gui import signals as gui_signals
from src.gui.widgets.chat_send_box import ChatSendBox
from src.services.ai_service import intent_handler
from src.utils.BasicUtils import global_signals

_APP = QApplication.instance() or QApplication([])


class CancelButtonTests(unittest.TestCase):
    def setUp(self):
        self.box = ChatSendBox()
        self.events = []
        gui_signals.ui_signals.cancel_requested.connect(
            lambda: self.events.append("cancel")
        )
        gui_signals.ui_signals.message_sent.connect(
            lambda author, text: self.events.append(("send", author, text))
        )

    def tearDown(self):
        self.box.deleteLater()
        _APP.processEvents()

    def test_typing_switches_button_to_cancel_and_back(self):
        self.assertEqual(self.box.send_btn.text(), "Отправить")

        gui_signals.ui_signals.typing_started.emit()
        self.assertEqual(self.box.send_btn.text(), "Отмена")
        self.assertEqual(self.box.send_btn.property("themeIcon"), "cancel.svg")

        gui_signals.ui_signals.typing_finished.emit()
        self.assertEqual(self.box.send_btn.text(), "Отправить")
        self.assertEqual(self.box.send_btn.property("themeIcon"), "send.svg")

    def test_click_in_cancel_mode_requests_cancel_without_sending(self):
        self.box.chat_send_input.setPlainText("привет")
        gui_signals.ui_signals.typing_started.emit()

        self.box.send_btn.click()

        self.assertEqual(self.events, ["cancel"])
        self.assertEqual(self.box.chat_send_input.toPlainText(), "привет")

    def test_enter_does_not_send_while_answering(self):
        self.box.chat_send_input.setPlainText("привет")
        gui_signals.ui_signals.typing_started.emit()

        self.box.send_message()

        self.assertEqual(self.events, [])


class HandlerCancelTests(unittest.TestCase):
    def setUp(self):
        self.handler = intent_handler.IntentHandler(api_key="test-key")
        self.handler._ollama_available = True
        self.aborted = []
        global_signals.stream_aborted.connect(lambda: self.aborted.append(True))

    def _fake_response(self, lines):
        response = MagicMock()
        response.status_code = 200
        response.iter_lines.return_value = [line.encode("utf-8") for line in lines]
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        return response

    def test_cancel_before_start_skips_request(self):
        cancel_event = threading.Event()
        cancel_event.set()

        with patch.object(intent_handler.requests, "post") as post:
            result = self.handler._send_offline_request(
                "prompt", "qwen2.5:3b", cancel_event
            )

        post.assert_not_called()
        self.assertIsNone(result)
        self.assertEqual(self.aborted, [True])

    def test_cancel_mid_stream_stops_processing(self):
        cancel_event = threading.Event()
        lines = [
            json.dumps({"response": '{"message": "Пр', "done": False}),
            json.dumps({"response": 'ивет", "tasks": []}', "done": False}),
        ]

        def iter_lines(chunk_size=None):
            yield lines[0].encode("utf-8")
            cancel_event.set()  # пользователь нажал «Отмену»
            yield lines[1].encode("utf-8")

        response = self._fake_response(lines)
        response.iter_lines.side_effect = iter_lines

        with patch.object(
            intent_handler.requests, "post", return_value=response
        ):
            result = self.handler._send_offline_request(
                "prompt", "qwen2.5:3b", cancel_event
            )

        self.assertIsNone(result)
        self.assertEqual(self.aborted, [True])


class WorkerCancelTests(unittest.TestCase):
    def test_cancelled_worker_emits_nothing(self):
        handler = MagicMock()
        handler.send_request.return_value = {"message": "ответ", "tasks": []}
        worker = intent_handler.IntentWorker(
            handler=handler, user_text="привет", use_online=True
        )
        results, errors = [], []
        worker.result_ready.connect(results.append)
        worker.error.connect(errors.append)

        worker.cancel_event.set()
        worker.run()

        self.assertEqual(results, [])
        self.assertEqual(errors, [])

    def test_cancel_closes_active_stream(self):
        handler = MagicMock()
        handler._active_response = MagicMock()
        handler._active_stream = MagicMock()
        worker = intent_handler.IntentWorker(
            handler=handler, user_text="привет"
        )

        worker.cancel()

        self.assertTrue(worker.cancel_event.is_set())
        handler._active_response.close.assert_called_once()
        handler._active_stream.close.assert_called_once()


class CoreCancelTests(unittest.TestCase):
    def test_cancel_sets_flag_and_restores_ui(self):
        core = object.__new__(AssistentCore)
        worker = MagicMock()
        worker.isRunning.return_value = True
        core.ai_thread = worker

        finished = []
        gui_signals.ui_signals.typing_finished.connect(
            lambda: finished.append(True)
        )
        cancel_logged = []
        original_logger = assistant_core.logger
        assistant_core.logger = lambda *args, **kwargs: cancel_logged.append(args)
        try:
            core.cancel_current_request()
        finally:
            assistant_core.logger = original_logger

        worker.cancel.assert_called_once()
        self.assertEqual(finished, [True])

    def test_cancel_without_active_worker_is_safe(self):
        core = object.__new__(AssistentCore)
        core.ai_thread = None
        core.cancel_current_request()  # не должно бросить исключение

    def test_cancel_when_worker_finished_is_noop(self):
        core = object.__new__(AssistentCore)
        worker = MagicMock()
        worker.isRunning.return_value = False
        core.ai_thread = worker
        core.cancel_current_request()
        worker.cancel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
