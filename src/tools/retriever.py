"""Подбор релевантных тулов по запросу пользователя (RAG).

Скоринг: лексика (ключевые слова, основы слов) всегда; семантика —
косинус вектора запроса и векторов тулов через Ollama. Без Ollama
работает чистая лексика.
"""
from __future__ import annotations

import re

from src.tools import registry
from src.tools.base import ToolSpec
from src.tools.embeddings import OllamaEmbedder, ToolVectorStore, cosine_similarity

# Не более стольких релевантных тулов подставляется в промпт за один запрос.
TOP_K = 6
# Порог откалиброван на реальных косинусах: релевантные ≥ 0.85, болтовня ≤ 0.3.
RELEVANCE_THRESHOLD = 0.7
# Семантическая близость (0..1) добавляется к лексическому скору с этим весом.
_SEMANTIC_WEIGHT = 1.0
# Точное совпадение слова запроса с ключевым словом весит больше совпадения по корню.
_EXACT_MATCH_WEIGHT = 1.0
_STEM_MATCH_WEIGHT = 0.5
# Слова описания и примеров — вторичная подсказка после ключевых слов.
_DESCRIPTION_MATCH_WEIGHT = 0.3
# Минимальная общая часть слова для совпадения по корню.
_STEM_MIN_LENGTH = 4

_PUNCTUATION = re.compile(r"[^\w\s]")


def _normalize(text: str) -> list[str]:
    """Приводит текст к набору токенов: нижний регистр, ё→е, без пунктуации."""
    text = text.lower().replace("ё", "е")
    return _PUNCTUATION.sub(" ", text).split()


def _stems_intersect(token: str, candidates: frozenset[str]) -> bool:
    """Проверяет совпадение по общей части слова (например, «выключить» ↔ «выключи»)."""
    for candidate in candidates:
        stem_length = min(len(token), len(candidate))
        if stem_length >= _STEM_MIN_LENGTH and token[:stem_length] == candidate[:stem_length]:
            return True
    return False


class ToolRetriever:
    """Подбирает тулы, релевантные запросу пользователя."""

    def __init__(self):
        # Индекс и векторы строятся лениво, при первом score().
        self._lexical_index: dict[str, tuple[frozenset, frozenset]] | None = None
        self._embedder = OllamaEmbedder()
        self._vector_store = ToolVectorStore(self._embedder)

    def select(self, user_text: str) -> list[ToolSpec]:
        """Возвращает тулы с релевантностью выше порога, лучшие первыми."""
        scored = self.score(user_text)
        relevant = [
            spec for spec, score in scored if score >= RELEVANCE_THRESHOLD
        ]
        return relevant[:TOP_K]

    def score(self, user_text: str) -> list[tuple[ToolSpec, float]]:
        """Скоринг всех тулов (лексика + семантика), отсортирован по убыванию."""
        index = self._get_lexical_index()
        query_tokens = _normalize(user_text)
        scored = [
            (spec, self._score_tool(spec, index[spec.name], query_tokens))
            for spec in registry.get_all_tools()
        ]

        query_vector = self._embedder.embed(user_text)
        if query_vector is None:
            scored.sort(key=lambda item: item[1], reverse=True)
            return scored

        tool_vectors = self._vector_store.tool_vectors()
        if not tool_vectors:
            scored.sort(key=lambda item: item[1], reverse=True)
            return scored

        combined = []
        for spec, lexical_score in scored:
            tool_vector = tool_vectors.get(spec.name)
            semantic_score = cosine_similarity(query_vector, tool_vector) if tool_vector else 0.0
            combined.append((spec, lexical_score + _SEMANTIC_WEIGHT * max(0.0, semantic_score)))
        combined.sort(key=lambda item: item[1], reverse=True)
        return combined

    def _get_lexical_index(self) -> dict[str, tuple[frozenset, frozenset]]:
        """Токены ключевых слов и описаний для каждого тула."""
        if self._lexical_index is None:
            self._lexical_index = {
                spec.name: (
                    frozenset(
                        token
                        for keyword in spec.keywords
                        for token in _normalize(keyword)
                    ),
                    frozenset(_normalize(spec.description))
                    | frozenset(
                        token
                        for example in spec.examples
                        for token in _normalize(example)
                    ),
                )
                for spec in registry.get_all_tools()
            }
        return self._lexical_index

    def _score_tool(
        self,
        spec: ToolSpec,
        index: tuple[frozenset, frozenset],
        query_tokens: list[str],
    ) -> float:
        """Релевантность тула: каждое слово запроса учитывается один раз."""
        keyword_tokens, description_tokens = index
        score = 0.0
        for token in query_tokens:
            if token in keyword_tokens:
                score += _EXACT_MATCH_WEIGHT
            elif _stems_intersect(token, keyword_tokens):
                score += _STEM_MATCH_WEIGHT
            elif token in description_tokens:
                score += _DESCRIPTION_MATCH_WEIGHT
            elif _stems_intersect(token, description_tokens):
                score += _DESCRIPTION_MATCH_WEIGHT / 2
        return score
