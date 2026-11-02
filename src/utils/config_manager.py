import json
import os
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.data.templates.data import DEFAULT_CONFIG as CONFIG_TEMPLATE
from src.utils.logger import logger
from src.utils.user_data import get_legacy_data_file, get_user_data_file

DEFAULT_SETTINGS_CONFIG = CONFIG_TEMPLATE


def _validate_template_value(value: Any, template: Any, key: str) -> None:
    if isinstance(template, bool):
        valid = isinstance(value, bool)
    elif isinstance(template, dict):
        valid = isinstance(value, dict)
    elif isinstance(template, list):
        valid = isinstance(value, list)
    elif isinstance(template, int):
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif template is None:
        valid = value is None or isinstance(value, str)
    else:
        valid = isinstance(value, type(template))

    if not valid:
        raise ValueError(f"Invalid value type for config key {key!r}.")

    if isinstance(template, dict):
        for nested_key, nested_value in value.items():
            if nested_key in template:
                _validate_template_value(
                    nested_value,
                    template[nested_key],
                    f"{key}.{nested_key}",
                )
    elif isinstance(template, list) and template:
        for index, item in enumerate(value):
            _validate_template_value(item, template[0], f"{key}[{index}]")


def _merge_defaults(settings: Any) -> dict[str, Any]:
    if not isinstance(settings, dict):
        raise ValueError("Configuration root must be a JSON object.")

    merged = deepcopy(settings)
    for key, default_value in CONFIG_TEMPLATE.items():
        if key not in merged:
            merged[key] = deepcopy(default_value)
            continue

        value = merged[key]
        _validate_template_value(value, default_value, key)
        if isinstance(default_value, dict):
            nested = deepcopy(default_value)
            nested.update(value)
            merged[key] = nested
    return merged


class ConfigManager:
    DEFAULT_CONFIG: dict[str, Any] = CONFIG_TEMPLATE
    _current_config: dict[str, Any] = {}
    _initialized = False

    @classmethod
    def get_config_path(cls) -> Path:
        return get_user_data_file("config.json")

    @classmethod
    def _backup_invalid_config(cls, config_file: Path) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path = config_file.with_name(
            f"{config_file.name}.invalid-{timestamp}"
        )
        shutil.copy2(config_file, backup_path)
        logger(
            "ConfigManager",
            "WARNING",
            f"Invalid configuration was preserved at {backup_path}",
        )

    @classmethod
    def _read_config(cls, config_file: Path) -> dict[str, Any]:
        with config_file.open("r", encoding="utf-8") as file:
            return _merge_defaults(json.load(file))

    @classmethod
    def init_config(cls) -> None:
        if cls._initialized:
            return

        config_file = cls.get_config_path()
        if config_file.exists():
            cls.load()
            return

        legacy_file = get_legacy_data_file("settings_config.json")
        cls._current_config = deepcopy(cls.DEFAULT_CONFIG)
        if legacy_file.is_file():
            try:
                cls._current_config = cls._read_config(legacy_file)
                logger(
                    "ConfigManager",
                    "INFO",
                    f"Migrated settings from {legacy_file}",
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                logger(
                    "ConfigManager",
                    "ERROR",
                    f"Could not migrate settings from {legacy_file}: {error}",
                )
        cls.save()

    @classmethod
    def load(cls) -> None:
        config_file = cls.get_config_path()
        if not config_file.exists():
            cls._initialized = False
            cls.init_config()
            return

        try:
            with config_file.open("r", encoding="utf-8") as file:
                original_config = json.load(file)
            cls._current_config = _merge_defaults(original_config)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            logger(
                "ConfigManager",
                "ERROR",
                f"Configuration at {config_file} is invalid; applying template: "
                f"{error}",
            )
            cls._backup_invalid_config(config_file)
            cls._current_config = deepcopy(cls.DEFAULT_CONFIG)
            cls.save()
            return

        cls._initialized = True
        if cls._current_config != original_config:
            cls.save()

    @classmethod
    def save(cls, settings_config: dict[str, Any] | None = None) -> None:
        config_file = cls.get_config_path()
        current_config = (
            settings_config if settings_config is not None else cls._current_config
        )
        validated_config = _merge_defaults(current_config)
        temporary_file = config_file.with_suffix(".json.tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(validated_config, file, ensure_ascii=False, indent=4)
        temporary_file.replace(config_file)
        cls._current_config = validated_config
        cls._initialized = True

    @classmethod
    def get(cls, key: str):
        if not cls._initialized:
            cls.init_config()
        if key not in cls._current_config:
            if key not in cls.DEFAULT_CONFIG:
                raise KeyError(key)
            logger(
                "ConfigManager",
                "DEBUG",
                f"Missing config key {key!r}; using its template value.",
            )
            return deepcopy(cls.DEFAULT_CONFIG[key])
        return cls._current_config[key]

    @classmethod
    def get_all(cls) -> dict[str, Any]:
        if not cls._initialized:
            cls.init_config()
        return deepcopy(cls._current_config)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        if not cls._initialized:
            cls.init_config()
        updated_config = deepcopy(cls._current_config)
        updated_config[key] = value
        cls.save(updated_config)


def get_config_path() -> Path:
    return ConfigManager.get_config_path()


def save_settings_config(settings_config: dict) -> None:
    ConfigManager.save(settings_config)


def load_settings_config() -> dict[str, Any]:
    if not ConfigManager._initialized:
        ConfigManager.init_config()
    return ConfigManager.get_all()


def get_settings_config_value(key: str):
    try:
        return ConfigManager.get(key)
    except KeyError:
        return None


def set_settings_config_value(key: str, value: Any) -> None:
    ConfigManager.set(key, value)


def get_env_variable(name: str) -> str:
    """Get an environment variable or an empty string."""
    load_dotenv()
    return os.getenv(name, "")
