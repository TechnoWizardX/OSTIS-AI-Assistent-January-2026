"""
Silero TTS — обёртка для синтеза речи на русском языке.

Использует Silero Models v4 (ru). Офлайн после первой загрузки.

Пример:
    from TTSSilero import speak, stop
    speak("Привет, чем могу помочь?")
"""

import os
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional, Callable, List

import torch
import sounddevice as sd

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

# Доступные русские голоса Silero v4
RUSSIAN_VOICES = ["aidar", "baya", "kseniya", "xenia", "eugene", "random"]

# Идентификатор модели (v4_ru — актуальная русская модель)
MODEL_ID = "v4_ru"

# Доступные sample_rate для v4_ru
SAMPLE_RATES = {
    "v4_ru": 48000,
}

SPEAKER = "kseniya"  # Голос по умолчанию
SAMPLE_RATE = 48000
SPEED = 1.0


class SileroTTS:
    """
    Синтезатор речи на базе Silero TTS (модель v4_ru).

    При первом использовании загружает модель (~200 МБ).
    Последующие запуски работают офлайн.

    Атрибуты:
        voice: имя голоса (kseniya, aidar, baya, irina, natasha, ruslan)
        sample_rate: частота дискретизации (48000)
        speed: скорость речи (0.5 - 2.0, 1.0 = норма)

    Примеры:
        >>> tts = SileroTTS(voice="kseniya")
        >>> tts.speak("Привет, мир!")
        >>> tts.speak("Медленная речь", speed=0.7)
        >>> tts.available_voices()  # список голосов
    """

    def __init__(
        self,
        voice: str = SPEAKER,
        sample_rate: int = SAMPLE_RATE,
        speed: float = SPEED,
        device: str = "cpu",
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            voice: имя голоса (kseniya, aidar, baya, irina, natasha, ruslan)
            sample_rate: частота дискретизации (48000)
            speed: скорость речи (0.5 — 2.0, 1.0 = норма)
            device: "cpu" или "cuda"
            on_status: callback для отображения статуса загрузки
        """
        self.voice = voice
        self.sample_rate = sample_rate
        self.speed = speed
        self.device = device
        self.on_status = on_status

        self._model = None
        self._is_speaking = False
        self._stop_requested = False

        self._load_model()

    def _log(self, msg: str):
        """Выводит статусное сообщение."""
        print(f"[SileroTTS] {msg}")
        if self.on_status:
            self.on_status(msg)

    def _load_model(self):
        """Загружает модель Silero TTS через torch.hub."""
        if self._model is not None:
            return

        self._log(f"Загрузка модели Silero TTS ({MODEL_ID})...")

        try:
            # ВНИМАНИЕ: speaker здесь = идентификатор модели, не имя голоса!
            # torch.hub.load возвращает кортеж (model, symbols, sample_rate)
            result = torch.hub.load(
                repo_or_dir="snakers4/silero-models",
                model="silero_tts",
                language="ru",
                speaker=MODEL_ID,
                trust_repo=True,
            )
            # torch.hub.load возвращает кортеж, но порядок зависит от версии
            # Определяем элементы по типу: int = sample_rate, hasattr(apply_tts) = model
            if isinstance(result, tuple):
                for item in result:
                    if isinstance(item, int):
                        self.sample_rate = item
                    elif hasattr(item, 'apply_tts'):
                        self._model = item
            if self._model is None and isinstance(result, tuple):
                self._model = result[0]
            if not isinstance(self.sample_rate, int):
                self.sample_rate = SAMPLE_RATE

            self._model.to(self.device)
            self._log(f"Модель загружена. Голос: {self.voice}, sample_rate: {self.sample_rate}")
        except Exception as e:
            self._log(f"Ошибка загрузки модели: {e}")
            raise

    def available_voices(self) -> List[str]:
        """Возвращает список доступных русских голосов."""
        return RUSSIAN_VOICES.copy()

    def synthesize(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> torch.Tensor:
        """
        Синтезирует речь из текста.

        Args:
            text: текст для синтеза
            voice: имя голоса (переопределяет self.voice)
            speed: скорость речи (переопределяет self.speed)

        Returns:
            torch.Tensor с аудиоданными
        """
        if self._model is None:
            self._load_model()

        v = voice if voice is not None else self.voice

        # Для v4_ru: apply_tts принимает text, speaker, sample_rate
        audio = self._model.apply_tts(
            text=text,
            speaker=v,
            sample_rate=self.sample_rate,
        )

        return audio

    def speak(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None, block: bool = True):
        """
        Воспроизводит текст вслух.

        Args:
            text: текст для произнесения
            voice: имя голоса (переопределяет self.voice)
            speed: скорость речи (переопределяет self.speed)
            block: блокировать поток до окончания (True) или запустить в фоне (False)
        """
        if self._is_speaking:
            self._stop_requested = True
            time.sleep(0.1)

        if block:
            self._speak_internal(text, voice, speed)
        else:
            self._stop_requested = False
            thread = threading.Thread(
                target=self._speak_internal, args=(text, voice, speed), daemon=True
            )
            thread.start()

    def _speak_internal(self, text: str, voice: Optional[str], speed: Optional[float]):
        """Внутренний метод для воспроизведения."""
        self._is_speaking = True
        self._stop_requested = False

        try:
            audio = self.synthesize(text, voice, speed)

            # Воспроизведение через sounddevice
            sd.play(audio.cpu().numpy(), self.sample_rate)
            sd.wait()

            if self._stop_requested:
                sd.stop()
                self._log("Воспроизведение остановлено")
            else:
                self._log("Воспроизведение завершено")
        except Exception as e:
            self._log(f"Ошибка воспроизведения: {e}")
        finally:
            self._is_speaking = False
            self._stop_requested = False

    def stop(self):
        """Останавливает текущее воспроизведение."""
        if self._is_speaking:
            self._stop_requested = True
            sd.stop()

    @property
    def is_speaking(self) -> bool:
        """Проверяет, идёт ли воспроизведение."""
        return self._is_speaking

    def save_wav(self, text: str, filepath: str, voice: Optional[str] = None, speed: Optional[float] = None):
        """
        Сохраняет синтезированную речь в WAV-файл.

        Args:
            text: текст
            filepath: путь к файлу
            voice: имя голоса
            speed: скорость речи
        """
        audio = self.synthesize(text, voice, speed)

        try:
            import scipy.io.wavfile as wavfile
            wavfile.write(filepath, self.sample_rate, audio.cpu().numpy())
            self._log(f"Файл сохранён: {filepath}")
        except ImportError:
            import torchaudio
            torchaudio.save(
                filepath,
                audio.unsqueeze(0).cpu(),
                self.sample_rate,
            )
            self._log(f"Файл сохранён: {filepath}")


# ============================================================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР (для удобства)
# ============================================================
_tts_instance: Optional[SileroTTS] = None


def get_tts(voice: str = SPEAKER, **kwargs) -> SileroTTS:
    """Возвращает или создаёт глобальный экземпляр TTS."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = SileroTTS(voice=voice, **kwargs)
    return _tts_instance


def speak(text: str, voice: Optional[str] = None, speed: Optional[float] = None, block: bool = True):
    """Быстрая функция для синтеза речи."""
    tts = get_tts()
    tts.speak(text, voice=voice, speed=speed, block=block)


def stop():
    """Остановить воспроизведение."""
    global _tts_instance
    if _tts_instance:
        _tts_instance.stop()


# ============================================================
# ТЕСТ
# ============================================================
if __name__ == "__main__":
    print("Тест Silero TTS...")
    print(f"Доступные голоса: {RUSSIAN_VOICES}")

    tts = SileroTTS(voice="xenia")
    tts.speak("Привет! Я голосовой ассистент. Чем могу помочь?", block=True)
    tts.speak("Это тест синтеза речи на русском языке.", block=True)
    print("Готово!")
