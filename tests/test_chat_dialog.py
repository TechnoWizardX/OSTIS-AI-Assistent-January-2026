import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication

from src.gui.widgets import chat_dialog
from src.gui.widgets.message_item import Message

_APP = QApplication.instance() or QApplication([])

MESSAGES = [
    {"author": "user", "text": f"message {index}", "time": "12:00"}
    for index in range(70)
]


class DialogBoxHistoryTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._patcher = patch.object(
            chat_dialog,
            "load_chat_history_page",
            side_effect=self._load_page,
        )
        self._patcher.start()
        self.dialog = chat_dialog.DialogBox()
        self.dialog.resize(400, 300)

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        _APP.processEvents()
        self._patcher.stop()

    def _load_page(self, limit, offset):
        self.calls.append((limit, offset))
        end = max(len(MESSAGES) - offset, 0)
        start = max(end - limit, 0)
        return MESSAGES[start:end]

    def _message_widgets(self):
        widgets = []
        for index in range(self.dialog.main_frame_lay.count()):
            widget = self.dialog.main_frame_lay.itemAt(index).widget()
            if isinstance(widget, Message):
                widgets.append(widget)
        return widgets

    def test_history_is_not_loaded_until_shown(self):
        self.assertEqual(self.calls, [])
        self.assertEqual(self._message_widgets(), [])

    def test_first_show_loads_only_the_newest_page(self):
        self.dialog.show()
        _APP.processEvents()

        self.assertEqual(self.calls, [(30, 0)])
        self.assertEqual(len(self._message_widgets()), 30)
        self.assertTrue(self.dialog.load_more_btn.isVisible())

    def test_load_older_prepends_the_previous_page(self):
        self.dialog.show()
        _APP.processEvents()

        self.dialog._load_older()

        self.assertEqual(self.calls[-1], (30, 30))
        widgets = self._message_widgets()
        self.assertEqual(len(widgets), 60)
        self.assertEqual(widgets[0].text_content, "message 10")
        self.assertEqual(widgets[-1].text_content, "message 69")

    def test_load_more_button_disappears_when_history_is_exhausted(self):
        self.dialog.show()
        _APP.processEvents()

        self.dialog._load_older()
        self.dialog._load_older()

        self.assertEqual(len(self._message_widgets()), 70)
        self.assertFalse(self.dialog.load_more_btn.isVisible())
        self.assertEqual(len(self.calls), 3)

    def test_reload_history_returns_to_the_newest_page(self):
        self.dialog.show()
        _APP.processEvents()
        self.dialog._load_older()

        self.dialog.reload_history()

        self.assertEqual(len(self._message_widgets()), 30)
        self.assertEqual(self.calls[-1], (30, 0))

    def test_hidden_dialog_defers_live_messages_until_next_show(self):
        self.dialog.show()
        _APP.processEvents()

        chat_dialog.ui_signals.message_sent.emit("IAMOS", "live message")
        self.assertEqual(len(self._message_widgets()), 31)

        self.dialog.hide()
        chat_dialog.ui_signals.message_sent.emit("IAMOS", "hidden message")

        self.assertEqual(len(self._message_widgets()), 31)
        self.assertTrue(self.dialog._history_dirty)


if __name__ == "__main__":
    unittest.main()
