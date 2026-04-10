# ============================================================
# voice.py — Распознавание речи с автозагрузкой модели Vosk
#
# Класс SpeechRecognizer для распознавания речи:
# - Запись с микрофона через sounddevice
# - Распознавание через Vosk
# - Непрерывный режим (работает постоянно)
# - Callback'и для получения результатов
# - Автозамена русских чисел на цифры
# ============================================================

import os
import threading
import queue
import urllib.request
import zipfile
import tempfile
import shutil
import json
import time
from typing import Optional, Callable, Dict, Any

import tkinter as tk
from tkinter import ttk, messagebox

import sounddevice as sd
from vosk import Model, KaldiRecognizer


# ============================================================
# SpeechRecognizer — основной класс
# ============================================================

class SpeechRecognizer:
    """Класс распознавания речи на базе Vosk
    
    Работает постоянно в фоновом потоке.
    Текст получается через get_text() или callback.
    
    Пример:
        recognizer = SpeechRecognizer(model_path="/path/to/model")
        recognizer.start_recording()
        
        # Получаем текст когда нужно
        while True:
            text = recognizer.get_text()
            if text:
                print(f"Вы сказали: {text}")
            time.sleep(0.1)
    """
    
    def __init__(
        self,
        model_path: str,
        sample_rate: int = 16000,
        auto_replace_numbers: bool = True
    ):
        """Инициализация
        
        Args:
            model_path: Путь к модели Vosk
            sample_rate: Частота дискретизации (16000 Гц)
            auto_replace_numbers: Заменять числа словами
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.auto_replace_numbers = auto_replace_numbers
        
        # Словарь чисел 0-100
        self._numbers = self._build_numbers_dict()
        
        # Очереди для межпоточного обмена
        self.text_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        
        # Callback для получения результатов
        self._callback: Optional[Callable[[str], None]] = None
        
        # Состояние
        self.listening_status = False
        self.thread = None
        
        # Загружаем модель
        self.model = None
        self.recognizer = None
        self._load_model()
    
    def _build_numbers_dict(self) -> Dict[str, int]:
        """Создает словарь русских чисел 0-100"""
        numbers = {
            "ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4,
            "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
            "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
            "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
            "восемнадцать": 18, "девятнадцать": 19,
        }
        # Составные числа (20-99)
        tens = {
            "двадцать": 20, "тридцать": 30, "сорок": 40,
            "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
            "восемьдесят": 80, "девяносто": 90
        }
        for ten_name, ten_val in tens.items():
            numbers[ten_name] = ten_val
            for unit_name, unit_val in list(numbers.items()):
                if 1 <= unit_val <= 9:
                    numbers[f"{ten_name} {unit_name}"] = ten_val + unit_val
        numbers["сто"] = 100
        return numbers
    
    def _load_model(self):
        """Загружает модель и создает распознаватель"""
        if not os.path.exists(self.model_path):
            err = f"Модель не найдена: {self.model_path}"
            self.error_queue.put(err)
            return
        
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
        except Exception as e:
            self.error_queue.put(f"Ошибка загрузки модели: {e}")
    
    def on_text(self, callback: Callable[[str], None]):
        """Регистрирует callback для получения текста
        
        Args:
            callback: Функция, принимающая строку с распознанным текстом
            
        Пример:
            recognizer.on_text(lambda text: print(f"Получено: {text}"))
        """
        self._callback = callback
    
    def start_recording(self):
        """Начинает постоянную запись и распознавание
        
        Работает в фоновом потоке до вызова stop_recording()
        """
        if self.listening_status:
            return
        
        self.listening_status = True
        self.thread = threading.Thread(target=self._recognize_loop, daemon=True)
        self.thread.start()
    
    def stop_recording(self):
        """Останавливает запись"""
        self.listening_status = False
    
    def get_text(self) -> Optional[str]:
        """Получает последний распознанный текст
        
        Returns:
            Текст или None, если очередь пуста
            
        Пример:
            text = recognizer.get_text()
            if text:
                print(f"Распознано: {text}")
        """
        if not self.text_queue.empty():
            text = self.text_queue.get()
            if self.auto_replace_numbers:
                text = self._replace_numbers(text)
            return text
        return None
    
    def get_error(self) -> Optional[str]:
        """Получает последнюю ошибку"""
        if not self.error_queue.empty():
            return self.error_queue.get()
        return None
    
    def _replace_numbers(self, text: str) -> str:
        """Заменяет русские числа на цифры (0-100)"""
        words = text.split()
        result = []
        i = 0
        while i < len(words):
            # Проверяем пару слов (например "двадцать один")
            if i + 1 < len(words):
                two = f"{words[i]} {words[i+1]}"
                if two in self._numbers:
                    result.append(str(self._numbers[two]))
                    i += 2
                    continue
            # Проверяем одиночное слово
            if words[i] in self._numbers:
                result.append(str(self._numbers[words[i]]))
            else:
                result.append(words[i])
            i += 1
        return " ".join(result)
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback sounddevice: получает аудио и кладет в очередь"""
        if status:
            self.error_queue.put(str(status))
        self.audio_queue.put(bytes(indata))
    
    def _recognize_loop(self):
        """Основной цикл распознавания (в отдельном потоке)
        
        Работает постоянно, пока listening_status = True
        """
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=self._audio_callback
            ):
                while self.listening_status:
                    data = self.audio_queue.get()
                    
                    # AcceptWaveform=True значит фраза распознана
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()
                        
                        if text:
                            # Кладем текст в очередь
                            self.text_queue.put(text)
                            
                            # Вызываем callback, если установлен
                            if self._callback:
                                try:
                                    processed_text = self._replace_numbers(text) if self.auto_replace_numbers else text
                                    self._callback(processed_text)
                                except Exception as e:
                                    print(f"Callback ошибка: {e}")
                                    
        except Exception as e:
            self.error_queue.put(f"VoiceRecognizer error: {e}")
            self.listening_status = False


# ============================================================
# Автозагрузка модели
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_NAME = "vosk-model-small-ru-0.22"
MODEL_PATH = os.path.join(SAMPLES_DIR, "voice-model", MODEL_NAME)
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"


class DownloadDialog:
    """Модальное окно загрузки модели с прогресс-баром"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.complete = False
        
        self.root = tk.Tk()
        self.root.title("Загрузка модели Vosk")
        self.root.geometry("450x200")
        self.root.resizable(False, False)
        self._center_window()
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        self._build_ui()
        threading.Thread(target=self._download, daemon=True).start()
        self._poll()
        self.root.mainloop()
    
    def _center_window(self):
        w, h = 450, 200
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
    
    def _build_ui(self):
        tk.Label(self.root, text="Загрузка голосовой модели",
                 font=("Arial", 12, "bold")).pack(pady=(15, 5))
        tk.Label(self.root, text=f"Модель '{MODEL_NAME}' не найдена.\nНачинается загрузка...",
                 font=("Arial", 10)).pack()
        self.progress = ttk.Progressbar(self.root, mode="determinate", length=380)
        self.progress.pack(pady=10)
        self.status_lbl = tk.Label(self.root, text="Подготовка...",
                                   font=("Arial", 9), fg="gray")
        self.status_lbl.pack()
    
    def _download(self):
        """Скачивает и распаковывает модель"""
        try:
            self.queue.put(("status", "Загрузка началась..."))
            self.queue.put(("progress", 0))
            
            model_dir = os.path.join(SAMPLES_DIR, "voice-model")
            os.makedirs(model_dir, exist_ok=True)
            
            # Скачиваем ZIP
            with urllib.request.urlopen(MODEL_URL, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 64 * 1024
                tmp_zip = os.path.join(tempfile.gettempdir(), "vosk_model.zip")
                
                with open(tmp_zip, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = int((downloaded / total) * 100)
                            self.queue.put(("progress", pct))
                            self.queue.put(("status", f"Загружено: {downloaded // 1024} / {total // 1024} КБ"))
            
            # Распаковка
            self.queue.put(("status", "Распаковка..."))
            self.queue.put(("progress", 100))
            
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                root_folder = zf.namelist()[0].split("/")[0]
                tmp_extract = os.path.join(tempfile.gettempdir(), "vosk_extract")
                if os.path.exists(tmp_extract):
                    shutil.rmtree(tmp_extract)
                zf.extractall(tmp_extract)
            
            src = os.path.join(tmp_extract, root_folder)
            if not os.path.exists(src):
                raise FileNotFoundError(f"Модель не найдена в архиве: {src}")
            
            # Перемещаем модель
            if os.path.exists(MODEL_PATH):
                shutil.rmtree(MODEL_PATH)
            shutil.move(src, MODEL_PATH)
            
            # Уборка
            shutil.rmtree(tmp_extract, ignore_errors=True)
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)
            
            self.queue.put(("done", True))
            
        except Exception as e:
            self.queue.put(("error", str(e)))
    
    def _poll(self):
        """Опрашивает очередь и обновляет UI"""
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == "status":
                    self.status_lbl.config(text=data)
                elif msg_type == "progress":
                    self.progress.config(value=data)
                elif msg_type == "done":
                    self.complete = True
                    self.root.after(100, lambda: (
                        messagebox.showinfo("Готово", f"Модель загружена!\n{MODEL_PATH}"),
                        self.root.destroy()
                    ))
                    return
                elif msg_type == "error":
                    self.root.after(100, lambda: (
                        messagebox.showerror("Ошибка", f"Не удалось загрузить модель:\n{data}"),
                        self.root.destroy()
                    ))
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


def download_model() -> bool:
    """Проверяет/загружает модель. Returns: True/False"""
    if os.path.exists(MODEL_PATH):
        print(f"Модель найдена: {MODEL_PATH}")
        return True
    print(f"Модель не найдена, начинаю загрузку...")
    dlg = DownloadDialog()
    return dlg.complete


# ============================================================
# Глобальный объект — удобные функции для вызова из других файлов
# ============================================================

# Глобальный распознаватель (создается при инициализации)
voice_recognizer: Optional[SpeechRecognizer] = None


def init_voice(model_path: str = MODEL_PATH):
    """Инициализация голосового помощника (вызвать один раз при старте)
    
    Args:
        model_path: Путь к модели Vosk (по умолчанию MODEL_PATH)
    """
    global voice_recognizer
    
    voice_recognizer = SpeechRecognizer(model_path=model_path)
    voice_recognizer.start_recording()
    print("Голосовой помощник запущен")


def get_voice_text() -> Optional[str]:
    """Получить распознанный текст из любого места программы
    
    Returns:
        Текст или None, если ничего не распознано
    
    Пример:
        text = get_voice_text()
        if text:
            print(f"Вы сказали: {text}")
    """
    if voice_recognizer:
        return voice_recognizer.get_text()
    return None


def stop_voice():
    """Остановить голосовой помощник"""
    global voice_recognizer
    if voice_recognizer:
        voice_recognizer.stop_recording()
        print("Голосовой помощник остановлен")


def set_voice_callback(callback: Callable[[str], None]):
    """Установить callback для автоматического получения текста
    
    Args:
        callback: Функция, принимающая текст
        
    Пример:
        def on_text(text):
            print(f"Голос: {text}")
        
        set_voice_callback(on_text)
    """
    if voice_recognizer:
        voice_recognizer.on_text(callback)


# ============================================================
# Пример использования
# ============================================================

if __name__ == "__main__":
    print(f"Путь к модели: {MODEL_PATH}")

    if not download_model():
        print("Модель не загруена.")
        exit()

    print("\n" + "="*60)
    print("РАСПОЗНАВАНИЕ РЕЧИ (постоянный режим)")
    print("="*60)

    # Инициализация через глобальные функции
    init_voice()

    # Пример использования
    print("\nРаспознавание запущено (говорите 'выход' для остановки)...")
    try:
        while True:
            # ПОЛУЧАЕМ ТЕКСТ ЗДЕСЬ
            text = get_voice_text()
            
            if text:
                print(f"→ Вы сказали: {text}")
                
                if "выход" in text.lower():
                    print("Остановка...")
                    break
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        stop_voice()
