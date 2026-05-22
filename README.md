# AI-Assistant

At the moment the Windows version has limited functionality due to the small number of libraries.
```
project-root/
│
├── main.py                         # точка входа
├── .env                            # переменные окружения
├── requirements.txt
├── README.md
│
├── src/                            # весь исходный код
│   ├── __init__.py
│   │
│   ├── core/                       # ядро приложения
│   │   ├── __init__.py
│   │   ├── assistant.py            # главный оркестратор (бывший AssistentCore)
│   │   ├── intent_handler.py       # обработка интентов (IntentHandler)
│   │   ├── recommendation.py       # рекомендации доступности
│   │   └── network_monitor.py      # проверка интернета
│   │
│   ├── gui/                        # графический интерфейс (PyQt6)
│   │   ├── __init__.py
│   │   ├── main_window.py          # главное окно (UserInterface)
│   │   ├── themes.py               # темы оформления
│   │   │
│   │   ├── widgets/                # независимые виджеты, не привязанные к конкретной странице
│   │   ├── __init__.py
│   │   ├── chat_dialog.py      # DialogBox (список сообщений с прокруткой)
│   │   ├── chat_send_box.py    # ChatSendBox (поле ввода + кнопки)
│   │   ├── message_item.py     # Message (один пузырёк сообщения)
│   │   ├── typing_indicator.py # TypingDotsWidget, TypingIndicator
│   │   ├── toggle_switch.py    # ToggleSwitch, ToggleSwitchRow
│   │   ├── recommendation_glow.py # RunningLineOverlay, RecommendationGlowEffect
│   │   └── settings_section.py # SettingsSectionLabel
│   │   │
│   │   ├── pages/                  # страницы, переключаемые в боковой панели
│   │   │   ├── __init__.py
│   │   │   ├── base_page.py        # ContentPageWidget (общий предок)
│   │   │   ├── settings_page.py    # настройки
│   │   │   ├── profile_page.py     # профиль пользователя
│   │   │   ├── voice_page.py       # голосовой ввод
│   │   │   ├── text_page.py        # текстовый ввод
│   │   │   └── gestures_page.py    # жестовый ввод
│   │   │
│   │   └── resources/              # иконки, стили (только данные)
│   │       ├── icons/              # все .png
│   │       └── qss/                # (опционально) вынос стилей
│   │
│   ├── audio/                      # работа со звуком и речью
│   │   ├── __init__.py
│   │   ├── tts_engine.py           # Silero TTS (бывший TTSSilero)
│   │   ├── stt_engine.py           # Whisper + VAD (WhisperRecognition)
│   │   └── voice_utils.py          # вспомогательные функции (wav→numpy, постпроцессинг)
│   │
│   ├── system/                     # системные вызовы (Windows API и др.)
│   │   ├── __init__.py
│   │   ├── control.py              # ControlSystem
│   │   ├── apps.py                 # работа с приложениями (AppOpener)
│   │   ├── hardware.py             # яркость, громкость, питание
│   │   └── window_management.py    # управление окнами, привязка, прозрачность
│   │
│   ├── utils/                      # служебные модули без состояния
│   │   ├── __init__.py
│   │   ├── logger.py               # логирование (бывший BasicUtils.logger)
│   │   ├── config.py               # работа с JSON-конфигами (settings_config.json)
│   │   ├── database.py             # DataBaseEditor (SQLite)
│   │   ├── network.py              # проверка интернета
│   │   ├── chat_history.py         # загрузка/сохранение/очистка истории чата
│   │   └── devices.py              # получение списка камер, микрофонов
│   │
│   └── data/                       # пользовательские данные 
│       ├── chat_history.json
│       ├── settings_config.json
│       ├── database.db
│       ├── basic_prompt.md
│       ├── recommendation_prompt.md
│       └── accessibility_cache.json
│
├── models/                         # скачанные модели (Whisper, Silero)
│   └── silero/ ...
│
└── tests/                          
    ├── test_intent_handler.py
    ├── test_system_control.py
    └── ...
```