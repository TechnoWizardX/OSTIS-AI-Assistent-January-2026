import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from BasicUtils import BasicUtils, DataBaseEditor
from .QwenRequest import QwenRequest

class RecommendationManager(QObject):
    """Управляет анализом профиля, кэшированием и выдачей рекомендаций."""
    recommendation_ready = pyqtSignal(str)  # Отправляет готовую текстовую рекомендацию
    analysis_failed = pyqtSignal(str)

    CACHE_PATH = Path(__file__).parent.parent / "data" / "recommendation.json"

    def __init__(self, qwen_request: QwenRequest):
        super().__init__()
        self.qwen_request = qwen_request
        self.db = DataBaseEditor()
        
        # 🔹 Подключаемся к сигналам QwenRequest вместо callback
        self.qwen_request.recommendation_ready.connect(self._on_ai_result)
        self.qwen_request.analysis_error.connect(self._on_ai_error)

    def analyze(self):
        """Запускает процесс анализа профиля."""
        try:
            res = self.db.get_data("Users", "dysfunctions", 0)
            disease = res[0][0].strip() if res and res[0][0] else ""

            if not disease or disease == "Не указано":
                BasicUtils.logger("RecManager", "INFO", "Поле нарушений пустое. Анализ пропущен.")
                return

            # 🔍 Проверка кэша
            cached = self._load_cache()
            if cached.get("disease") == disease and "result" in cached:
                BasicUtils.logger("RecManager", "INFO", f"✅ Загружена рекомендация из кэша: '{disease}'")
                self.recommendation_ready.emit(cached["result"])
                return

            # 🤖 Запуск AI-анализа (БЕЗ callback!)
            BasicUtils.logger("RecManager", "INFO", f"Запуск AI-анализа для: '{disease}'")
            self.qwen_request.get_input_recommendation(disease)

        except Exception as e:
            BasicUtils.logger("RecManager", "ERROR", f"Ошибка запуска анализа: {e}")
            self.analysis_failed.emit(str(e))

    def _on_ai_result(self, result_text: str):
        """Вызывается автоматически через сигнал, когда модель возвращает ответ."""
        try:
            disease = self.db.get_data("Users", "dysfunctions", 0)[0][0].strip()
            self._save_cache(disease, result_text)
            self.recommendation_ready.emit(result_text)
        except Exception as e:
            BasicUtils.logger("RecManager", "ERROR", f"Ошибка обработки результата AI: {e}")
            self.analysis_failed.emit(str(e))

    def _on_ai_error(self, error_msg: str):
        """Обрабатывает ошибки инференса."""
        BasicUtils.logger("RecManager", "ERROR", f"Сбой AI: {error_msg}")
        # Отправляем в ядро fallback-текст, чтобы интерфейс не завис
        self.recommendation_ready.emit("Рекомендуется текстовый и голосовой ввод")

    def _load_cache(self) -> dict:
        if self.CACHE_PATH.exists():
            with open(self.CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self, disease: str, result: str):
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"disease": disease, "result": result}, f, ensure_ascii=False, indent=4)
        BasicUtils.logger("RecManager", "INFO", "Рекомендация сохранена в кэш.")