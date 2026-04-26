import json
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from BasicUtils import BasicUtils

class QwenRequest(QObject):
    """Модуль отправки запросов к локальной модели Qwen для анализа заболеваний."""
    
    # 🔹 Сигналы для безопасной межпоточной коммуникации
    recommendation_ready = pyqtSignal(str)
    analysis_error = pyqtSignal(str)

    def __init__(self, model_path: str, n_threads: int = 4, n_gpu_layers: int = 0):
        super().__init__()  # 🔹 Обязательно инициализируем QObject
        self.model_path = Path(model_path)
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.llm = None
        BasicUtils.logger("QwenRequest", "INFO", f"Менеджер запросов инициализирован: {self.model_path}")

    def _ensure_llm_loaded(self):
        """Ленивая загрузка модели в память."""
        if self.llm is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Файл модели не найден: {self.model_path}")
            try:
                from llama_cpp import Llama
            except ImportError:
                raise RuntimeError("llama-cpp-python не установлен.")
                
            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=512,           # ⚡ Малый контекст для скорости
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False
            )
            BasicUtils.logger("QwenRequest", "INFO", "✅ LLM загружена в память")

    def get_input_recommendation(self, disease: str):
        """Запускает анализ асинхронно. Результат придёт через сигнал recommendation_ready."""
        if not disease or not disease.strip():
            self.recommendation_ready.emit(self._fallback("Диагноз не указан."))
            return

        BasicUtils.logger("QwenRequest", "INFO", f"Анализ заболевания: '{disease[:50]}...'")
        
        def _run():
            try:
                self._ensure_llm_loaded()
                result = self._call_llm(disease)
                self.recommendation_ready.emit(result)  # 🔹 Доставка в главный поток
            except Exception as e:
                BasicUtils.logger("QwenRequest", "ERROR", f"Ошибка запроса: {e}")
                self.analysis_error.emit(str(e))
                self.recommendation_ready.emit(self._fallback(str(e)))
                
        threading.Thread(target=_run, daemon=True, name="QwenAdvisor").start()

    def _call_llm(self, disease: str) -> str:
        prompt = f"""Диагноз пользователя: '{disease}'.

    Выбери ВСЕ подходящие способы ввода: vosk, faster-whisper, gesture, text.
    Верни их через пробел (например: faster-whisper gesture).

    ПРАВИЛА (применяй в указанном порядке):

    1. Если есть ЛЮБЫЕ нарушения речи (дизартрия, заикание, афазия, дисфония, афония, "нарушение речи") → ОБЯЗАТЕЛЬНО добавь faster-whisper. Не удаляй его.
    2. Если есть нарушения зрения (плохое зрение, слепота, слабовидение) → НЕ ДОБАВЛЯЙ text (клавиатуру). Вместо этого используй голос или жесты.
    3. Если есть нарушения рук (паралич, парез, тремор, болезнь Паркинсона, ампутация) → НЕ ДОБАВЛЯЙ gesture, добавь text (если нет речи) или голос.
    4. Если есть глухонемота или полная потеря речи + сохранные руки → добавь gesture.
    5. text (клавиатурный ввод) используй ТОЛЬКО в случаях:
    - одновременное нарушение речи И рук (нет голоса, нет жестов),
    - отсутствие камеры и микрофона,
    - пользователь явно предпочёл текст.
    6. НИКОГДА не возвращай один text, если есть нарушения речи или зрения без полного паралича рук.

    ПРИМЕРЫ (диагноз → ответ):
    - Плохое зрение, нарушение речи → faster-whisper (и возможно gesture)
    - Паралич рук → vosk
    - Глухонемота, зрение хорошее → gesture
    - Дизартрия, руки работают → faster-whisper
    - Чёткая речь, нет нарушений → vosk
    - Плохое зрение, чёткая речь → vosk (а не text!)

    Ответь строго словами через пробел. Без кавычек, точек, пояснений."""

        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": "Ты классификатор. Отвечай только латинскими названиями через пробел: vosk faster-whisper gesture text. Строго соблюдай правила."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=20,
            stop=None
        )
        raw = response["choices"][0]["message"]["content"].strip().strip('"\',. ')
        result = raw if len(raw) >= 3 else self._fallback("Пустой ответ модели")
        BasicUtils.logger("QwenRequest", "INFO", f"Модель выбрала: {result}")
        return result

    def _fallback(self, reason: str) -> str:
        BasicUtils.logger("QwenRequest", "WARNING", f"Возвращён резервный ответ: {reason}")
        return "Рекомендуется текстовый и голосовой ввод"