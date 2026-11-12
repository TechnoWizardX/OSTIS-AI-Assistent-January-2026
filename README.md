# AI-Assistant

At the moment the Windows version has limited functionality due to the small number of libraries.
```
project-root/
├── main.py
├── models/                         # скачанные модели
└── src/
    ├── core/
    │   ├── assistant_core.py       # оркестрация приложения
    │   ├── network_monitor.py
    │   └── __init__.py
    ├── gui/
    │   ├── main_window.py
    │   ├── theme_manager.py
    │   ├── signals.py
    │   ├── pages/
    │   └── widgets/
    ├── modules/
    │   ├── gesture/
    │   │   ├── gestures.py
    │   │   └── gestures_config.json
    │   └── voice/
    │       ├── stt_engine.py
    │       └── tts_engine.py
    ├── services/
    │   └── ai_service/
    │       ├── llm_client.py
    │       ├── intent_handler.py
    │       └── recommendation.py
    ├── utils/
    │   ├── config_manager.py
    │   ├── database.py
    │   ├── chat_history.py
    │   ├── user_data.py
    │   ├── BasicUtils.py
    │   ├── logger.py
    │   ├── network.py
    │   └── system_control.py
    ├── resources/
    │   ├── icons/
    │   ├── styles/
    │   │   └── base.qss
    │   └── themes/
    │       └── *.json
    └── data/
        ├── prompts/
        └── templates/
```

Пользовательские настройки, профильная база и история чата хранятся вне каталога
проекта в стандартной пользовательской папке Qt (`AppLocalDataLocation`) для
приложения `IAMOS`: `config.json`, `database.sqlite3` и `chat_history.sqlite3`.
При первом запуске старые настройки, база и JSON-история переносятся туда без
удаления исходных файлов. Повреждённая конфигурация сохраняется в резервной
копии, после чего применяется шаблон из `src/data/templates/data.py`.
Кэш рекомендаций также хранится в пользовательской папке; промпты остаются
внутренними ресурсами приложения.

Оформление отделено от цветов: общий шаблон QSS лежит в
`src/resources/styles/base.qss`, а в `src/resources/themes/*.json` остаются
только палитры. `ThemeManager` подставляет значения `{{ключ}}` из палитры,
поэтому новое правило стиля добавляется один раз для всех тем.
