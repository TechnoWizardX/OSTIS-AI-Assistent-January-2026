import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.services.ai_service import intent_handler
from src.services.ai_service.streaming import StreamingMessageExtractor
from src.utils.BasicUtils import global_signals

FULL_RESPONSE = '{"message": "Привет! Чем могу помочь?", "tasks": []}'


class StreamingMessageExtractorTests(unittest.TestCase):
    def _feed_chunks(self, chunks):
        extractor = StreamingMessageExtractor()
        parts = []
        for chunk in chunks:
            part = extractor.feed(chunk)
            if part:
                parts.append(part)
        return extractor, parts

    def test_message_is_extracted_in_streaming_order(self):
        chunks = [
            '{"messa',
            'ge": "Прив',
            'ет! Чем могу помочь?"',
            ', "tasks": []}',
        ]
        extractor, parts = self._feed_chunks(chunks)
        self.assertEqual("".join(parts), "Привет! Чем могу помочь?")
        self.assertEqual(extractor.message(), "Привет! Чем могу помочь?")
        self.assertTrue(extractor.announced)

    def test_no_message_key_yields_nothing(self):
        extractor, parts = self._feed_chunks(['{"tasks": []}'])
        self.assertEqual(parts, [])
        self.assertFalse(extractor.announced)

    def test_split_inside_escape_sequence(self):
        chunks = [
            '{"message": "Скачиваю \\',
            '"файл\\" готово",',
            ' "tasks": []}',
        ]
        _, parts = self._feed_chunks(chunks)
        self.assertEqual("".join(parts), 'Скачиваю "файл" готово')

    def test_split_inside_unicode_escape(self):
        chunks = ['{"message": "пр\\u04', '38вет", "tasks": []}']
        _, parts = self._feed_chunks(chunks)
        self.assertEqual("".join(parts), "привет")

    def test_split_inside_newline_escape(self):
        chunks = ['{"message": "строка\\', 'nвторая", "tasks": []}']
        _, parts = self._feed_chunks(chunks)
        self.assertEqual("".join(parts), "строка\nвторая")

    def test_nothing_after_closing_quote(self):
        chunks = ['{"message": "done", "tasks": [{"function": "x"}]}']
        _, parts = self._feed_chunks(chunks)
        self.assertEqual("".join(parts), "done")

    def test_empty_message(self):
        _, parts = self._feed_chunks(['{"message": "", "tasks": []}'])
        self.assertEqual(parts, [])

    def test_feed_after_done_is_ignored(self):
        extractor, parts = self._feed_chunks([FULL_RESPONSE, 'garbage"}'])
        self.assertEqual("".join(parts), "Привет! Чем могу помочь?")


class OfflineStreamingRequestTests(unittest.TestCase):
    def setUp(self):
        self.handler = intent_handler.IntentHandler(api_key="test-key")
        self.handler._ollama_available = True

    def _fake_response(self, tokens):
        lines = [json.dumps({"response": token, "done": False}) for token in tokens]
        lines.append(json.dumps({"response": "", "done": True}))
        response = MagicMock()
        response.status_code = 200
        response.iter_lines.return_value = [line.encode("utf-8") for line in lines]
        response.__enter__ = MagicMock(return_value=response)
        response.__exit__ = MagicMock(return_value=False)
        return response

    def test_offline_request_streams_and_returns_intent(self):
        parts = []
        global_signals.stream_part.connect(parts.append)

        tokens = ['{"message": "Пр', 'ивет", "tasks": []}']
        with patch.object(
            intent_handler.requests, "post", return_value=self._fake_response(tokens)
        ) as post:
            result = self.handler._send_offline_request("prompt", "qwen2.5:3b")

        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs.get("stream"), True)
        self.assertEqual(result["message"], "Привет")
        self.assertEqual("".join(parts), "Привет")
        # Строки должны приходить без буферизации по мере генерации
        self.assertEqual(
            post.return_value.iter_lines.call_args.kwargs.get("chunk_size"), 1
        )

    def test_connection_error_emits_abort(self):
        aborted = []
        global_signals.stream_aborted.connect(lambda: aborted.append(True))
        global_signals.stream_part.connect(lambda _: None)

        with patch.object(
            intent_handler.requests,
            "post",
            side_effect=intent_handler.requests.exceptions.ConnectionError("dead"),
        ):
            result = self.handler._send_offline_request("prompt", "qwen2.5:3b")

        self.assertIn("недоступна", result["message"])
        self.assertEqual(aborted, [True])
        self.assertFalse(self.handler._ollama_available)


if __name__ == "__main__":
    unittest.main()
