"""Тесты семантического подбора тулов: эмбеддинги, кеш, откат на лексику."""
import json

import pytest

from src.tools import embeddings
from src.tools.embeddings import OllamaEmbedder, ToolVectorStore
from src.tools.retriever import ToolRetriever


class StubEmbedder:
    """Эмбеддер-заглушка: «яркие» тексты в один вектор, остальные в другой."""

    model = "stub"

    def __init__(self, available=True):
        self.available = available
        self.calls = 0

    def is_available(self):
        return self.available

    def embed(self, text):
        self.calls += 1
        if not self.available:
            return None
        # Матчинг по основе слова: «освещенности» и «освещенность» — одна основа.
        bright = "яркост" in text or "освещенност" in text or "экрана" in text
        return [1.0, 0.0] if bright else [0.0, 1.0]


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Кеш эмбеддингов кладём во временную папку вместо AppLocalData."""
    monkeypatch.setattr(embeddings, "get_user_data_file", lambda name: tmp_path / name)
    return tmp_path


def make_retriever(stub):
    retriever = ToolRetriever()
    retriever._embedder = stub
    retriever._vector_store = ToolVectorStore(stub)
    return retriever


def test_semantic_finds_paraphrase(cache_dir):
    """«Уровень освещенности дисплея» лексикой не ловится, семантикой — да."""
    retriever = make_retriever(StubEmbedder())
    names = {spec.name for spec in retriever.select("уровень освещенности дисплея повыше")}
    assert "set_brightness" in names


def test_fallback_to_lexical_when_ollama_down(cache_dir):
    retriever = make_retriever(StubEmbedder(available=False))
    names = {spec.name for spec in retriever.select("выключи компьютер через 5 минут")}
    assert "os_shutdown" in names


def test_unavailable_embedder_is_not_polled(cache_dir):
    """При кулдауне эмбеддер не опрашивается ни для тула, ни для запроса."""
    stub = StubEmbedder(available=False)
    store = ToolVectorStore(stub)
    assert store.tool_vectors() == {}
    assert stub.calls == 0


def test_tool_vectors_cached_on_disk(cache_dir):
    """Первый расчёт идёт через эмбеддер, второй — из кеша без запросов."""
    stub = StubEmbedder()
    ToolVectorStore(stub).tool_vectors()
    first_calls = stub.calls
    assert first_calls > 0

    stub2 = StubEmbedder()
    vectors = ToolVectorStore(stub2).tool_vectors()
    assert stub2.calls == 0
    assert len(vectors) == first_calls


def test_cache_invalidated_by_signature_change(cache_dir):
    """Кеш со старым хешем каталога не используется — векторы пересчитываются."""
    stub = StubEmbedder()
    ToolVectorStore(stub).tool_vectors()

    cache_path = cache_dir / "tool_embeddings.json"
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    data["signature"] = "stale-signature"
    cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    stub2 = StubEmbedder()
    ToolVectorStore(stub2).tool_vectors()
    assert stub2.calls > 0


def test_catalog_signature_is_stable_and_hex():
    from src.tools import registry

    signature = registry.catalog_signature()
    assert signature == registry.catalog_signature()
    assert len(signature) == 64
    int(signature, 16)


def test_embedding_failure_cooldown(monkeypatch):
    """После сбоя OllamaEmbedder не ходит в сеть до конца кулдауна."""
    def fail_post(*args, **kwargs):
        raise ConnectionError("refused")

    monkeypatch.setattr(embeddings.requests, "post", fail_post)

    embedder = OllamaEmbedder(model="stub")
    assert embedder.embed("тест") is None
    assert embedder.is_available() is False
    # Второй вызов сразу отдаёт None, не делая сетевой запрос.
    assert embedder.embed("тест") is None
