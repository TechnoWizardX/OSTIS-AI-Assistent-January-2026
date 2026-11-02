import json
import os
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv

SETTINGS_CONFIG_FILE = Path(__file__).parent / "data" / "settings_config.json"
SETTINGS_CONFIG_FILE.parent.mkdir(exist_ok=True)

DEFAULT_SETTINGS_CONFIG = {
    "Wifi": {
        "ssid": "",
        "password": ""
    },
    "use_online_model": True,
    "allow_online_model_user_info": False,
    "theme": "dark",
    "last_message_send": None,
    "recording_enabled": False,
    "camera_index": 0,
    "microphone_index": 0,
    "voice_send_directly": False,
    "gesture_send_directly": False,
    "recognition_model": "faster-whisper",
    "available_silero_voices": {
        "Сеня": "xenia",
        "Евгений": "eugene",
        "Байя": "baya",
        "Айдар": "aidar",
        "Ксения": "kseniya"
    },
    "available_silero_voices_reversed": {
        "xenia": "Сеня",
        "eugene": "Евгений",
        "baya": "Байя",
        "aidar": "Айдар",
        "kseniya": "Ксения"
    },
    "tts_voice": "kseniya",
    "tts_model": "silero",
    "tts_speed": 1,
    "tts_recommendation_always": False,
    "available_recognition_models": [
        "faster-whisper"
    ],
    "speaker_index": 0,
    "recommended_methods": [
        "text",
        "gesture",
        "voice",
        "tts"
    ],
    "auto_tts": False
}

def _default_settings_config() -> dict:
    return deepcopy(DEFAULT_SETTINGS_CONFIG)


def save_settings_config(settings_config: dict) -> None:
    """Сохраняет настройки в settings_config.json."""
    SETTINGS_CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(SETTINGS_CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(settings_config, file, ensure_ascii=False, indent=4)


def load_settings_config() -> dict:
    """Загружает настройки из settings_config.json. Если файла нет или JSON повреждён, создаёт дефолтный файл."""
    if not SETTINGS_CONFIG_FILE.exists():
        settings_config = _default_settings_config()
        save_settings_config(settings_config)
        return settings_config

    try:
        with open(SETTINGS_CONFIG_FILE, "r", encoding="utf-8") as file:
            settings_config = json.load(file)
    except (json.JSONDecodeError, OSError):
        settings_config = _default_settings_config()
        save_settings_config(settings_config)
        return settings_config

    if not isinstance(settings_config, dict):
        settings_config = _default_settings_config()
        save_settings_config(settings_config)
        return settings_config

    changed = False
    for key, value in DEFAULT_SETTINGS_CONFIG.items():
        if key not in settings_config:
            settings_config[key] = deepcopy(value)
            changed = True

    if changed:
        save_settings_config(settings_config)

    return settings_config


def get_settings_config_value(key: str):
    """Возвращает значение конкретного параметра из настроек."""
    settings_config = load_settings_config()
    return settings_config.get(key, DEFAULT_SETTINGS_CONFIG.get(key))


def set_settings_config_value(key: str, value):
    """Устанавливает и сохраняет значение параметра в настройках."""
    settings_config = load_settings_config()
    settings_config[key] = value
    save_settings_config(settings_config)


def get_env_variable(name: str) -> str:
        """Получает значение переменной окружения. Если переменная не найдена, возвращает пустую строку."""
        load_dotenv() 
        return os.getenv(name, "")