import io
import wave
import numpy as np
import torch
import speech_recognition as sr
from faster_whisper import WhisperModel
from silero_vad import load_silero_vad, get_speech_timestamps  # pip install silero-vad
from BasicUtils import BasicUtils, global_signals

torch.set_num_threads(1)  # Важно для VAD на CPU

class WhisperRecognition():
    def __init__(
        self,
        model: str = "small",
        device: str = "cpu",
        model_download_root: str = None,
        compute_type: str = "int8",
        vad_threshold: float = 0.5,
        min_speech_duration: float = 0.3,
    ):
        BasicUtils.logger("Whisper", "INFO", f"Используем модель: {model}")
        self.model = WhisperModel(
            model, device=device,
            compute_type=compute_type,
            download_root=model_download_root
        )
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.stop_func = None
        self.sample_rate = 16000
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration

        BasicUtils.logger("Whisper", "INFO", "Загрузка Silero VAD...")
        self.vad_model = load_silero_vad()  # правильный вызов для pip-пакета
        BasicUtils.logger("Whisper", "INFO", "Silero VAD загружен")

    def _contains_speech(self, wav_bytes: bytes) -> bool:
        """Проверяет через Silero VAD, есть ли речь в аудио"""
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            raw = wf.readframes(wf.getnframes())

        audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_np)

        speech_timestamps = get_speech_timestamps(
            audio_tensor,
            self.vad_model,
            sampling_rate=self.sample_rate,
            threshold=self.vad_threshold,
            min_speech_duration_ms=int(self.min_speech_duration * 1000),
        )

        if not speech_timestamps:
            return False

        total_speech_sec = sum(
            s["end"] - s["start"] for s in speech_timestamps
        ) / self.sample_rate

        return total_speech_sec >= self.min_speech_duration

    def _callback(self, recognizer, audio):
        try:
            wav_data = audio.get_wav_data()

            if not self._contains_speech(wav_data):
                BasicUtils.logger("Whisper", "DEBUG", "VAD: речь не обнаружена, пропускаем")
                return

            segments, _ = self.model.transcribe(
                io.BytesIO(wav_data),
                beam_size=5,
                language="ru",
                no_speech_threshold=0.45,
                log_prob_threshold=-0.8,
                compression_ratio_threshold=2.4,
                condition_on_previous_text=False,
            )

            for segment in segments:
                text = segment.text.strip()
                if not text or segment.no_speech_prob > 0.6:
                    continue
                BasicUtils.logger("Whisper", "INFO", f"Распознано: {text}")
                global_signals.voice_message_recognized.emit(text)

        except Exception as e:
            BasicUtils.logger("Whisper", "ERROR", f"Ошибка: {e}")

    def start_recognition(self):
        if self.stop_func is not None:
            return
        BasicUtils.logger("Whisper", "INFO", "Микрофон включен")
        with sr.Microphone(sample_rate=self.sample_rate) as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        self.stop_func = self.recognizer.listen_in_background(
            sr.Microphone(sample_rate=self.sample_rate), self._callback
        )

    def stop_recognition(self):
        if self.stop_func:
            self.stop_func(wait_for_stop=False)
            self.stop_func = None
            BasicUtils.logger("SpeechRecognition", "INFO", "Микрофон выключен")