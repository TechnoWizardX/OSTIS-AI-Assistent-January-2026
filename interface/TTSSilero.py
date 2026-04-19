"""
Silero TTS v5 — обёртка для синтеза речи на русском языке (модель v5_4_ru).

Особенности v5_4_ru:
- Автоматическая расстановка ударений и работа с омографами
- Поддержка SSML
- Скорость в 1.5-2 раза выше v4
- Качество звука близкое к живому голосу

Модели хранятся локально в папке проекта ./models/silero/

Пример:
    from TTSSilero import SileroTTS
    tts = SileroTTS(voice="xenia", quality="high")
    tts.speak("Очень длинный текст...")  # автоматически разобьётся на части
"""
from BasicUtils import BasicUtils
import os
import sys
import tempfile
import threading
import time
import re
from pathlib import Path
from typing import Optional, Callable, List, Dict, Tuple
from collections import OrderedDict
from queue import Queue

import torch
import sounddevice as sd
import numpy as np

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

# Доступные русские голоса Silero v5
RUSSIAN_VOICES = ["xenia", "baya", "kseniya", "aidar", "eugene"]

# Идентификатор модели (v5_4_ru — актуальная русская модель)
MODEL_ID = "v5_5_ru"

# Настройки по умолчанию
DEFAULT_VOICE = "xenia"  # Лучший женский голос
DEFAULT_SAMPLE_RATE = 48000  # v5_4_ru работает с 48 кГц
DEFAULT_SPEED = 1.0
DEFAULT_QUALITY = "high"  # high, medium, low

# Ограничения для разбиения текста
MAX_CHUNK_LENGTH = 500  # максимальная длина одного фрагмента в символах
MAX_SENTENCE_LENGTH = 300  # максимальная длина предложения перед принудительным разбиением

# Путь для сохранения моделей (относительно корня проекта)
MODELS_DIR = Path(__file__).parent.parent / "models" / "silero"


class SileroTTS:
    """
    Синтезатор речи на базе Silero TTS v5_4_ru с автоматическим разбиением текста.

    При первом использовании загружает модель в папку ./models/silero/
    Последующие запуски работают офлайн.

    Особенности:
    - Автоматически разбивает длинный текст на части
    - Сохраняет естественные паузы между предложениями
    - Поддерживает очередь сообщений

    Атрибуты:
        voice: имя голоса ("xenia" рекомендуется)
        sample_rate: частота дискретизации (48000)
        speed: скорость речи (0.5 - 2.0, 1.0 = норма)
        quality: качество синтеза ("high", "medium", "low")
        device: устройство ("cpu", "cuda", "auto")
        max_chunk_length: максимальная длина фрагмента текста

    Примеры:
        >>> tts = SileroTTS(voice="xenia", quality="high")
        >>> tts.speak("Очень длинный текст..." * 100)  # автоматически разобьётся
        >>> tts.speak("Короткий текст")  # синтезируется целиком
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        speed: float = DEFAULT_SPEED,
        quality: str = DEFAULT_QUALITY,
        device: str = "auto",
        cache_size: int = 50,
        max_chunk_length: int = MAX_CHUNK_LENGTH,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            voice: имя голоса ("xenia" рекомендуется)
            sample_rate: частота дискретизации (48000)
            speed: скорость речи (0.5 — 2.0, 1.0 = норма)
            quality: качество синтеза ("high" - полная обработка, "medium" - базовая, "low" - без обработки)
            device: "cpu", "cuda" или "auto" (автоопределение)
            cache_size: размер кэша аудио (0 - отключить)
            max_chunk_length: максимальная длина фрагмента текста для синтеза
            on_status: callback для отображения статуса загрузки
        """
        self.voice = voice
        self.sample_rate = sample_rate
        self.speed = speed
        self.quality = quality
        self.cache_size = cache_size
        self.max_chunk_length = max_chunk_length
        self.on_status = on_status

        # Автоопределение устройства
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self._model = None
        self._is_speaking = False
        self._stop_requested = False
        self._audio_cache: OrderedDict = OrderedDict()
        
        # Очередь для TTS сообщений
        self._tts_queue = Queue()
        self._tts_processing = False
        self._tts_worker_running = True
        self._tts_worker_thread = None
        
        # Настройка обработки текста
        self._setup_text_processing()
        
        # Установка пути для моделей
        self._setup_models_path()
        
        # Загрузка модели
        self._load_model()
        
        # Запуск фонового воркера для очереди
        self._start_tts_worker()
        
        BasicUtils.logger("TTSSilero", "INFO", 
                         f"Инициализирован v5_4_ru: голос={voice}, качество={quality}, устройство={self.device}, "
                         f"макс. длина фрагмента={max_chunk_length}, путь моделей={MODELS_DIR}")

    def _setup_models_path(self):
        """Настраивает путь для хранения моделей Silero"""
        # Создаём директорию для моделей, если её нет
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Устанавливаем переменную окружения для torch.hub
        os.environ['TORCH_HOME'] = str(MODELS_DIR.parent.parent)
        
        # Настраиваем путь для кэша torch.hub
        torch.hub.set_dir(str(MODELS_DIR.parent.parent))
        
        BasicUtils.logger("TTSSilero", "INFO", f"Директория моделей: {MODELS_DIR}")

    def _start_tts_worker(self):
        """Запускает фоновый воркер для обработки очереди TTS"""
        self._tts_worker_running = True
        self._tts_worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_worker_thread.start()
        BasicUtils.logger("TTSSilero", "INFO", "Фоновый TTS воркер запущен")

    def _tts_worker(self):
        """Фоновый воркер для обработки очереди сообщений"""
        while self._tts_worker_running:
            try:
                if not self._tts_processing and not self._tts_queue.empty():
                    # Получаем сообщение из очереди
                    text, voice, speed, callback = self._tts_queue.get()
                    
                    self._tts_processing = True
                    
                    BasicUtils.logger("TTSSilero", "INFO", f"Начинаем воспроизведение из очереди: {text[:50]}...")
                    
                    # Воспроизводим с блокировкой
                    self._speak_sync(text, voice, speed)
                    
                    # Вызываем callback если есть
                    if callback:
                        try:
                            callback()
                        except Exception as e:
                            BasicUtils.logger("TTSSilero", "WARNING", f"Ошибка в callback: {e}")
                    
                    self._tts_processing = False
                
                time.sleep(0.05)  # Небольшая пауза для снижения нагрузки CPU
                
            except Exception as e:
                BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка в TTS воркере: {e}")
                self._tts_processing = False

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """
        Разбивает длинный текст на части для обхода ограничений модели
        
        Стратегия разбиения:
        1. Сначала разбиваем по предложениям (по .!?;:\n)
        2. Если предложение слишком длинное, разбиваем по запятым
        3. Если всё ещё длинное, разбиваем по словам
        
        Args:
            text: исходный текст
            
        Returns:
            список фрагментов текста для синтеза
        """
        if not text or not text.strip():
            return []
        
        # Если текст короткий, возвращаем как есть
        if len(text) <= self.max_chunk_length:
            return [text.strip()]
        
        chunks = []
        
        # Шаг 1: Разбиваем по предложениям
        sentence_delimiters = r'(?<=[.!?;:\n])\s+'
        sentences = re.split(sentence_delimiters, text)
        
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Если предложение влазит в текущий чанк
            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_length:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                # Сохраняем текущий чанк если он не пустой
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Если предложение само по себе слишком длинное, разбиваем его
                if len(sentence) > self.max_chunk_length:
                    sub_chunks = self._split_long_sentence(sentence)
                    chunks.extend(sub_chunks)
                else:
                    current_chunk = sentence
        
        # Добавляем последний чанк
        if current_chunk:
            chunks.append(current_chunk)
        
        # Логируем результат разбиения
        if len(chunks) > 1:
            BasicUtils.logger("TTSSilero", "INFO", f"Текст разбит на {len(chunks)} частей (макс. длина {self.max_chunk_length})")
            for i, chunk in enumerate(chunks):
                BasicUtils.logger("TTSSilero", "DEBUG", f"  Часть {i+1}: {len(chunk)} символов - {chunk[:50]}...")
        
        return chunks
    
    def _split_long_sentence(self, sentence: str) -> List[str]:
        """
        Разбивает очень длинное предложение на части
        
        Args:
            sentence: длинное предложение
            
        Returns:
            список фрагментов
        """
        chunks = []
        
        # Шаг 1: Пробуем разбить по запятым
        comma_parts = re.split(r'(?<=,)\s+', sentence)
        
        if len(comma_parts) > 1:
            current = ""
            for part in comma_parts:
                if len(current) + len(part) + 2 <= self.max_chunk_length:
                    if current:
                        current += " " + part
                    else:
                        current = part
                else:
                    if current:
                        chunks.append(current)
                        current = part
                    else:
                        # Часть сама по себе длинная, разбиваем дальше
                        if len(part) > self.max_chunk_length:
                            chunks.extend(self._split_by_words(part))
                        else:
                            current = part
            
            if current:
                chunks.append(current)
            
            return chunks
        
        # Шаг 2: Разбиваем по словам
        return self._split_by_words(sentence)
    
    def _split_by_words(self, text: str) -> List[str]:
        """
        Разбивает текст по словам на части заданной длины
        
        Args:
            text: текст для разбиения
            
        Returns:
            список фрагментов
        """
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            if len(current_chunk) + len(word) + 1 <= self.max_chunk_length:
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    def _setup_text_processing(self):
        """Настройка обработки текста для улучшения качества синтеза"""
        
        # Базовые числа от 0 до 10
        self.base_numbers = {
            0: 'ноль', 1: 'один', 2: 'два', 3: 'три', 4: 'четыре',
            5: 'пять', 6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять',
            10: 'десять'
        }
        
        # Числа от 11 до 19
        self.teen_numbers = {
            11: 'одиннадцать', 12: 'двенадцать', 13: 'тринадцать',
            14: 'четырнадцать', 15: 'пятнадцать', 16: 'шестнадцать',
            17: 'семнадцать', 18: 'восемнадцать', 19: 'девятнадцать'
        }
        
        # Десятки
        self.tens = {
            20: 'двадцать', 30: 'тридцать', 40: 'сорок',
            50: 'пятьдесят', 60: 'шестьдесят', 70: 'семьдесят',
            80: 'восемьдесят', 90: 'девяносто'
        }
        
        # Сотни
        self.hundreds = {
            100: 'сто', 200: 'двести', 300: 'триста',
            400: 'четыреста', 500: 'пятьсот', 600: 'шестьсот',
            700: 'семьсот', 800: 'восемьсот', 900: 'девятьсот'
        }
        
        # Разряды чисел (тысячи, миллионы и т.д.)
        self.magnitudes = [
            (1000, 'тысяча', 'тысячи', 'тысяч'),
            (1000000, 'миллион', 'миллиона', 'миллионов'),
            (1000000000, 'миллиард', 'миллиарда', 'миллиардов'),
            (1000000000000, 'триллион', 'триллиона', 'триллионов'),
            (1000000000000000, 'квадриллион', 'квадриллиона', 'квадриллионов'),
        ]
        
        # Аббревиатуры и сокращения
        self.abbreviations = {
            'т.д.': 'так далее',
            'т.п.': 'такое прочее',
            'т.е.': 'то есть',
            'и.т.д.': 'и так далее',
            'и.т.п.': 'и тому подобное',
            'т.к.': 'потому что',
            'напр.': 'например',
            'т.н.': 'так называемый',
            'др.': 'другие',
            'г.': 'год',
            'гг.': 'годы',
            'см.': 'смотри',
            'стр.': 'страница',
            'руб.': 'рублей',
            'коп.': 'копеек',
            'м.': 'метров',
            'км.': 'километров',
            'кг.': 'килограммов',
            'г.': 'граммов',
            'л.': 'литров',
            'сек.': 'секунд',
            'мин.': 'минут',
            'ч.': 'часов',
            'сут.': 'суток',
            'нед.': 'недель',
            'мес.': 'месяцев',
            'год.': 'годов',
        }
        
        # Знаки препинания с паузами
        self.punctuation_pauses = {
            '.': ' . ', '!': ' ! ', '?': ' ? ', ';': ' ; ',
            ':': ' : ', ',': ' , ', '(': ' ( ', ')': ' ) ',
        }

    def _convert_number_to_words(self, num: int) -> str:
        """
        Преобразует число в слова на русском языке
        
        Args:
            num: число для преобразования
            
        Returns:
            строковое представление числа словами
        """
        if num < 0:
            return f"минус {self._convert_number_to_words(-num)}"
        
        if num == 0:
            return self.base_numbers[0]
        
        # Обработка до 1000
        if num < 1000:
            return self._convert_less_than_thousand(num)
        
        # Обработка больших чисел
        result_parts = []
        
        for magnitude, single, few, many in self.magnitudes:
            if num >= magnitude:
                count = num // magnitude
                remainder = num % magnitude
                
                # Преобразуем количество
                count_words = self._convert_less_than_thousand(count)
                
                # Выбираем правильную форму слова
                if count % 10 == 1 and count % 100 != 11:
                    magnitude_word = single
                elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                    magnitude_word = few
                else:
                    magnitude_word = many
                
                result_parts.append(f"{count_words} {magnitude_word}")
                num = remainder
        
        # Добавляем остаток меньше 1000
        if num > 0:
            result_parts.append(self._convert_less_than_thousand(num))
        
        return ' '.join(result_parts)
    
    def _convert_less_than_thousand(self, num: int) -> str:
        """
        Преобразует число меньше 1000 в слова
        
        Args:
            num: число от 0 до 999
            
        Returns:
            строковое представление числа словами
        """
        if num == 0:
            return ""
        
        parts = []
        
        # Сотни
        if num >= 100:
            hundreds_val = (num // 100) * 100
            if hundreds_val in self.hundreds:
                parts.append(self.hundreds[hundreds_val])
            num %= 100
        
        # Десятки и единицы
        if num >= 20:
            tens_val = (num // 10) * 10
            if tens_val in self.tens:
                parts.append(self.tens[tens_val])
            num %= 10
        
        if 11 <= num <= 19:
            parts.append(self.teen_numbers[num])
            num = 0
        elif num >= 1:
            parts.append(self.base_numbers[num])
        
        return ' '.join(parts)
    
    def _process_numbers_in_text(self, text: str) -> str:
        """
        Обрабатывает числа в тексте, заменяя их на слова
        
        Args:
            text: текст с числами
            
        Returns:
            текст с числами, замененными на слова
        """
        def replace_number(match):
            num_str = match.group(0)
            # Убираем ведущие нули
            num_str = num_str.lstrip('0')
            if not num_str:
                return 'ноль'
            
            try:
                num = int(num_str)
                # Ограничиваем максимальное число для производительности
                if num > 10**15:  # Больше квадриллиона
                    return num_str
                return self._convert_number_to_words(num)
            except ValueError:
                return num_str
        
        # Находим все числа в тексте
        pattern = r'\b\d+(?:\.\d+)?\b'
        text = re.sub(pattern, replace_number, text)
        
        return text
    
    def _process_ordinal_numbers(self, text: str) -> str:
        """
        Обрабатывает порядковые числительные (1-й, 2-й и т.д.)
        
        Args:
            text: текст с порядковыми числительными
            
        Returns:
            текст с замененными порядковыми числительными
        """
        ordinal_map = {
            '1-й': 'первый', '2-й': 'второй', '3-й': 'третий',
            '4-й': 'четвертый', '5-й': 'пятый', '6-й': 'шестой',
            '7-й': 'седьмой', '8-й': 'восьмой', '9-й': 'девятый',
            '10-й': 'десятый', '11-й': 'одиннадцатый', '12-й': 'двенадцатый',
            '13-й': 'тринадцатый', '14-й': 'четырнадцатый', '15-й': 'пятнадцатый',
            '16-й': 'шестнадцатый', '17-й': 'семнадцатый', '18-й': 'восемнадцатый',
            '19-й': 'девятнадцатый', '20-й': 'двадцатый'
        }
        
        for num_str, word in ordinal_map.items():
            text = text.replace(num_str, word)
        
        # Обработка составных порядковых (21-й, 32-й и т.д.)
        pattern = r'(\d+)-й'
        def replace_composite(match):
            num = int(match.group(1))
            if num <= 20:
                return ordinal_map.get(f"{num}-й", f"{num}-й")
            # Для больших чисел
            tens = num // 10
            units = num % 10
            if units == 0:
                tens_word = self.tens.get(tens * 10, '')
                return f"{tens_word}й"
            elif 1 <= units <= 9:
                tens_word = self.tens.get(tens * 10, '')
                units_word = self.base_numbers.get(units, '')
                return f"{tens_word} {units_word}й"
            return match.group(0)
        
        text = re.sub(pattern, replace_composite, text)
        return text

    def _log_status(self, message: str):
        """Логирование статуса"""
        BasicUtils.logger("TTSSilero", "INFO", message)
        if self.on_status:
            self.on_status(message)

    def _load_model(self):
        """Загружает модель Silero TTS v5_4_ru через torch.hub"""
        if self._model is not None:
            return

        self._log_status(f"Загрузка модели Silero TTS {MODEL_ID} в {MODELS_DIR}...")
        
        try:
            # Устанавливаем путь для загрузки модели
            torch.hub.set_dir(str(MODELS_DIR.parent.parent))
            
            # Загрузка модели v5_4_ru
            result = torch.hub.load(
                repo_or_dir="snakers4/silero-models",
                model="silero_tts",
                language="ru",
                speaker=MODEL_ID,
                trust_repo=True,
            )
            
            # v5_4_ru возвращает кортеж из 2 элементов: (model, sample_rate)
            if isinstance(result, tuple):
                if len(result) == 2:
                    self._model, self.sample_rate = result
                elif len(result) == 3:
                    # Для обратной совместимости с v4
                    self._model, _, self.sample_rate = result
                else:
                    raise ValueError(f"Неожиданный формат возвращаемых данных: {len(result)} элементов")
            else:
                self._model = result
            
            # Убеждаемся, что sample_rate корректный
            if not isinstance(self.sample_rate, int):
                self.sample_rate = DEFAULT_SAMPLE_RATE
            
            # Перемещаем модель на устройство
            if hasattr(self._model, 'to'):
                self._model.to(self.device)
            
            self._log_status(f"Модель Silero TTS {MODEL_ID} успешно загружена (частота: {self.sample_rate} Гц)")
            
        except Exception as e:
            BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка загрузки модели: {e}")
            import traceback
            traceback.print_exc()
            raise

    def preprocess_text(self, text: str) -> str:
        """
        Предобработка текста для улучшения качества синтеза
        
        Args:
            text: исходный текст
            
        Returns:
            обработанный текст
        """
        if not text or not text.strip():
            return text
        
        original_text = text
        
        # 1. Замена аббревиатур
        for abbr, full in self.abbreviations.items():
            text = text.replace(abbr, full)
            text = text.replace(abbr.upper(), full)
            text = text.replace(abbr.capitalize(), full)
        
        # 2. Обработка порядковых числительных
        text = self._process_ordinal_numbers(text)
        
        # 3. Обработка чисел
        text = self._process_numbers_in_text(text)
        
        # 4. Добавление пауз для знаков препинания
        for punct, replacement in self.punctuation_pauses.items():
            text = text.replace(punct, replacement)
        
        # 5. Нормализация кавычек и скобок
        text = text.replace('«', '"').replace('»', '"')
        text = text.replace('“', '"').replace('”', '"')
        
        # 6. Удаление лишних пробелов
        text = re.sub(r'\s+', ' ', text)
        
        # 7. Обработка специальных символов
        text = text.replace('\n', '. ')
        text = text.replace('\t', ' ')
        
        # 8. Добавление точки в конце если нет
        if text and text[-1] not in '.!?':
            text += '.'
        
        # Логирование изменений
        if original_text != text:
            BasicUtils.logger("TTSSilero", "DEBUG", f"Текст обработан: {original_text[:50]}... -> {text[:50]}...")
        
        return text.strip()

    def _change_speed(self, audio: torch.Tensor, speed: float) -> torch.Tensor:
        """
        Изменение скорости аудио с сохранением высоты тона
        
        Args:
            audio: аудиоданные
            speed: коэффициент скорости (0.5-2.0)
            
        Returns:
            измененное аудио
        """
        if speed == 1.0 or self.quality == "low":
            return audio
        
        try:
            # Пытаемся использовать librosa для качественного изменения
            import librosa
            audio_np = audio.cpu().numpy()
            # time_stretch сохраняет высоту тона
            audio_changed = librosa.effects.time_stretch(audio_np, rate=speed)
            return torch.from_numpy(audio_changed)
        except ImportError:
            # Fallback: простое изменение скорости
            if self.quality == "high":
                # Интерполяция для лучшего качества
                old_len = len(audio)
                new_len = int(old_len / speed)
                indices = torch.linspace(0, old_len - 1, new_len)
                indices = torch.floor(indices).long()
                indices = torch.clamp(indices, 0, old_len - 1)
                return audio[indices]
            else:
                # Простой ресемплинг
                indices = torch.arange(0, len(audio), speed)
                return audio[torch.floor(indices).long()]

    def _post_process_audio(self, audio: torch.Tensor) -> torch.Tensor:
        """
        Пост-обработка аудио для улучшения качества
        
        Args:
            audio: аудиоданные
            
        Returns:
            обработанное аудио
        """
        if self.quality == "low":
            return audio
        
        try:
            # Мягкое ограничение для удаления кликов
            audio = torch.clamp(audio, -0.99, 0.99)
            
            # Для высокого качества применяем частотную коррекцию
            if self.quality == "high" and hasattr(torch, 'fft'):
                # Переводим в частотную область
                fft = torch.fft.rfft(audio)
                freq = torch.fft.rfftfreq(len(audio), d=1/self.sample_rate)
                
                # Частотная коррекция для улучшения разборчивости
                boost = torch.ones_like(fft)
                # Подъем высоких частот (четкость)
                boost[freq > 2000] = 1.1
                # Небольшое снижение низких частот
                boost[freq < 200] = 0.95
                # Плавный переход
                mask = (freq >= 200) & (freq <= 2000)
                boost[mask] = 1.0
                
                # Применение фильтра
                audio = torch.fft.irfft(fft * boost)
                
                # Повторное ограничение
                audio = torch.clamp(audio, -0.99, 0.99)
            
            return audio
        except Exception as e:
            BasicUtils.logger("TTSSilero", "WARNING", f"Ошибка пост-обработки: {e}")
            return audio

    def _normalize_volume(self, audio: torch.Tensor, target_db: float = -20.0) -> torch.Tensor:
        """
        Нормализация громкости аудио
        
        Args:
            audio: аудиоданные
            target_db: целевая громкость в dB
            
        Returns:
            нормализованное аудио
        """
        if self.quality == "low":
            return audio
        
        try:
            # RMS нормализация
            rms = torch.sqrt(torch.mean(audio ** 2))
            if rms > 0:
                target_rms = 10 ** (target_db / 20)
                audio = audio * (target_rms / rms)
            
            # Ограничение пиков
            max_val = torch.max(torch.abs(audio))
            if max_val > 0.95:
                audio = audio * (0.95 / max_val)
            
            return audio
        except Exception as e:
            BasicUtils.logger("TTSSilero", "WARNING", f"Ошибка нормализации: {e}")
            return audio

    def _synthesize_single_chunk(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> torch.Tensor:
        """
        Синтезирует один фрагмент текста без разбиения и кэширования
        
        Args:
            text: текст для синтеза (должен быть коротким)
            voice: имя голоса
            speed: скорость речи
            
        Returns:
            torch.Tensor с аудиоданными
        """
        if self._model is None:
            self._load_model()

        v = voice if voice is not None else self.voice
        s = speed if speed is not None else self.speed
        
        # Предобработка текста
        processed_text = self.preprocess_text(text)
        
        # Синтез аудио с поддержкой возможностей v5_4_ru
        audio = self._model.apply_tts(
            text=processed_text,
            speaker=v,
            sample_rate=self.sample_rate,
            put_accent=True,      # Ударения в обычных словах
            put_yo=True,          # Расстановка буквы ё
        )
        
        # Изменение скорости
        if s != 1.0:
            audio = self._change_speed(audio, s)
        
        return audio

    def _synthesize_with_chunks(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> List[torch.Tensor]:
        """
        Синтезирует длинный текст, разбивая на части
        
        Args:
            text: текст для синтеза
            voice: имя голоса
            speed: скорость речи
            
        Returns:
            список аудиофрагментов
        """
        chunks = self._split_text_into_chunks(text)
        audio_parts = []
        
        for i, chunk in enumerate(chunks):
            BasicUtils.logger("TTSSilero", "DEBUG", f"Синтез части {i+1}/{len(chunks)}: {len(chunk)} символов")
            
            # Проверяем кэш для этого фрагмента
            v = voice if voice is not None else self.voice
            s = speed if speed is not None else self.speed
            cache_key = f"{chunk}_{v}_{s}"
            
            if self.cache_size > 0 and cache_key in self._audio_cache:
                BasicUtils.logger("TTSSilero", "DEBUG", f"Использован кэш для части {i+1}")
                audio = self._audio_cache[cache_key]
            else:
                audio = self._synthesize_single_chunk(chunk, voice, speed)
                
                # Пост-обработка
                if self.quality != "low":
                    audio = self._post_process_audio(audio)
                    audio = self._normalize_volume(audio)
                
                # Сохраняем в кэш
                if self.cache_size > 0:
                    if len(self._audio_cache) >= self.cache_size:
                        self._audio_cache.popitem(last=False)
                    self._audio_cache[cache_key] = audio
            
            audio_parts.append(audio)
        
        return audio_parts

    def synthesize(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> torch.Tensor:
        """
        Синтезирует речь из текста (с автоматическим разбиением длинного текста)
        
        Args:
            text: текст для синтеза (может быть очень длинным)
            voice: имя голоса (переопределяет self.voice)
            speed: скорость речи (переопределяет self.speed)
            
        Returns:
            torch.Tensor с объединёнными аудиоданными
        """
        if not text or not text.strip():
            return torch.tensor([])
        
        # Если текст короткий, синтезируем как есть
        if len(text) <= self.max_chunk_length:
            v = voice if voice is not None else self.voice
            s = speed if speed is not None else self.speed
            cache_key = f"{text}_{v}_{s}"
            
            if self.cache_size > 0 and cache_key in self._audio_cache:
                BasicUtils.logger("TTSSilero", "DEBUG", f"Использован кэш для: {text[:50]}...")
                self._audio_cache.move_to_end(cache_key)
                return self._audio_cache[cache_key]
            
            audio = self._synthesize_single_chunk(text, voice, speed)
            
            if self.quality != "low":
                audio = self._post_process_audio(audio)
                audio = self._normalize_volume(audio)
            
            if self.cache_size > 0:
                if len(self._audio_cache) >= self.cache_size:
                    self._audio_cache.popitem(last=False)
                self._audio_cache[cache_key] = audio
            
            return audio
        
        # Для длинного текста синтезируем по частям
        audio_parts = self._synthesize_with_chunks(text, voice, speed)
        
        # Объединяем все аудиофрагменты с небольшой паузой между ними
        if not audio_parts:
            return torch.tensor([])
        
        # Создаём тишину для паузы между частями (0.3 секунды)
        silence_length = int(0.3 * self.sample_rate)
        silence = torch.zeros(silence_length)
        
        # Объединяем
        combined = audio_parts[0]
        for i in range(1, len(audio_parts)):
            combined = torch.cat([combined, silence, audio_parts[i]])
        
        BasicUtils.logger("TTSSilero", "INFO", f"Объединено {len(audio_parts)} аудиофрагментов в {len(combined)/self.sample_rate:.1f} сек")
        
        return combined

    def _speak_sync(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None):
        """
        Синхронное воспроизведение текста (для фонового потока)
        
        Args:
            text: текст для произнесения
            voice: имя голоса
            speed: скорость речи
        """
        if not text or not text.strip():
            return
        
        self._is_speaking = True
        self._stop_requested = False

        try:
            # Синтез аудио (с автоматическим разбиением длинного текста)
            audio = self.synthesize(text, voice, speed)
            
            if len(audio) == 0:
                return
            
            # Конвертация в numpy для sounddevice
            audio_np = audio.cpu().numpy()
            
            # Воспроизведение
            sd.play(audio_np, self.sample_rate)
            
            # Ожидание окончания воспроизведения
            while sd.get_stream().active and not self._stop_requested:
                time.sleep(0.01)
            
            if self._stop_requested:
                sd.stop()
                BasicUtils.logger("TTSSilero", "INFO", "Воспроизведение прервано")
                
        except Exception as e:
            BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка воспроизведения: {e}")
        finally:
            self._is_speaking = False
            self._stop_requested = False

    def speak(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None, block: bool = False):
        """
        Воспроизводит текст вслух с автоматическим разбиением длинного текста.
        
        Длинный текст (>max_chunk_length символов) автоматически разбивается на части,
        которые синтезируются последовательно с небольшими паузами между ними.
        
        Args:
            text: текст для произнесения (может быть очень длинным)
            voice: имя голоса (переопределяет self.voice)
            speed: скорость речи (переопределяет self.speed)
            block: блокировать поток до окончания (True) или запустить в фоне (False)
        """
        if not text or not text.strip():
            return
        
        v = voice if voice is not None else self.voice
        s = speed if speed is not None else self.speed
        
        # Логируем информацию о тексте
        text_len = len(text)
        if text_len > self.max_chunk_length:
            chunks_count = len(self._split_text_into_chunks(text))
            BasicUtils.logger("TTSSilero", "INFO", 
                             f"Длинный текст ({text_len} символов) будет разбит на ~{chunks_count} частей")
        
        if block:
            self._speak_sync(text, v, s)
        else:
            # Добавляем в очередь для фонового воспроизведения
            self._tts_queue.put((text, v, s, None))
            BasicUtils.logger("TTSSilero", "INFO", f"Текст добавлен в очередь: {text[:50]}...")

    def speak_async(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None, callback: Optional[Callable] = None):
        """
        Асинхронное воспроизведение с callback по окончании
        
        Args:
            text: текст для произнесения
            voice: имя голоса
            speed: скорость речи
            callback: функция, вызываемая после завершения воспроизведения
        """
        if not text or not text.strip():
            if callback:
                callback()
            return
        
        v = voice if voice is not None else self.voice
        s = speed if speed is not None else self.speed
        
        self._tts_queue.put((text, v, s, callback))
        BasicUtils.logger("TTSSilero", "INFO", f"Текст добавлен в очередь (async): {text[:50]}...")

    def stop(self):
        """Останавливает текущее воспроизведение и очищает очередь."""
        if self._is_speaking:
            self._stop_requested = True
            sd.stop()
            BasicUtils.logger("TTSSilero", "INFO", "Остановка воспроизведения")
        
        # Очищаем очередь
        while not self._tts_queue.empty():
            try:
                self._tts_queue.get_nowait()
            except:
                break
        BasicUtils.logger("TTSSilero", "INFO", "Очередь TTS очищена")

    def clear_cache(self):
        """Очищает кэш аудио."""
        self._audio_cache.clear()
        BasicUtils.logger("TTSSilero", "INFO", "Кэш аудио очищен")

    @property
    def is_speaking(self) -> bool:
        """Проверяет, идёт ли воспроизведение."""
        return self._is_speaking

    @property
    def queue_size(self) -> int:
        """Возвращает размер очереди TTS."""
        return self._tts_queue.qsize()

    def available_voices(self) -> List[str]:
        """Возвращает список доступных русских голосов."""
        return RUSSIAN_VOICES.copy()

    def get_best_voice(self) -> str:
        """Возвращает рекомендуемый голос для лучшего качества."""
        return "xenia"

    def save_wav(self, text: str, filepath: str, voice: Optional[str] = None, speed: Optional[float] = None):
        """
        Сохраняет синтезированную речь в WAV-файл.
        
        Args:
            text: текст (может быть длинным)
            filepath: путь к файлу
            voice: имя голоса
            speed: скорость речи
        """
        audio = self.synthesize(text, voice, speed)

        try:
            import scipy.io.wavfile as wavfile
            # Конвертируем в int16 для WAV
            audio_int16 = (audio.cpu().numpy() * 32767).astype(np.int16)
            wavfile.write(filepath, self.sample_rate, audio_int16)
            BasicUtils.logger("TTSSilero", "INFO", f"Файл сохранён: {filepath}")
        except ImportError:
            import torchaudio
            torchaudio.save(
                filepath,
                audio.unsqueeze(0).cpu(),
                self.sample_rate,
            )
            BasicUtils.logger("TTSSilero", "INFO", f"Файл сохранён: {filepath}")

    def get_cache_info(self) -> Dict:
        """
        Возвращает информацию о кэше.
        
        Returns:
            словарь с информацией о кэше
        """
        return {
            "cache_size": len(self._audio_cache),
            "max_cache_size": self.cache_size,
            "voices": self.available_voices(),
            "current_voice": self.voice,
            "quality": self.quality,
            "device": self.device,
            "model": MODEL_ID,
            "models_path": str(MODELS_DIR),
            "max_chunk_length": self.max_chunk_length,
            "queue_size": self.queue_size
        }

    def cleanup(self):
        """Очистка ресурсов при завершении"""
        BasicUtils.logger("TTSSilero", "INFO", "Очистка ресурсов...")
        self._tts_worker_running = False
        self.stop()
        
        if self._tts_worker_thread and self._tts_worker_thread.is_alive():
            self._tts_worker_thread.join(timeout=1.0)


# ============================================================
# КЛАСС ДЛЯ ПРОСТОГО ИСПОЛЬЗОВАНИЯ (СОВМЕСТИМОСТЬ)
# ============================================================

# Глобальный экземпляр для простого использования
_default_tts = None


def get_default_tts() -> SileroTTS:
    """Возвращает глобальный экземпляр TTS"""
    global _default_tts
    if _default_tts is None:
        _default_tts = SileroTTS(quality="high")
    return _default_tts


def speak(text: str, voice: Optional[str] = None, block: bool = False):
    """
    Простая функция для быстрого воспроизведения текста.
    
    Args:
        text: текст для произнесения (может быть очень длинным)
        voice: имя голоса (опционально)
        block: блокировать поток (False - фоновое воспроизведение)
    """
    tts = get_default_tts()
    tts.speak(text, voice=voice, block=block)


def speak_async(text: str, voice: Optional[str] = None, callback: Optional[Callable] = None):
    """
    Асинхронное воспроизведение текста с callback.
    
    Args:
        text: текст для произнесения
        voice: имя голоса
        callback: функция, вызываемая после завершения
    """
    tts = get_default_tts()
    tts.speak_async(text, voice=voice, callback=callback)


def stop():
    """Останавливает текущее воспроизведение"""
    tts = get_default_tts()
    tts.stop()


def cleanup():
    """Очистка ресурсов"""
    tts = get_default_tts()
    tts.cleanup()


# ============================================================
# ТЕСТ
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("Тест Silero TTS v5_4_ru")
    print("=" * 50)
    
    print(f"\nДоступные голоса: {RUSSIAN_VOICES}")
    print(f"Рекомендуемый голос: xenia")
    print(f"Модели сохраняются в: {MODELS_DIR}")
    
    # Создаем TTS
    tts = SileroTTS(voice="xenia", quality="high", max_chunk_length=500)
    
    # Тест короткого текста
    print("\n--- Короткий текст ---")
    tts.speak("Привет! Я обновлённый голосовой ассистент на модели v5_4_ru.", block=True)
    
    # Тест длинного текста (автоматическое разбиение)
    print("\n--- Длинный текст (автоматическое разбиение) ---")
    long_text = """
    Это очень длинный текст для проверки автоматического разбиения. 
    Модель должна самостоятельно разбить его на части, чтобы обойти ограничения по длине.
    
    Вот второе предложение. И третье предложение с числами: сто двадцать три, четыреста пятьдесят шесть.
    
    Проверка омографов: Я живу в большом замке. У меня сломался замок на двери.
    
    Проверка ударений: Мне нужна мука для пирога. Это была настоящая мука.
    
    И финальное предложение, которое завершает этот длинный тест. Тест успешно пройден!
    """
    
    print(f"Длина текста: {len(long_text)} символов")
    tts.speak(long_text, block=True)
    
    # Тест очереди сообщений
    print("\n--- Очередь сообщений ---")
    tts.speak("Первое сообщение в очереди", block=False)
    tts.speak("Второе сообщение в очереди", block=False)
    tts.speak("Третье сообщение в очереди", block=False)
    
    # Ждём завершения
    time.sleep(10)
    
    print(f"\nИнформация: {tts.get_cache_info()}")
    print("\n✅ Тест v5_4_ru завершён успешно!")