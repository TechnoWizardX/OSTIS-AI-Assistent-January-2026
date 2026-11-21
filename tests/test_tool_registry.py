"""Тесты реестра тулов: дискавери, метаданные и дефолты параметров."""
import pytest

from src.tools import registry
from src.tools.base import tool
from src.utils.system_control import ControlSystem

# Все имена, которые раньше жили в actions_mapping, должны найтись в реестре.
EXPECTED_TOOL_NAMES = {
    "open_site", "close_current_tab",
    "open_application", "close_application", "reload_application",
    "minimize_all_windows", "toggle_always_on_top", "set_window_state",
    "set_window_transparency", "snap_window",
    "set_brightness", "set_volume",
    "os_sleep", "os_shutdown", "cancel_shutdown", "os_restart",
    "insert_text", "empty_recycle_bin", "get_system_stats",
    "disconnect_wifi", "connect_wifi", "set_airplane_mode",
    "create_quick_note", "open_directory", "take_screenshot", "media_control",
}


def test_discovery_registers_all_known_tools():
    names = {spec.name for spec in registry.get_all_tools()}
    assert EXPECTED_TOOL_NAMES <= names


def test_every_tool_is_self_describing():
    for spec in registry.get_all_tools():
        assert spec.description, f"У тула {spec.name} нет описания"
        assert spec.func is not None, f"У тула {spec.name} нет функции"
        assert spec.keywords, f"У тула {spec.name} нет ключевых слов для поиска"


def test_blocking_tools_match_old_blocking_set():
    """Тулы из старого BLOCKING_ACTIONS помечены blocking=True у остальных False."""
    blocking_names = {spec.name for spec in registry.get_all_tools() if spec.blocking}
    assert blocking_names == {"get_system_stats", "reload_application", "insert_text"}


def test_core_tools_exist():
    core = registry.get_core_tools()
    assert 3 <= len(core) <= 5
    assert all(spec.core for spec in core)


def test_unknown_tool_returns_none():
    assert registry.get_tool("definitely_not_a_tool") is None


def test_duplicate_registration_is_rejected():
    with pytest.raises(ValueError):
        @tool(name="open_site", description="дубль существующего тула")
        def duplicate(params: dict):
            pass


def test_shutdown_default_delay(monkeypatch):
    """Дефолты из старых лямбд actions_mapping сохранены в туловых функциях."""
    calls = {}
    monkeypatch.setattr(ControlSystem, "os_shutdown", lambda delay=60: calls.update(delay=delay))
    registry.get_tool("os_shutdown").func({})
    assert calls["delay"] == 60


def test_media_control_default_action(monkeypatch):
    calls = {}
    monkeypatch.setattr(ControlSystem, "media_control", lambda action="play": calls.update(action=action))
    registry.get_tool("media_control").func({})
    assert calls["action"] == "play"


def test_set_brightness_default_level(monkeypatch):
    calls = {}
    monkeypatch.setattr(ControlSystem, "set_brightness", lambda level=50: calls.update(level=level))
    registry.get_tool("set_brightness").func({})
    assert calls["level"] == 50
