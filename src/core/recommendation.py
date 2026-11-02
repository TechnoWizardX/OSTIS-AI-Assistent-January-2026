"""
Модуль рекомендаций методов ввода на основе диагноза пользователя.

Публичный интерфейс
-------------------
    AccessibilityRecommender   — фасад; вызывайте request_recommendation()
    RecommendationResult       — dataclass с полями methods / user_text
    METHOD_LABELS              — человекочитаемые названия методов
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.core.llm_client import LocalModel, MedicalAPI
from src.utils.config import get_settings_config_value
from src.utils.database import DataBaseEditor
from src.utils.logger import logger
from src.utils.network import \
    has_internet  # тонкая обёртка над BasicUtils.has_internet

# ---------------------------------------------------------------------------
# Пути и константы
# ---------------------------------------------------------------------------
_DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "..", "src", "data")
CACHE_PATH  = os.path.join(_DATA_DIR, "accessibility_cache.json")
PROMPT_PATH = os.path.join(_DATA_DIR, "recommendation_prompt.md")

METHOD_LABELS: dict[str, str] = {
    "voice":   "Голосовой ввод",
    "gesture": "Жестовый ввод",
    "text":    "Текстовый ввод",
    "tts":     "Озвучка",
}

_FALLBACK_SYSTEM_PROMPT = "Ты помощник по доступности. Предложи методы ввода для: "
_DEFAULT_RECOMMENDATION_PROMPT = """Ты помощник по доступности.
Предложи подходящие методы взаимодействия только из списка: voice, gesture, text, tts.
Ответь строго в формате:
METHODS: voice,gesture,text,tts
TEXT: краткое объяснение на русском
"""


def _ensure_data_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _ensure_text_file(path: str, default_content: str) -> str:
    _ensure_data_dir()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(default_content)
        return default_content

    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
            return content or default_content
    except OSError:
        return default_content


# ---------------------------------------------------------------------------
# Dataclass результата
# ---------------------------------------------------------------------------

@dataclass
class RecommendationResult:
    methods:   List[str]
    user_text: str


# ---------------------------------------------------------------------------
# Парсер ответа LLM
# ---------------------------------------------------------------------------

class RecommendationParser:
    """Парсит ответ LLM — JSON или текст с метками METHODS / TEXT."""

    @staticmethod
    def parse(raw: str) -> RecommendationResult:
        # 1. Пробуем JSON
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data    = json.loads(match.group())
                methods = data.get("METHODS") or data.get("methods") or ""
                text    = data.get("TEXT")    or data.get("text")    or raw
                return RecommendationResult(
                    [x.strip() for x in methods.split(",") if x.strip()], text
                )
            except json.JSONDecodeError:
                pass

        # 2. Текстовые метки
        methods, text = [], raw
        for line in raw.splitlines():
            upper = line.upper()
            if upper.startswith("METHODS:"):
                methods = [m.strip() for m in line[8:].split(",") if m.strip()]
            elif upper.startswith("TEXT:"):
                text = line[5:].strip()
        return RecommendationResult(methods, text)


# ---------------------------------------------------------------------------
# Кэш рекомендаций
# ---------------------------------------------------------------------------

class RecommendationCache:
    """Простой файловый кэш с TTL (по умолчанию 2 часа)."""

    def __init__(self, path: str = CACHE_PATH, ttl_hours: int = 2):
        self._path = path
        self._ttl  = timedelta(hours=ttl_hours)
        _ensure_data_dir()
        self._data = self._load()

    # ------------------------------------------------------------------
    def get(self, diagnosis: str) -> Optional[RecommendationResult]:
        key   = self._key(diagnosis)
        entry = self._data.get(key)
        if entry:
            age = datetime.now() - datetime.fromisoformat(entry["ts"])
            if age < self._ttl:
                return RecommendationResult(entry["methods"], entry["text"])
        return None

    def set(self, diagnosis: str, result: RecommendationResult, model: str) -> None:
        key = self._key(diagnosis)
        self._data[key] = {
            "methods": result.methods,
            "text":    result.user_text,
            "model":   model,
            "ts":      datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    @staticmethod
    def _key(diagnosis: str) -> str:
        return hashlib.sha256(diagnosis.strip().lower().encode()).hexdigest()

    def _load(self) -> dict:
        if not os.path.exists(self._path):
            self._write_empty_cache()
            return {}

        try:
            with open(self._path, encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            self._write_empty_cache()
            return {}

    def _write_empty_cache(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump({}, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Рабочий поток
# ---------------------------------------------------------------------------

class _RecommendationWorker(QThread):
    """Фоновый запрос к LLM (не использовать напрямую)."""

    finished = pyqtSignal(str)
    failed   = pyqtSignal(str)

    def __init__(self, user_prompt: str, system_prompt: str,
                 api_key: str, model: str, online: bool, parent=None):
        super().__init__(parent)
        self._user_prompt   = user_prompt
        self._system_prompt = system_prompt
        self._api_key       = api_key
        self._model         = model
        self._online        = online

    def run(self):
        try:
            client = (MedicalAPI(self._api_key, self._model)
                      if self._online else LocalModel(self._model))
            response = client.generate(self._user_prompt,
                                       system=self._system_prompt)
            if str(response).startswith(("⚠️", "❌")):
                self.failed.emit(response)
            else:
                self.finished.emit(response)
        except Exception as exc:
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Публичный фасад
# ---------------------------------------------------------------------------

class AccessibilityRecommender(QObject):
    """Запрашивает рекомендации методов ввода для пользователя.

    Сигналы
    -------
    recommendation_obtained(methods: list[str], text: str)
        Испускается при получении результата (из кэша или от LLM).
    """

    recommendation_obtained = pyqtSignal(object, str)

    def __init__(self,
                 api_key:      str = None,
                 online_model: str = "anthropic/claude-3-haiku",
                 offline_model: str = "qwen2.5:3b",
                 parent: QObject = None):
        super().__init__(parent)
        self._api_key      = api_key or os.getenv("OPENROUTER_API_KEY")
        self._online_model = online_model
        self._offline_model = offline_model
        self._cache        = RecommendationCache()
        self._db           = DataBaseEditor()
        self._worker: Optional[_RecommendationWorker] = None

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def request_recommendation(self, user_id: int = 0, force: bool = False) -> None:
        """Запустить получение рекомендации для пользователя ``user_id``.

        Параметры
        ---------
        user_id : int
            Идентификатор строки в таблице Users.
        force : bool
            Игнорировать кэш и запросить заново.
        """
        # 1. Читаем диагноз из БД
        rows  = self._db.get_data("Users", "dysfunctions", user_id)
        diag  = str(rows[0][0]).strip() if rows and rows[0][0] else None

        if not diag or diag.lower() == "не указано":
            logger("Recommender", "INFO", "Диагноз не указан — все методы доступны")
            self.recommendation_obtained.emit([], "Нарушения не указаны. Все методы доступны.")
            return

        # 2. Кэш
        if not force:
            cached = self._cache.get(diag)
            if cached:
                logger("Recommender", "INFO", "Результат из кэша")
                self.recommendation_obtained.emit(cached.methods, cached.user_text)
                return

        # 3. Выбираем модель
        use_online = bool(get_settings_config_value("use_online_model") and has_internet())
        model      = self._online_model if use_online else self._offline_model

        # 4. Загружаем системный промпт
        sys_prompt = _ensure_text_file(PROMPT_PATH, _DEFAULT_RECOMMENDATION_PROMPT)
        if sys_prompt == _DEFAULT_RECOMMENDATION_PROMPT:
            logger("Recommender", "WARNING",
                   f"Используется базовый промпт рекомендаций: {PROMPT_PATH}")

        user_prompt = f"Особенности здоровья: {diag}. Предложи лучшие методы взаимодействия."

        # 5. Запускаем поток (защита от двойного запуска)
        if self._worker and self._worker.isRunning():
            logger("Recommender", "WARNING", "Предыдущий запрос ещё выполняется")
            return

        self._worker = _RecommendationWorker(
            user_prompt, sys_prompt,
            self._api_key, model, use_online,
            parent=self,
        )
        self._worker.finished.connect(lambda raw: self._on_success(raw, diag, model))
        self._worker.failed.connect(lambda err: logger("Recommender", "ERROR", err))
        self._worker.start()
        logger("Recommender", "INFO", f"Запрос отправлен (модель: {model})")

    # ------------------------------------------------------------------
    # Приватные обработчики
    # ------------------------------------------------------------------

    def _on_success(self, raw: str, diagnosis: str, model: str) -> None:
        result = RecommendationParser.parse(raw)
        self._cache.set(diagnosis, result, model)
        self.recommendation_obtained.emit(result.methods, result.user_text)