"""Семантический подбор тулов: эмбеддинги через локальный Ollama.

Векторы тулов считаются одним батч-запросом и кешируются в AppLocalData;
на каждый запрос считается только вектор короткой фразы.
"""
from __future__ import annotations

import json
import math
import time

import requests

from src.tools import registry
from src.tools.base import ToolSpec
from src.utils.logger import logger
from src.utils.user_data import get_user_data_file

# Лёгкая многоязычная модель, хороша для русского. Установка: ollama pull paraphrase-multilingual
EMBEDDING_MODEL = "paraphrase-multilingual"
# 127.0.0.1 вместо localhost: его резолв в Python на Windows стоит ~2 с.
OLLAMA_EMBED_URL = "http://127.0.0.1:11434/api/embed"

# Таймаут вектора запроса: при зависшей Ollama быстро откатываемся на лексику.
_QUERY_TIMEOUT_SECONDS = 10
# Батч тулов может включать холодную загрузку модели — таймаут с запасом.
_BATCH_TIMEOUT_SECONDS = 30
# Столько секунд после ошибки не пытаемся получить эмбеддинги снова.
_RETRY_COOLDOWN_SECONDS = 300


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Косинусная близость без numpy — размерности малы, хватает питона."""
    if len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def tool_text(spec: ToolSpec) -> str:
    """Текст тула для векторизации: описание + ключевые слова + примеры."""
    return " ".join(
        [spec.description, " ".join(spec.keywords), " ".join(spec.examples)]
    )


class OllamaEmbedder:
    """Получает векторы текстов через Ollama."""

    def __init__(self, model: str = EMBEDDING_MODEL):
        self.model = model
        # После сбоя семантика отключается на время, чтобы не долбить Ollama.
        self._unavailable_until = 0.0

    def is_available(self) -> bool:
        return time.monotonic() >= self._unavailable_until

    def embed(self, text: str) -> list[float] | None:
        """Вектор одного текста или None, если эмбеддинги сейчас недоступны."""
        vectors = self.embed_batch([text])
        return vectors[0] if vectors else None

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        """Векторы пачки текстов одним запросом или None при недоступности."""
        if not self.is_available():
            return None
        timeout = _BATCH_TIMEOUT_SECONDS if len(texts) > 1 else _QUERY_TIMEOUT_SECONDS
        try:
            response = requests.post(
                OLLAMA_EMBED_URL,
                json={"model": self.model, "input": texts},
                timeout=timeout,
            )
            if response.status_code == 200:
                embeddings = response.json().get("embeddings")
                if embeddings and len(embeddings) == len(texts):
                    return embeddings
                logger("ToolEmbedder", "WARNING", f"Ollama вернула эмбеддинги не в полном объёме для модели {self.model}")
            else:
                logger(
                    "ToolEmbedder",
                    "WARNING",
                    f"Модель {self.model} недоступна (HTTP {response.status_code}). "
                    f"Скачайте её: ollama pull {self.model}",
                )
        except Exception as error:
            # Семантика — усилитель, её сбой не должен ломать запрос интента.
            logger("ToolEmbedder", "WARNING", f"Ollama недоступна, семантический подбор пропущен: {error}")
        self._unavailable_until = time.monotonic() + _RETRY_COOLDOWN_SECONDS
        return None


class ToolVectorStore:
    """Векторы тулов: один расчёт, кеш в AppLocalData, инвалидация по хешу каталога."""

    def __init__(self, embedder: OllamaEmbedder):
        self._embedder = embedder
        # None — ещё не загружены; {} — недоступны, пробуем позже.
        self._vectors: dict[str, list[float]] | None = None
        self._retry_after = 0.0

    def tool_vectors(self) -> dict[str, list[float]]:
        """Векторы всех тулов; пустой словарь, если эмбеддинги недоступны."""
        if self._vectors is None or (
            not self._vectors and time.monotonic() >= self._retry_after
        ):
            self._vectors = self._load_or_compute() or {}
            if not self._vectors:
                self._retry_after = time.monotonic() + _RETRY_COOLDOWN_SECONDS
        return self._vectors

    def _load_or_compute(self) -> dict[str, list[float]] | None:
        """Загружает кеш по хешу каталога или считает векторы через Ollama."""
        if not self._embedder.is_available():
            return None

        signature = registry.catalog_signature()
        cached = self._load_cache(signature)
        if cached is not None:
            return cached

        specs = registry.get_all_tools()
        # Весь каталог одним батч-запросом — доли секунды.
        vectors_list = self._embedder.embed_batch([tool_text(spec) for spec in specs])
        if vectors_list is None:
            # Эмбеддинги недоступны — кеш не пишем, вернёмся после кулдауна.
            return None

        vectors = {
            spec.name: vector for spec, vector in zip(specs, vectors_list)
        }
        self._save_cache(signature, vectors)
        logger("ToolEmbedder", "INFO", f"Рассчитаны эмбеддинги для {len(vectors)} тулов")
        return vectors

    def _cache_path(self):
        return get_user_data_file("tool_embeddings.json")

    def _load_cache(self, signature: str) -> dict[str, list[float]] | None:
        try:
            path = self._cache_path()
            if not path.exists():
                return None
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("model") == self._embedder.model and data.get("signature") == signature:
                return data.get("vectors", {})
        except (OSError, json.JSONDecodeError) as error:
            logger("ToolEmbedder", "WARNING", f"Кеш эмбеддингов не читается, будет пересчёт: {error}")
        return None

    def _save_cache(self, signature: str, vectors: dict[str, list[float]]) -> None:
        try:
            with self._cache_path().open("w", encoding="utf-8") as f:
                json.dump(
                    {"model": self._embedder.model, "signature": signature, "vectors": vectors},
                    f,
                    ensure_ascii=False,
                )
        except OSError as error:
            logger("ToolEmbedder", "WARNING", f"Не удалось сохранить кеш эмбеддингов: {error}")
