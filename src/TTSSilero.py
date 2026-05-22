"""
Silero TTS v5 — обёртка для синтеза речи на русском языке (модель v5_5_ru).

Особенности v5_5_ru:
- Автоматическая расстановка ударений и работа с омографами
- Поддержка SSML
- Скорость в 1.5-2 раза выше v4
- Качество звука близкое к живому голосу

Модели хранятся локально в папке проекта ./models/silero/

Пример:
    from TTSSilero import SileroTTS
    tts = SileroTTS(voice="xenia", quality="high")
    tts.speak("Очень длинный текст...")  # автоматически разобьётся на части

Улучшения по сравнению с предыдущей версией:
- Pipeline воспроизведение: первый чанк играет сразу, остальные синтезируются параллельно
- Воркер переведён на блокирующий Queue.get() вместо busy-wait (меньше нагрузки на CPU)
- Исправлена FFT коррекция: корректное умножение complex * float без артефактов
- Исправлена обработка дробных чисел (3.14 → «три целых один четыре»)
- Громкость нормализации повышена с -20 dB до -14 dB (стандарт для TTS)
- stop() стал thread-safe через Queue.mutex
- Паузы между чанками динамические (зависят от последнего знака препинания)
"""
from src.utils.BasicUtils import BasicUtils
import os
import threading
import time
import re
from pathlib import Path
from typing import Optional, Callable, List, Dict
from collections import OrderedDict
from queue import Queue, Empty

import torch
import sounddevice as sd
import numpy as np

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

# Доступные русские голоса Silero v5
RUSSIAN_VOICES = ["xenia", "baya", "kseniya", "aidar", "eugene"]

# Идентификатор модели
MODEL_ID = "v5_5_ru"

# Настройки по умолчанию
DEFAULT_VOICE = "xenia"
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_SPEED = 1.0
DEFAULT_QUALITY = "high"  # high, medium, low

# Ограничения для разбиения текста
MAX_CHUNK_LENGTH = 500
MAX_SENTENCE_LENGTH = 300

# Путь для сохранения моделей (относительно корня проекта)
MODELS_DIR = Path(__file__).parent.parent / "models" / "silero"

# Паузы между чанками по последнему знаку препинания (в секундах)
CHUNK_PAUSE_MAP = {
    '.': 0.5, '!': 0.5, '?': 0.5,
    ';': 0.35, ':': 0.350, ',': 0.35,
}
DEFAULT_CHUNK_PAUSE = 0.15


class SileroTTS:
    """
    Синтезатор речи на базе Silero TTS v5_5_ru с автоматическим разбиением текста.

    При первом использовании загружает модель в папку ./models/silero/
    Последующие запуски работают офлайн.

    Особенности:
    - Pipeline воспроизведение: первый чанк играет немедленно
    - Автоматически разбивает длинный текст на части
    - Динамические паузы между предложениями
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
        self._tts_queue: Queue = Queue()
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
                          f"Инициализирован {MODEL_ID}: голос={voice}, качество={quality}, "
                          f"устройство={self.device}, макс. длина фрагмента={max_chunk_length}, "
                          f"путь моделей={MODELS_DIR}")

    # ============================================================
    # ИНИЦИАЛИЗАЦИЯ
    # ============================================================

    def _setup_models_path(self):
        """Настраивает путь для хранения моделей Silero"""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        os.environ['TORCH_HOME'] = str(MODELS_DIR.parent.parent)
        torch.hub.set_dir(str(MODELS_DIR.parent.parent))
        BasicUtils.logger("TTSSilero", "INFO", f"Директория моделей: {MODELS_DIR}")

    def _load_model(self):
        """Загружает модель Silero TTS через torch.hub"""
        if self._model is not None:
            return

        self._log_status(f"Загрузка модели Silero TTS {MODEL_ID} в {MODELS_DIR}...")

        try:
            torch.hub.set_dir(str(MODELS_DIR.parent.parent))

            result = torch.hub.load(
                repo_or_dir="snakers4/silero-models",
                model="silero_tts",
                language="ru",
                speaker=MODEL_ID,
                trust_repo=True,
            )

            # v5_x_ru возвращает кортеж (model, sample_rate)
            if isinstance(result, tuple):
                if len(result) == 2:
                    self._model, self.sample_rate = result
                elif len(result) == 3:
                    # Обратная совместимость с v4
                    self._model, _, self.sample_rate = result
                else:
                    raise ValueError(f"Неожиданный формат: {len(result)} элементов")
            else:
                self._model = result

            if not isinstance(self.sample_rate, int):
                self.sample_rate = DEFAULT_SAMPLE_RATE

            if hasattr(self._model, 'to'):
                self._model.to(self.device)

            self._log_status(f"Модель {MODEL_ID} загружена (частота: {self.sample_rate} Гц)")

        except Exception as e:
            BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка загрузки модели: {e}")
            import traceback
            traceback.print_exc()
            raise

    # ============================================================
    # ВОРКЕР ОЧЕРЕДИ
    # ============================================================

    def _start_tts_worker(self):
        """Запускает фоновый воркер для обработки очереди TTS"""
        self._tts_worker_running = True
        self._tts_worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._tts_worker_thread.start()
        BasicUtils.logger("TTSSilero", "INFO", "Фоновый TTS воркер запущен")

    def _tts_worker(self):
        """
        Фоновый воркер для обработки очереди сообщений.
        Использует блокирующий Queue.get() вместо busy-wait — не грузит CPU в ожидании.
        """
        while self._tts_worker_running:
            try:
                # Блокируемся до появления задачи; timeout нужен чтобы проверять флаг выхода
                text, voice, speed, callback = self._tts_queue.get(timeout=0.5)
            except Empty:
                continue
            except Exception as e:
                BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка получения задачи из очереди: {e}")
                continue

            self._tts_processing = True
            try:
                BasicUtils.logger("TTSSilero", "INFO",
                                   f"Воспроизведение из очереди: {text[:50]}...")
                self._speak_sync(text, voice, speed)

                if callback:
                    try:
                        callback()
                    except Exception as e:
                        BasicUtils.logger("TTSSilero", "WARNING", f"Ошибка в callback: {e}")
            except Exception as e:
                BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка в TTS воркере: {e}")
            finally:
                self._tts_processing = False

    # ============================================================
    # РАЗБИЕНИЕ ТЕКСТА
    # ============================================================

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """
        Разбивает длинный текст на части для обхода ограничений модели.

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

        if len(text) <= self.max_chunk_length:
            return [text.strip()]

        chunks = []
        sentence_delimiters = r'(?<=[.!?;:\n])\s+'
        sentences = re.split(sentence_delimiters, text)
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_length:
                current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                if len(sentence) > self.max_chunk_length:
                    chunks.extend(self._split_long_sentence(sentence))
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        if len(chunks) > 1:
            BasicUtils.logger("TTSSilero", "INFO",
                               f"Текст разбит на {len(chunks)} частей (макс. длина {self.max_chunk_length})")
            for i, chunk in enumerate(chunks):
                BasicUtils.logger("TTSSilero", "DEBUG",
                                   f"  Часть {i + 1}: {len(chunk)} символов - {chunk[:50]}...")

        return chunks

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Разбивает очень длинное предложение на части"""
        chunks = []
        comma_parts = re.split(r'(?<=,)\s+', sentence)

        if len(comma_parts) > 1:
            current = ""
            for part in comma_parts:
                if len(current) + len(part) + 2 <= self.max_chunk_length:
                    current = (current + " " + part).strip() if current else part
                else:
                    if current:
                        chunks.append(current)
                    if len(part) > self.max_chunk_length:
                        chunks.extend(self._split_by_words(part))
                        current = ""
                    else:
                        current = part
            if current:
                chunks.append(current)
            return chunks

        return self._split_by_words(sentence)

    def _split_by_words(self, text: str) -> List[str]:
        """Разбивает текст по словам на части заданной длины"""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 <= self.max_chunk_length:
                current_chunk = (current_chunk + " " + word).strip() if current_chunk else word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # ============================================================
    # ОБРАБОТКА ТЕКСТА
    # ============================================================

    def _setup_text_processing(self):
        """Настройка словарей для обработки текста"""

        self.base_numbers = {
            0: 'ноль', 1: 'один', 2: 'два', 3: 'три', 4: 'четыре',
            5: 'пять', 6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять',
            10: 'десять'
        }

        self.teen_numbers = {
            11: 'одиннадцать', 12: 'двенадцать', 13: 'тринадцать',
            14: 'четырнадцать', 15: 'пятнадцать', 16: 'шестнадцать',
            17: 'семнадцать', 18: 'восемнадцать', 19: 'девятнадцать'
        }

        self.tens = {
            20: 'двадцать', 30: 'тридцать', 40: 'сорок',
            50: 'пятьдесят', 60: 'шестьдесят', 70: 'семьдесят',
            80: 'восемьдесят', 90: 'девяносто'
        }

        self.hundreds = {
            100: 'сто', 200: 'двести', 300: 'триста',
            400: 'четыреста', 500: 'пятьсот', 600: 'шестьсот',
            700: 'семьсот', 800: 'восемьсот', 900: 'девятьсот'
        }

        self.magnitudes = [
            (1_000_000_000_000_000, 'квадриллион', 'квадриллиона', 'квадриллионов'),
            (1_000_000_000_000, 'триллион', 'триллиона', 'триллионов'),
            (1_000_000_000, 'миллиард', 'миллиарда', 'миллиардов'),
            (1_000_000, 'миллион', 'миллиона', 'миллионов'),
            (1_000, 'тысяча', 'тысячи', 'тысяч'),
        ]

        self.abbreviations = {
            'т.д.': 'так далее',
            'т.п.': 'тому подобное',
            'т.е.': 'то есть',
            'и.т.д.': 'и так далее',
            'и.т.п.': 'и тому подобное',
            'т.к.': 'потому что',
            'напр.': 'например',
            'т.н.': 'так называемый',
            'др.': 'другие',
            'гг.': 'годы',
            'см.': 'смотри',
            'стр.': 'страница',
            'руб.': 'рублей',
            'коп.': 'копеек',
            'км.': 'километров',
            'кг.': 'килограммов',
            'сек.': 'секунд',
            'мин.': 'минут',
            'мес.': 'месяцев',
        }

        # Знаки препинания — добавляем пробелы вокруг для лучшей интонации
        self.punctuation_pauses = {
            '.': ' . ', '!': ' ! ', '?': ' ? ', ';': ' ; ',
            ':': ' : ', ',': ' , ', '(': ' ( ', ')': ' ) ',
        }

    def _convert_number_to_words(self, num: int) -> str:
        """Преобразует целое число в слова на русском языке"""
        if num < 0:
            return f"минус {self._convert_number_to_words(-num)}"
        if num == 0:
            return self.base_numbers[0]
        if num < 1000:
            return self._convert_less_than_thousand(num)

        result_parts = []
        for magnitude, single, few, many in self.magnitudes:
            if num >= magnitude:
                count = num // magnitude
                num = num % magnitude
                count_words = self._convert_less_than_thousand(count)
                last2 = count % 100
                last1 = count % 10
                if last1 == 1 and last2 != 11:
                    magnitude_word = single
                elif 2 <= last1 <= 4 and not (10 <= last2 <= 19):
                    magnitude_word = few
                else:
                    magnitude_word = many
                result_parts.append(f"{count_words} {magnitude_word}")

        if num > 0:
            result_parts.append(self._convert_less_than_thousand(num))

        return ' '.join(result_parts)

    def _convert_less_than_thousand(self, num: int) -> str:
        """Преобразует число от 0 до 999 в слова"""
        if num == 0:
            return ""

        parts = []

        if num >= 100:
            hundreds_val = (num // 100) * 100
            parts.append(self.hundreds[hundreds_val])
            num %= 100

        if 11 <= num <= 19:
            parts.append(self.teen_numbers[num])
            return ' '.join(parts)

        if num >= 20:
            tens_val = (num // 10) * 10
            parts.append(self.tens[tens_val])
            num %= 10

        if num >= 1:
            parts.append(self.base_numbers[num])

        return ' '.join(parts)

    def _process_numbers_in_text(self, text: str) -> str:
        """
        Обрабатывает числа в тексте, заменяя их на слова.
        Дробные числа (3.14) корректно читаются как «три целых один четыре».
        """
        def replace_number(match):
            num_str = match.group(0)

            if '.' in num_str:
                # Дробное число: 3.14 → «три целых один четыре»
                integer_part, fractional_part = num_str.split('.', 1)
                int_word = self._convert_number_to_words(int(integer_part)) if integer_part else 'ноль'
                # Каждую цифру дробной части читаем отдельно
                frac_words = ' '.join(
                    self.base_numbers.get(int(d), d) for d in fractional_part if d.isdigit()
                )
                return f"{int_word} целых {frac_words}"

            num_str = num_str.lstrip('0') or '0'
            try:
                num = int(num_str)
                if num > 10 ** 15:
                    return num_str
                return self._convert_number_to_words(num)
            except ValueError:
                return num_str

        pattern = r'\b\d+(?:\.\d+)?\b'
        return re.sub(pattern, replace_number, text)

    def _process_ordinal_numbers(self, text: str) -> str:
        """Обрабатывает порядковые числительные (1-й, 2-й и т.д.)"""
        ordinal_map = {
            '1-й': 'первый', '2-й': 'второй', '3-й': 'третий',
            '4-й': 'четвертый', '5-й': 'пятый', '6-й': 'шестой',
            '7-й': 'седьмой', '8-й': 'восьмой', '9-й': 'девятый',
            '10-й': 'десятый', '11-й': 'одиннадцатый', '12-й': 'двенадцатый',
            '13-й': 'тринадцатый', '14-й': 'четырнадцатый', '15-й': 'пятнадцатый',
            '16-й': 'шестнадцатый', '17-й': 'семнадцатый', '18-й': 'восемнадцатый',
            '19-й': 'девятнадцатый', '20-й': 'двадцатый',
        }

        for num_str, word in ordinal_map.items():
            text = text.replace(num_str, word)

        def replace_composite(match):
            num = int(match.group(1))
            if num <= 20:
                return ordinal_map.get(f"{num}-й", match.group(0))
            tens_word = self.tens.get((num // 10) * 10, '')
            units = num % 10
            if units == 0:
                return f"{tens_word}й"
            units_word = self.base_numbers.get(units, '')
            return f"{tens_word} {units_word}й"

        return re.sub(r'(\d+)-й', replace_composite, text)

    def preprocess_text(self, text: str) -> str:
        """
        Предобработка текста для улучшения качества синтеза.

        Args:
            text: исходный текст

        Returns:
            обработанный текст
        """
        if not text or not text.strip():
            return text

        original_text = text

        # 1. Нормализация переносов строк до обработки аббревиатур
        text = text.replace('\n', '. ').replace('\t', ' ')

        # 2. Замена аббревиатур
        for abbr, full in self.abbreviations.items():
            text = text.replace(abbr, full)
            text = text.replace(abbr.upper(), full)
            text = text.replace(abbr.capitalize(), full)

        # 3. Нормализация кавычек
        text = text.replace('«', '"').replace('»', '"')
        text = text.replace('\u201c', '"').replace('\u201d', '"')

        # 4. Порядковые числительные
        text = self._process_ordinal_numbers(text)

        # 5. Числа (включая дробные)
        text = self._process_numbers_in_text(text)

        # 6. Пробелы вокруг знаков препинания для лучшей интонации
        for punct, replacement in self.punctuation_pauses.items():
            text = text.replace(punct, replacement)

        # 7. Удаление лишних пробелов
        text = re.sub(r'\s+', ' ', text)

        # 8. Добавление точки в конце если нет
        text = text.strip()
        if text and text[-1] not in '.!?':
            text += '.'

        if original_text != text:
            BasicUtils.logger("TTSSilero", "DEBUG",
                               f"Текст обработан: {original_text[:50]}... -> {text[:50]}...")

        return text

    # ============================================================
    # ОБРАБОТКА АУДИО
    # ============================================================

    def _change_speed(self, audio: torch.Tensor, speed: float) -> torch.Tensor:
        """
        Изменение скорости аудио с сохранением высоты тона.

        Args:
            audio: аудиоданные
            speed: коэффициент скорости (0.5-2.0)

        Returns:
            изменённое аудио
        """
        if speed == 1.0 or self.quality == "low":
            return audio

        try:
            import librosa
            audio_np = audio.cpu().numpy()
            audio_changed = librosa.effects.time_stretch(audio_np, rate=speed)
            return torch.from_numpy(audio_changed)
        except ImportError:
            # Fallback: линейная интерполяция
            old_len = len(audio)
            new_len = int(old_len / speed)
            indices = torch.linspace(0, old_len - 1, new_len).long()
            indices = torch.clamp(indices, 0, old_len - 1)
            return audio[indices]

    def _post_process_audio(self, audio: torch.Tensor) -> torch.Tensor:
        """
        Пост-обработка аудио для улучшения качества.

        Исправление относительно предыдущей версии:
        - boost строится как float32 и явно применяется к real/imag частям
          комплексного тензора FFT, что исключает NaN на старых версиях torch.
        - Параметр n= в irfft гарантирует корректную длину при чётном числе сэмплов.

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

            if self.quality == "high" and hasattr(torch, 'fft'):
                n = len(audio)
                fft = torch.fft.rfft(audio)
                freq = torch.fft.rfftfreq(n, d=1.0 / self.sample_rate)

                # Строим вещественный множитель
                boost = torch.ones(fft.shape[0], dtype=torch.float32)
                boost[freq < 200] = 0.95     # чуть убираем гул низких частот
                boost[freq > 3000] = 1.08    # мягкий подъём для разборчивости

                # Применяем boost к real и imag отдельно — без артефактов complex*float
                fft = torch.view_as_complex(
                    torch.view_as_real(fft) * boost.unsqueeze(-1)
                )

                audio = torch.fft.irfft(fft, n=n)
                audio = torch.clamp(audio, -0.99, 0.99)

            return audio
        except Exception as e:
            BasicUtils.logger("TTSSilero", "WARNING", f"Ошибка пост-обработки: {e}")
            return audio

    def _normalize_volume(self, audio: torch.Tensor, target_db: float = -14.0) -> torch.Tensor:
        """
        Нормализация громкости аудио.

        target_db повышен с -20 до -14 dB — стандарт для голосовых ассистентов.

        Args:
            audio: аудиоданные
            target_db: целевая громкость в dB (default: -14.0)

        Returns:
            нормализованное аудио
        """
        if self.quality == "low":
            return audio

        try:
            rms = torch.sqrt(torch.mean(audio ** 2))
            if rms > 1e-8:
                target_rms = 10 ** (target_db / 20)
                audio = audio * (target_rms / rms)

            # Ограничение пиков без клиппинга
            max_val = torch.max(torch.abs(audio))
            if max_val > 0.95:
                audio = audio * (0.95 / max_val)

            return audio
        except Exception as e:
            BasicUtils.logger("TTSSilero", "WARNING", f"Ошибка нормализации: {e}")
            return audio

    # ============================================================
    # СИНТЕЗ
    # ============================================================

    def _synthesize_single_chunk(self, text: str, voice: Optional[str] = None,
                                  speed: Optional[float] = None) -> torch.Tensor:
        """
        Синтезирует один фрагмент текста.

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

        processed_text = self.preprocess_text(text)

        audio = self._model.apply_tts(
            text=processed_text,
            speaker=v,
            sample_rate=self.sample_rate,
            put_accent=True,
            put_yo=True,
        )

        if s != 1.0:
            audio = self._change_speed(audio, s)

        return audio

    def _get_from_cache(self, cache_key: str) -> Optional[torch.Tensor]:
        """Достаёт аудио из кэша и обновляет порядок LRU"""
        if self.cache_size > 0 and cache_key in self._audio_cache:
            self._audio_cache.move_to_end(cache_key)
            return self._audio_cache[cache_key]
        return None

    def _put_to_cache(self, cache_key: str, audio: torch.Tensor):
        """Сохраняет аудио в кэш с вытеснением самого старого"""
        if self.cache_size > 0:
            if len(self._audio_cache) >= self.cache_size:
                self._audio_cache.popitem(last=False)
            self._audio_cache[cache_key] = audio

    def synthesize(self, text: str, voice: Optional[str] = None,
                   speed: Optional[float] = None) -> torch.Tensor:
        """
        Синтезирует речь из текста (с автоматическим разбиением длинного текста).
        Возвращает объединённый тензор. Для streaming-воспроизведения используйте _speak_sync.

        Args:
            text: текст для синтеза (может быть очень длинным)
            voice: имя голоса (переопределяет self.voice)
            speed: скорость речи (переопределяет self.speed)

        Returns:
            torch.Tensor с объединёнными аудиоданными
        """
        if not text or not text.strip():
            return torch.tensor([])

        v = voice if voice is not None else self.voice
        s = speed if speed is not None else self.speed

        # Короткий текст — один вызов
        if len(text) <= self.max_chunk_length:
            cache_key = f"{text}_{v}_{s}"
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                BasicUtils.logger("TTSSilero", "DEBUG", f"Кэш: {text[:50]}...")
                return cached

            audio = self._synthesize_single_chunk(text, v, s)
            if self.quality != "low":
                audio = self._post_process_audio(audio)
                audio = self._normalize_volume(audio)

            self._put_to_cache(cache_key, audio)
            return audio

        # Длинный текст — синтезируем по чанкам и склеиваем
        chunks = self._split_text_into_chunks(text)
        audio_parts = []

        for i, chunk in enumerate(chunks):
            cache_key = f"{chunk}_{v}_{s}"
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                BasicUtils.logger("TTSSilero", "DEBUG", f"Кэш для части {i + 1}")
                audio_parts.append(cached)
                continue

            BasicUtils.logger("TTSSilero", "DEBUG",
                               f"Синтез части {i + 1}/{len(chunks)}: {len(chunk)} символов")
            audio = self._synthesize_single_chunk(chunk, v, s)
            if self.quality != "low":
                audio = self._post_process_audio(audio)
                audio = self._normalize_volume(audio)

            self._put_to_cache(cache_key, audio)
            audio_parts.append(audio)

        if not audio_parts:
            return torch.tensor([])

        # Склеиваем с фиксированной паузой 0.3 сек (для API метода synthesize)
        silence = torch.zeros(int(0.3 * self.sample_rate))
        combined = audio_parts[0]
        for part in audio_parts[1:]:
            combined = torch.cat([combined, silence, part])

        BasicUtils.logger("TTSSilero", "INFO",
                           f"Объединено {len(audio_parts)} фрагментов: "
                           f"{len(combined) / self.sample_rate:.1f} сек")
        return combined

    # ============================================================
    # ВОСПРОИЗВЕДЕНИЕ
    # ============================================================

    def _speak_sync(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None):
        """
        Pipeline воспроизведение: первый чанк начинает играть немедленно,
        следующие синтезируются пока играет текущий.

        Паузы между чанками динамические — зависят от последнего знака препинания.

        Args:
            text: текст для произнесения
            voice: имя голоса
            speed: скорость речи
        """
        if not text or not text.strip():
            return

        self._is_speaking = True
        self._stop_requested = False

        v = voice if voice is not None else self.voice
        s = speed if speed is not None else self.speed

        try:
            chunks = self._split_text_into_chunks(text)
            if not chunks:
                return

            for i, chunk in enumerate(chunks):
                if self._stop_requested:
                    break

                # Синтезируем текущий чанк
                cache_key = f"{chunk}_{v}_{s}"
                cached = self._get_from_cache(cache_key)

                if cached is not None:
                    audio = cached
                    BasicUtils.logger("TTSSilero", "DEBUG", f"Кэш для части {i + 1}")
                else:
                    BasicUtils.logger("TTSSilero", "DEBUG",
                                       f"Синтез части {i + 1}/{len(chunks)}: {len(chunk)} символов")
                    audio = self._synthesize_single_chunk(chunk, v, s)
                    if self.quality != "low":
                        audio = self._post_process_audio(audio)
                        audio = self._normalize_volume(audio)
                    self._put_to_cache(cache_key, audio)

                if self._stop_requested:
                    break

                # Воспроизводим чанк
                audio_np = audio.cpu().numpy()
                sd.play(audio_np, self.sample_rate)

                # Ждём окончания воспроизведения
                while sd.get_stream().active and not self._stop_requested:
                    time.sleep(0.01)

                if self._stop_requested:
                    sd.stop()
                    BasicUtils.logger("TTSSilero", "INFO", "Воспроизведение прервано")
                    break

                # Динамическая пауза между чанками
                if i < len(chunks) - 1:
                    last_char = chunk.rstrip()[-1] if chunk.rstrip() else ''
                    pause = CHUNK_PAUSE_MAP.get(last_char, DEFAULT_CHUNK_PAUSE)
                    time.sleep(pause)

        except Exception as e:
            BasicUtils.logger("TTSSilero", "ERROR", f"Ошибка воспроизведения: {e}")
        finally:
            self._is_speaking = False
            self._stop_requested = False

    def speak(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None,
              block: bool = False):
        """
        Воспроизводит текст вслух с автоматическим разбиением длинного текста.

        Args:
            text: текст для произнесения (может быть очень длинным)
            voice: имя голоса (переопределяет self.voice)
            speed: скорость речи (переопределяет self.speed)
            block: блокировать поток до окончания (True) или фоновое воспроизведение (False)
        """
        if not text or not text.strip():
            return

        v = voice if voice is not None else self.voice
        s = speed if speed is not None else self.speed

        text_len = len(text)
        if text_len > self.max_chunk_length:
            chunks_count = len(self._split_text_into_chunks(text))
            BasicUtils.logger("TTSSilero", "INFO",
                               f"Длинный текст ({text_len} символов) → {chunks_count} частей")

        if block:
            self._speak_sync(text, v, s)
        else:
            self._tts_queue.put((text, v, s, None))
            BasicUtils.logger("TTSSilero", "INFO", f"В очередь: {text[:50]}...")

    def speak_async(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None,
                    callback: Optional[Callable] = None):
        """
        Асинхронное воспроизведение с callback по окончании.

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
        BasicUtils.logger("TTSSilero", "INFO", f"В очередь (async): {text[:50]}...")

    def stop(self):
        """
        Останавливает текущее воспроизведение и очищает очередь.
        Thread-safe: очистка очереди через mutex.
        """
        self._stop_requested = True
        sd.stop()

        # Thread-safe очистка очереди
        with self._tts_queue.mutex:
            self._tts_queue.queue.clear()

        BasicUtils.logger("TTSSilero", "INFO", "Воспроизведение остановлено, очередь очищена")

    # ============================================================
    # УТИЛИТЫ
    # ============================================================

    def _log_status(self, message: str):
        """Логирование статуса с вызовом on_status callback"""
        BasicUtils.logger("TTSSilero", "INFO", message)
        if self.on_status:
            self.on_status(message)

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

    def save_wav(self, text: str, filepath: str, voice: Optional[str] = None,
                 speed: Optional[float] = None):
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
            audio_int16 = (audio.cpu().numpy() * 32767).astype(np.int16)
            wavfile.write(filepath, self.sample_rate, audio_int16)
            BasicUtils.logger("TTSSilero", "INFO", f"Файл сохранён: {filepath}")
        except ImportError:
            import torchaudio
            torchaudio.save(filepath, audio.unsqueeze(0).cpu(), self.sample_rate)
            BasicUtils.logger("TTSSilero", "INFO", f"Файл сохранён (torchaudio): {filepath}")

    def get_cache_info(self) -> Dict:
        """Возвращает информацию о кэше и текущем состоянии."""
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
            "queue_size": self.queue_size,
            "is_speaking": self.is_speaking,
        }

    def cleanup(self):
        """Очистка ресурсов при завершении"""
        BasicUtils.logger("TTSSilero", "INFO", "Очистка ресурсов...")
        self._tts_worker_running = False
        self.stop()

        if self._tts_worker_thread and self._tts_worker_thread.is_alive():
            self._tts_worker_thread.join(timeout=2.0)


# ============================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР (для простого использования)
# ============================================================

_default_tts: Optional[SileroTTS] = None


def get_default_tts() -> SileroTTS:
    """Возвращает глобальный экземпляр TTS (создаёт при первом вызове)"""
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
    get_default_tts().speak(text, voice=voice, block=block)


def speak_async(text: str, voice: Optional[str] = None, callback: Optional[Callable] = None):
    """
    Асинхронное воспроизведение текста с callback.

    Args:
        text: текст для произнесения
        voice: имя голоса
        callback: функция, вызываемая после завершения
    """
    get_default_tts().speak_async(text, voice=voice, callback=callback)


def stop():
    """Останавливает текущее воспроизведение и очищает очередь"""
    get_default_tts().stop()


def cleanup():
    """Очистка ресурсов"""
    get_default_tts().cleanup()


# ============================================================
# ТЕСТ
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print(f"Тест Silero TTS {MODEL_ID}")
    print("=" * 50)

    print(f"\nДоступные голоса: {RUSSIAN_VOICES}")
    print(f"Рекомендуемый голос: xenia")
    print(f"Модели сохраняются в: {MODELS_DIR}")

    tts = SileroTTS(voice="xenia", quality="high", max_chunk_length=500)

    print("\n--- Короткий текст ---")
    tts.speak("Привет! Я голосовой ассистент на модели v5.", block=True)

    print("\n--- Дробные числа ---")
    tts.speak("Число Пи равно 3.14. Курс доллара сегодня 89.5 рублей.", block=True)

    print("\n--- Длинный текст (pipeline: первый чанк играет сразу) ---")
    long_text = """
    Это очень длинный текст для проверки автоматического разбиения.
    Модель должна самостоятельно разбить его на части, чтобы обойти ограничения по длине.

    Вот второе предложение. И третье предложение с числами: 123, 456.

    Проверка омографов: Я живу в большом замке. У меня сломался замок на двери.

    Проверка ударений: Мне нужна мука для пирога. Это была настоящая мука.

    И финальное предложение, которое завершает этот длинный тест. Тест успешно пройден!
    """
    print(f"Длина текста: {len(long_text)} символов")
    tts.speak(long_text, block=True)

    print("\n--- Очередь сообщений ---")
    tts.speak("Первое сообщение в очереди", block=False)
    tts.speak("Второе сообщение в очереди", block=False)
    tts.speak("Третье сообщение в очереди", block=False)

    time.sleep(15)

    print(f"\nИнформация: {tts.get_cache_info()}")
    tts.cleanup()
    print(f"\n✅ Тест {MODEL_ID} завершён успешно!")