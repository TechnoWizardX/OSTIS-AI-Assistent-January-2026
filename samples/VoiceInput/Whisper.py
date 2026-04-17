import io
import os
import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel

def main():
    # 1. Настройка модели faster-whisper
    # Модели: 'tiny', 'base', 'small', 'medium', 'large-v3'
    # device="cuda" если есть NVIDIA GPU, иначе "cpu"
    # compute_type="int8" позволяет модели работать быстрее и потреблять меньше RAM
    model_size = "small"
    print(f"Загрузка модели {model_size}...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root="./models")

    # 2. Настройка распознавателя речи
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.1  # Пауза в 0.1 сек означает конец фразы
    recognizer.energy_threshold = 300  # Базовый порог громкости

    print("Модель готова. Начинаю прослушивание...")

    with sr.Microphone(sample_rate=16000) as source:
        # Адаптация под фоновый шум
        print("Подстройка под шум... (тишина 1 сек)")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        while True:
            try:
                print("\nГоворите...")
                # Слушаем микрофон, пока не будет зафиксирована фраза
                audio_data = recognizer.listen(source)
                print("Обработка...")

                # 3. Конвертация аудио из формата SpeechRecognition в формат для faster-whisper
                # Получаем байты из AudioData (wav формат)
                wav_data = io.BytesIO(audio_data.get_wav_data())
                
                # Faster-whisper может принимать путь к файлу или бинарный поток. 
                # Мы передаем поток.
                segments, info = model.transcribe(wav_data, beam_size=5, language="ru")

                # 4. Вывод результата
                for segment in segments:
                    # Выводим текст по мере распознавания сегментов
                    print(f"[{info.language}] Распознано: {segment.text.strip()}")

            except KeyboardInterrupt:
                print("Выход из программы...")
                break
            except Exception as e:
                print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()