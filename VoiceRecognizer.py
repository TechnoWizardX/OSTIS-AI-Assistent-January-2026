from threading import Thread
from queue import Queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import os
from DataExchange import DataExchange


class VoiceRecognizer:
    def __init__(self):
        self.config = DataExchange.get_config()

        # === ПУТЬ К МОДЕЛИ ===
        self.model_path = "vosk-model-small-ru-0.22"

        self.text_queue = Queue()
        self.error_queue = Queue()

        if not os.path.exists(self.model_path):
            self.model = None
            self.recognizer = None
            self.error_queue.put(
                "Модель Vosk не найдена. Скачайте модель с https://alphacephei.com/vosk/models"
            )
            return

        # === VOSK ===
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)

        # === ПОТОК ===
        self.listening_status = False
        self.thread = None

        # Аудио очередь
        self.audio_queue = Queue()

    # ===============================
    # PUBLIC API
    # ===============================

    def start_recording(self):
        if self.listening_status:
            return

        self.listening_status = True
        self.thread = Thread(target=self._recognize_loop, daemon=True)
        self.thread.start()

    def stop_recording(self):
        self.listening_status = False

    def get_text(self):
        if not self.text_queue.empty():
            return self.text_queue.get()
        return None

    def get_error(self):
        if not self.error_queue.empty():
            return self.error_queue.get()
        return None

    # ===============================
    # INTERNAL
    # ===============================

    def _audio_callback(self, indata, frames, time, status):
        if status:
            self.error_queue.put(str(status))
        self.audio_queue.put(bytes(indata))

    def _recognize_loop(self):
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback
            ):
                while self.listening_status:
                    data = self.audio_queue.get()

                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self.text_queue.put(text)

                    # PartialResult можно использовать при необходимости
                    # else:
                    #     partial = json.loads(self.recognizer.PartialResult())
                    #     print(partial.get("partial", ""))

        except Exception as e:
            self.error_queue.put(f"VoiceRecognizer error: {e}")
            self.listening_status = False
