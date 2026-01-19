from threading import Thread
from queue import Queue
import speech_recognition as sr
from DataExchange import DataExchange
from datetime import datetime


class VoiceRecognizer():
    def __init__(self):
        self.confing = DataExchange.get_config()

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.listening_status = False
        self.thread = None
        self.text_queue = Queue()
        self.error_queue = Queue()  # Очередь для ошибок, чтобы передавать в основной поток

    def start_recording(self):
        if not self.listening_status:
            self.listening_status = True

            self.thread = Thread(target=self._recognize_voice)
            self.thread.start()

    def stop_recording(self):
        self.listening_status = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.1) 

    def get_text(self):
        if not self.text_queue.empty():
            return self.text_queue.get()
        return None

    def get_error(self):
        if not self.error_queue.empty():
            return self.error_queue.get()
        return None

    def _recognize_voice(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)  # Увеличиваем калибровку для лучшего шума
            self.recognizer.dynamic_energy_threshold = True  # Автоматическая настройка чувствительности
            self.recognizer.energy_threshold = 200  # Снижаем порог для тихой речи
            self.recognizer.pause_threshold = 1.5  # Увеличиваем паузу для длинных фраз
            
            while self.listening_status:
                try:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=10)  # Увеличиваем лимиты для длинных фраз
                    text = self.recognizer.recognize_google(audio, language="ru-RU")

                    self.text_queue.put(text)

                    DataExchange.update_chat_history(text, "user", datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"))
                    DataExchange.send_to_nika(text)

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    self.error_queue.put("Ошибка подключения к интернету или сервиса распознавания.")  # Помещаем ошибку в очередь
                    break  # Останавливаем цикл при ошибке подключения

