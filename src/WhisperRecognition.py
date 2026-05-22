import io
import re
import wave
import queue
import threading
import numpy as np
import torch
import speech_recognition as sr
from faster_whisper import WhisperModel
from silero_vad import load_silero_vad, get_speech_timestamps
from BasicUtils import BasicUtils, global_signals

torch.set_num_threads(1)


class WhisperRecognition:
    """
    Модуль распознавания голоса, адаптированный для людей с ОПРФ.

    Поддерживаемые нарушения речи:
    ─────────────────────────────────────────────────────────────────
    • Дизартрия      — нечёткая, смазанная речь (ДЦП, инсульт, БАС)
    • Заикание       — повторы слогов, длинные паузы внутри фразы
    • Афазия         — пропуски слов, нарушенный порядок, короткие фразы
    • Слабый голос   — тихая речь, утомляемость голоса
    • Медленная речь — растянутые слоги, паузы между словами

    Архитектура пайплайна:
    ─────────────────────────────────────────────────────────────────
    Микрофон → _callback (enqueue, <1 мс)
             → VAD-воркер (мягкий, терпимый к паузам)
             → Chunk-аккумулятор (склеивает фрагменты с паузами)
             → Whisper (с промптом и щадящими порогами)
             → Постпроцессор (чистит артефакты дизартрии/заикания)
             → emit сигнала в UI
    """

    _QUEUE_MAX = 20

    def __init__(
        self,
        model: str = "small",
        device: str = "cpu",
        model_download_root: str = None,
        compute_type: str = "int8",
        # ── VAD: мягкие настройки для слабого/нечёткого голоса ──────
        vad_threshold: float = 0.25,        # ↓ стандарт 0.5 → ловим тихую речь
        min_speech_duration: float = 0.15,  # ↓ стандарт 0.3 → ловим короткие слоги
        # ── Аккумулятор: ждём паузы при заикании/медленной речи ─────
        max_pause_sec: float = 2.5,         # пауза внутри фразы до сброса буфера
        max_chunk_sec: float = 15.0,        # максимальная длина накопленного аудио
        # ── Усиление сигнала для тихой речи ─────────────────────────
        amplify_factor: float = 2.5,        # коэффициент усиления (1.0 = выкл)
    ):
        BasicUtils.logger("Whisper", "INFO", f"Модель: {model} | Режим ОПРФ активен")

        self.model = WhisperModel(
            model,
            device=device,
            compute_type=compute_type,
            download_root=model_download_root,
        )

        self.sample_rate = 16000
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration
        self.max_pause_samples = int(max_pause_sec * self.sample_rate)
        self.max_chunk_samples = int(max_chunk_sec * self.sample_rate)
        self.amplify_factor = amplify_factor

        BasicUtils.logger("Whisper", "INFO", "Загрузка Silero VAD...")
        self.vad_model = load_silero_vad()
        BasicUtils.logger("Whisper", "INFO", "Silero VAD загружен")

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 150   # ↓ стандарт 300 → тихий голос
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 2.0    # ↑ стандарт 0.8 → ждём паузу при заикании
        self.recognizer.phrase_threshold = 0.1   # ↓ быстрее начинаем слушать

        # Очередь сырых numpy-фрагментов от микрофона
        self._audio_queue: queue.Queue[np.ndarray | None] = queue.Queue(
            maxsize=self._QUEUE_MAX
        )

        # Аккумулятор фрагментов (склеивает паузы при заикании/медленной речи)
        self._buffer: list[np.ndarray] = []
        self._buffer_samples: int = 0

        self._stop_func = None
        self._buffer_lock = threading.Lock()
        self._flush_timer: threading.Timer | None = None

        self._worker_thread = threading.Thread(
            target=self._process_loop, daemon=True, name="WhisperWorker"
        )
        self._worker_thread.start()

    # ──────────────────────────────────────────────────────────────────
    # Публичный API
    # ──────────────────────────────────────────────────────────────────

    def start_recognition(self):
        if self._stop_func is not None:
            return
        BasicUtils.logger("Whisper", "INFO", "Микрофон включён (режим ОПРФ)")
        mic = sr.Microphone(sample_rate=self.sample_rate)
        with mic as source:
            # Дольше калибруемся — голос может быть тихим или нестабильным
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
        self._stop_func = self.recognizer.listen_in_background(mic, self._callback)

    def stop_recognition(self):
        if self._stop_func:
            self._stop_func(wait_for_stop=False)
            self._stop_func = None
            self._cancel_flush_timer()
            BasicUtils.logger("Whisper", "INFO", "Микрофон выключен")

    # ──────────────────────────────────────────────────────────────────
    # Пайплайн
    # ──────────────────────────────────────────────────────────────────

    def _callback(self, recognizer, audio):
        """
        Вызывается из потока speech_recognition.
        Только декодирует WAV → numpy и кладёт в очередь. < 1 мс.
        """
        try:
            audio_np = _wav_bytes_to_numpy(audio.get_wav_data())
            if audio_np is None:
                return
            try:
                self._audio_queue.put_nowait(audio_np)
            except queue.Full:
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    pass
                self._audio_queue.put_nowait(audio_np)
        except Exception as e:
            BasicUtils.logger("Whisper", "ERROR", f"Callback: {e}")

    def _process_loop(self):
        """
        Воркер: достаёт фрагменты из очереди, прогоняет через VAD,
        аккумулирует в буфер, по таймауту/максимуму — отправляет в Whisper.
        """
        while True:
            try:
                audio_np = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if audio_np is None:
                break

            # Усиление тихой речи с защитой от клиппинга
            if self.amplify_factor != 1.0:
                audio_np = np.clip(audio_np * self.amplify_factor, -1.0, 1.0)

            # VAD: есть ли речь в фрагменте?
            if not self._vad_contains_speech(audio_np):
                BasicUtils.logger("Whisper", "DEBUG", "VAD: речь не обнаружена")
                with self._buffer_lock:
                    if self._buffer:
                        self._schedule_flush()
                continue

            # Есть речь → добавить в буфер, перезапустить таймер
            with self._buffer_lock:
                self._cancel_flush_timer()
                self._buffer.append(audio_np)
                self._buffer_samples += len(audio_np)

                if self._buffer_samples >= self.max_chunk_samples:
                    # Буфер достиг максимума — транскрибируем немедленно
                    self._flush_buffer_locked()
                else:
                    # Ждём паузу (при заикании пользователь может замолчать)
                    self._schedule_flush()

    def _schedule_flush(self):
        """Запланировать сброс буфера через max_pause_sec."""
        self._cancel_flush_timer()
        timeout = self.max_pause_samples / self.sample_rate
        self._flush_timer = threading.Timer(timeout, self._flush_on_timeout)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _cancel_flush_timer(self):
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None

    def _flush_on_timeout(self):
        """Сброс буфера по таймауту (пауза в речи — заикание, медленная речь)."""
        with self._buffer_lock:
            self._flush_buffer_locked()

    def _flush_buffer_locked(self):
        """Склеивает буфер и отправляет в Whisper. Вызывать под _buffer_lock."""
        if not self._buffer:
            return
        audio_np = np.concatenate(self._buffer)
        self._buffer.clear()
        self._buffer_samples = 0
        threading.Thread(
            target=self._transcribe_and_emit,
            args=(audio_np,),
            daemon=True,
            name="WhisperTranscribe",
        ).start()

    # ──────────────────────────────────────────────────────────────────
    # VAD
    # ──────────────────────────────────────────────────────────────────

    def _vad_contains_speech(self, audio_np: np.ndarray) -> bool:
        audio_tensor = torch.from_numpy(audio_np)
        speech_ts = get_speech_timestamps(
            audio_tensor,
            self.vad_model,
            sampling_rate=self.sample_rate,
            threshold=self.vad_threshold,
            min_speech_duration_ms=int(self.min_speech_duration * 1000),
            # Мягкие отступы — не обрезаем краевые фонемы при дизартрии
            speech_pad_ms=200,
        )
        return bool(speech_ts)

    # ──────────────────────────────────────────────────────────────────
    # Транскрипция
    # ──────────────────────────────────────────────────────────────────

    def _transcribe_and_emit(self, audio_np: np.ndarray):
        try:
            segments, _ = self.model.transcribe(
                audio_np,
                beam_size=5,
                language="ru",
                # ── Щадящие пороги для нечёткой/тихой речи ─────────────
                no_speech_threshold=0.30,        # ↓ стандарт 0.6 → не дропаем нечёткое
                log_prob_threshold=-1.2,         # ↓ стандарт -1.0 → терпимее к неуверенности
                compression_ratio_threshold=3.0, # ↑ стандарт 2.4 → терпимее к повторам (заикание)
                condition_on_previous_text=True, # контекст помогает при афазии
                # ── Промпт: подсказываем модели чего ожидать ────────────
                initial_prompt=(
                    "Речь человека с нарушением речи. "
                    "Возможны паузы, повторы слогов и слов, нечёткое произношение. "
                    "Распознавай максимально точно, не пропускай слова."
                ),
                # ── Несколько температур: fallback при низкой уверенности
                temperature=[0.0, 0.2, 0.4],
            )

            full_text = ""
            for segment in segments:
                # Пропускаем только при очень высокой уверенности в тишине
                if segment.no_speech_prob > 0.80:
                    continue
                full_text += segment.text

            full_text = _postprocess(full_text)

            if full_text:
                BasicUtils.logger("Whisper", "INFO", f"Распознано: {full_text}")
                global_signals.voice_message_recognized.emit(full_text)

        except Exception as e:
            BasicUtils.logger("Whisper", "ERROR", f"Транскрипция: {e}")


# ──────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────────────────────────────

def _wav_bytes_to_numpy(wav_bytes: bytes) -> np.ndarray | None:
    """WAV-байты → float32 numpy [-1, 1]."""
    try:
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            raw = wf.readframes(wf.getnframes())
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        return None


def _postprocess(text: str) -> str:
    """
    Чистит артефакты нарушений речи после транскрипции Whisper.

    • Убирает одиночные паразитные звуки: «э», «м», «эм», «хм»
    • Убирает повторы слов (заикание): «я я я хочу» → «я хочу»
    • Нормализует пробелы
    • Отфильтровывает строки только из знаков препинания
    """
    text = text.strip()
    if not text:
        return text

    # Одиночные паразитные звуки
    text = re.sub(r'\b(э+|м+|эм+|хм+|ах+|ох+)\b', '', text, flags=re.IGNORECASE)

    # Повторы слов подряд (заикание): «да да да» → «да», до 5 повторов
    text = re.sub(r'\b(\w+)(\s+\1){1,4}\b', r'\1', text, flags=re.IGNORECASE)

    # Нормализация пробелов
    text = re.sub(r'\s{2,}', ' ', text).strip()

    # Артефакт тихой речи — строка только из пунктуации
    if re.fullmatch(r'[\s.,!?;:\-–—…]+', text):
        return ""

    return text