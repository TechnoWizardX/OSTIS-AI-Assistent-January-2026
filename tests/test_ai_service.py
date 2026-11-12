import io
import os
import sys
import unittest
import wave
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from faster_whisper.audio import decode_audio

from src.services.ai_service.llm_client import (
    OPENROUTER_CHAT_COMPLETIONS_URL,
    MedicalAPI,
)


class MedicalAPITests(unittest.TestCase):
    def test_posts_to_chat_completions_endpoint(self):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }

        with patch(
            "src.services.ai_service.llm_client.requests.post",
            return_value=response,
        ) as post:
            result = MedicalAPI(api_key="test-key").generate(
                "prompt",
                system="system",
            )

        self.assertEqual(result, "ok")
        self.assertEqual(post.call_args.args[0], OPENROUTER_CHAT_COMPLETIONS_URL)
        self.assertEqual(
            post.call_args.kwargs["json"]["messages"],
            [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "prompt"},
            ],
        )


class WhisperAudioTests(unittest.TestCase):
    def test_faster_whisper_decodes_in_memory_wav(self):
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 1600)

        decoded = decode_audio(io.BytesIO(wav_buffer.getvalue()))

        self.assertEqual(decoded.shape, (1600,))
        self.assertEqual(str(decoded.dtype), "float32")


if __name__ == "__main__":
    unittest.main()
