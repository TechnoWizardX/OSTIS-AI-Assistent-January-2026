from threading import Thread
from queue import Queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import os
from DataExchange import DataExchanger


class VoiceRecognizer:
    def __init__(self):
        self.config = DataExchanger.get_config()

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

        # vosk
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)

        # поток
        self.listening_status = False
        self.thread = None

        # Аудио очередь
        self.audio_queue = Queue()

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
            return self.replace_number_in_phrase(self.text_queue.get())
        return None

    def replace_number_in_phrase(self, text):
        numbers = {
        "ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5,
        "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10,
        "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14,
        "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18,
        "девятнадцать": 19,
        "двадцать": 20, "тридцать": 30, "сорок": 40,
        "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
        "восемьдесят": 80, "девяносто": 90,
        "сто": 100
        }
        words = text.split()
        result_words = []

        for word in words:
            if word in numbers:
                result_words.append(str(numbers[word]))
            else:
                result_words.append(word)

        return " ".join(result_words)

    def get_error(self):
        if not self.error_queue.empty():
            return self.error_queue.get()
        return None

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

        except Exception as e:
            self.error_queue.put(f"VoiceRecognizer error: {e}")
            self.listening_status = False
