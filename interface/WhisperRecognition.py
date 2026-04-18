import io
import speech_recognition as sr
from faster_whisper import WhisperModel
from BasicUtils import BasicUtils,global_signals

class WhisperRecognition():
    def __init__(self, model: str = "small", device: str = "cpu", model_download_root: str = None, compute_type: str = "int8"): 
        self.model = WhisperModel(model, device=device, compute_type=compute_type, download_root=model_download_root)
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2 
        self.stop_func = None # Здесь будет функция для остановки

    def _callback(self, recognizer, audio):
        """Функция, которая вызывается автоматически, когда фраза записана"""
        try:
            # Превращаем аудио в байты для Whisper
            wav_data = io.BytesIO(audio.get_wav_data())
            segments, _ = self.model.transcribe(wav_data, beam_size=5, language="ru")
            
            for segment in segments:
                if segment.text.strip():
                    BasicUtils.logger(self, "Whisper", "INFO", f"Распознано: {segment.text}")    
                    global_signals.voice_message_recognized.emit(segment.text)
        except Exception as e:
            BasicUtils.logger(self, "Whisper", "ERROR", f"Ошибка: {e}")

    def start_recognition(self):
        if self.stop_func is not None:
            return # Уже запущено
            
        BasicUtils.logger(self, "SpeechRecognition", "INFO", "Микрофон включен")
        with sr.Microphone(sample_rate=16000) as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        # Запускаем фоновый поток. Он сам вызывает _callback, когда слышит речь.
        self.stop_func = self.recognizer.listen_in_background(sr.Microphone(sample_rate=16000), self._callback)

    def stop_recognition(self):
        if self.stop_func:
            self.stop_func(wait_for_stop=False) # Мгновенно прекращаем прослушивание
            self.stop_func = None
            BasicUtils.logger(self, "SpeechRecognition", "INFO", "Микрофон выключен")