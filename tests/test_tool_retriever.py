"""Тесты подбора релевантных тулов и динамического блока действий в промпте."""
from src.services.ai_service.intent_handler import IntentHandler
from src.tools.retriever import TOP_K, ToolRetriever


def test_shutdown_request_finds_power_tools():
    names = {spec.name for spec in ToolRetriever().select("выключи компьютер через 5 минут")}
    assert "os_shutdown" in names


def test_brightness_request_finds_brightness_tool():
    names = {spec.name for spec in ToolRetriever().select("сделай экран ярче")}
    assert "set_brightness" in names


def test_chitchat_selects_nothing():
    """Болтовня не должна подтягивать ни одного тула выше порога."""
    assert ToolRetriever().select("привет, как дела?") == []


def test_select_is_capped():
    relevant = ToolRetriever().select("открой браузер и запусти приложение и выключи компьютер")
    assert len(relevant) <= TOP_K


def test_prompt_contains_relevant_tools():
    handler = IntentHandler(api_key="test-key")
    prompt = handler._build_prompt("выключи компьютер", "")
    assert "ДОСТУПНЫЕ ДЕЙСТВИЯ" in prompt
    assert "os_shutdown" in prompt


def test_prompt_keeps_core_tools_and_drops_irrelevant():
    handler = IntentHandler(api_key="test-key")
    prompt = handler._build_prompt("привет", "")
    # Ядро присутствует всегда, нерелевантные тулы не подставились.
    assert "open_application" in prompt
    assert "os_shutdown" not in prompt


def test_prompt_tool_line_format():
    handler = IntentHandler(api_key="test-key")
    prompt = handler._build_prompt("выключи компьютер", "")
    assert "- os_shutdown — " in prompt
    assert "params: delay" in prompt


def test_send_request_injects_relevant_tools(monkeypatch):
    handler = IntentHandler(api_key="test-key")
    captured = {}
    monkeypatch.setattr(
        handler,
        "_send_offline_request",
        lambda prompt, model: captured.update(prompt=prompt) or {"message": "ок", "tasks": []},
    )
    handler.send_request("выключи компьютер", "", use_online=False)
    assert "os_shutdown" in captured["prompt"]
    assert "Сообщение пользователя:" in captured["prompt"]
