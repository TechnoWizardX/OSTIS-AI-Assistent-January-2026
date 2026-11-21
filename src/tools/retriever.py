"""Подбор релевантных тулов по запросу пользователя (RAG).

Промпт не раздувается каталогом всех тулов: в него подставляются
универсальные тулы (core) плюс несколько отобранных по релевантности.
Текущий этап — лексический скоринг; семантика подключается поверх него.
"""
from __future__ import annotations

import re

from src.tools import registry
from src.tools.base import ToolSpec

TOP_K = 6
RELEVANCE_THRESHOLD = 0.5
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
        # Индекс строится один раз при первом запросе.
        self._lexical_index: dict[str, tuple[frozenset, frozenset]] | None = None

    def select(self, user_text: str) -> list[ToolSpec]:
        """Возвращает тулы с релевантностью выше порога, лучшие первыми."""
        scored = self.score(user_text)
        relevant = [
            spec for spec, score in scored if score >= RELEVANCE_THRESHOLD
        ]
        return relevant[:TOP_K]

    def score(self, user_text: str) -> list[tuple[ToolSpec, float]]:
        """Лексический скоринг всех тулов, отсортирован по убыванию."""
        index = self._get_lexical_index()
        query_tokens = _normalize(user_text)
        scored = [
            (spec, self._score_tool(spec, index[spec.name], query_tokens))
            for spec in registry.get_all_tools()
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

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
