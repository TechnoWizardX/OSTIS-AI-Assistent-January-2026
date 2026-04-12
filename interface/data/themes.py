"""
Темы интерфейса — сгруппированы по компонентам.
Каждая тема — словарь со стилями QSS для каждого виджета.
"""

# ============================================================
# LIGHT THEME (текущие цвета)
# ============================================================
LIGHT = {
    # --- ГЛАВНОЕ ОКНО ---
    "main_window": """
        background-color: #D9D9D9;
    """,

    # --- БОКОВАЯ ПАНЕЛЬ ---
    "side_panel": """
        background-color: #FFFFFF;
        border-radius: 16px;
    """,

    # --- КНОПКА БОКОВОЙ ПАНЕЛИ ---
    "side_panel_button": """
        QPushButton {
            background-color: #D9D9D9;
            border-radius: 12px;
            color: #000000;
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 5px 5px 5px 16px;
            text-align: left;
        }
        QPushButton:hover {
            background-color: #C8C8C8;
            border: 3px solid #888888;
        }
        QPushButton:pressed {
            background-color: #B8B8B8;
            border: 3px solid #666666;
        }
        QPushButton:checked {
            background-color: #AAFF00;
            border: 3px solid #666666;
        }
    """,

    # --- ФРЕЙМ КАМЕРЫ / МИКРОФОНА / ДИКТОРА / ПЕРЕКЛЮЧАТЕЛЯ (настройки) ---
    "settings_frame": """
        background-color: #D3D3D3;
        border-radius: 12px;
    """,

    # --- ТЕКСТ НАСТРОЕК ---
    "settings_text": """
        color: #000000;
        font-size: 14px;
        font-family: "Roboto";
    """,

    # --- ВЫПАДАЮЩИЙ СПИСОК (QComboBox в настройках) ---
    "settings_combobox": """
        QComboBox {
            background-color: #FFFFFF;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            font-size: 14px;
            color: #000000;
        }
        QComboBox:hover {
            border: 1px solid #888888;
            background-color: #F9F9F9;
        }
        QComboBox:on {
            border: 1px solid #888888;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox QAbstractItemView {
            background-color: transparent;
            border-radius: 8px;
            selection-background-color: #D9D9D9;
            selection-color: #000000;
            outline: none;
        }
    """,

    # --- ПЕРЕКЛЮЧАТЕЛЬ (ToggleSwitch) ---
    "toggle_switch": {
        "bg_off": "#B0B0B0",
        "bg_on": "#4CAF50",
        "circle": "#FFFFFF",
    },

    # --- ФРЕЙМ ПОЛЯ ОТПРАВКИ СООБЩЕНИЙ ---
    "chat_send_box_frame": """
        background-color: #FFFFFF;
        border-radius: 16px;
    """,

    # --- ПОЛЕ ВВОДА СООБЩЕНИЙ (QTextEdit) ---
    "chat_send_input": """
        QTextEdit {
            background-color: transparent;
            border: none;
            font-size: 14px;
            font-family: "Roboto";
            color: #000000;
        }
    """,

    # --- КНОПКА ГОЛОСА (microphone) ---
    "voice_button": """
        QPushButton {
            background-color: #D9D9D9;
            border-radius: 12px;
            border: 3px solid transparent;
            padding: 8px;
        }
        QPushButton:hover {
            background-color: #C8C8C8;
            border: 3px solid #888888;
        }
        QPushButton:pressed {
            background-color: #B8B8B8;
            border: 3px solid #666666;
        }
        QPushButton:checked {
            background-color: #4CAF50;
            border: 3px solid #388E3C;
        }
    """,

    # --- КНОПКА ОТПРАВКИ ---
    "send_button": """
        QPushButton {
            background-color: #D9D9D9;
            border-radius: 12px;
            color: #000000;
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 10px 10px 10px 20px;
        }
        QPushButton:hover {
            background-color: #C8C8C8;
            border: 3px solid #888888;
        }
        QPushButton:pressed {
            background-color: #B8B8B8;
            border: 3px solid #666666;
        }
    """,

    # --- ФРЕЙМ СООБЩЕНИЯ ---
    "message_frame": """
        background-color: #D9D9D9;
        border-radius: 12px;
    """,

    # --- АВТОР СООБЩЕНИЯ ---
    "message_author": """
        color: #666666;
        font-size: 12px;
        font-family: "Roboto";
        background-color: transparent;
        font-weight: bold;
    """,

    # --- ТЕКСТ СООБЩЕНИЯ ---
    "message_text": """
        color: #000000;
        font-size: 14px;
        font-family: "Roboto";
        background-color: transparent;
    """,

    # --- ВРЕМЯ СООБЩЕНИЯ ---
    "message_time": """
        color: #999999;
        background-color: transparent;
        font-size: 10px;
        font-family: "Roboto";
    """,

    # --- ОБЛАСТЬ ЧАТА (QScrollArea) ---
    "chat_scroll_area": """
        QScrollArea {
            border: none;
            background: transparent;
        }
    """,

    # --- СКРОЛЛБАР ---
    "scrollbar": """
        QScrollBar:vertical {
            border: none;
            background-color: #E0E0E0;
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background-color: #B0B0B0;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """,

    # --- ФРЕЙМ ДИАЛОГА ---
    "dialog_frame": """
        background-color: #FFFFFF;
        border-radius: 16px;
    """,

    # --- СТРОКА ПРОФИЛЯ (ProfileOption) ---
    "profile_option_frame": """
        background-color: #D3D3D3;
        border-radius: 12px;
    """,

    # --- ТЕКСТ ПРОФИЛЯ ---
    "profile_text": """
        color: #000000;
        font-size: 16px;
    """,

    # --- ЛИНИЯ-РАЗДЕЛИТЕЛЬ ---
    "profile_line": """
        color: #000000;
        background-color: #000000;
    """,

    # --- ФОТО ПРОФИЛЯ ---
    "profile_photo_frame": """
        background-color: #D3D3D3;
        border-radius: 12px;
    """,

    # --- СТРАНИЦА ГОЛОСОВОГО / ТЕКСТОВОГО ВВОДА ---
    "input_page": """
        QWidget {
            background-color: transparent;
            border-radius: 16px;
        }
    """,

    # --- ФРЕЙМ КАМЕРЫ (жесты) ---
    "gestures_camera_frame": """
        QFrame {
            background-color: #D3D3D3;
            border-radius: 12px;
        }
    """,

    # --- ПРЕВЬЮ КАМЕРЫ ---
    "camera_preview_label": """
        QLabel {
            background-color: #A8A8A8;
            border-radius: 8px;
        }
    """,

    # --- КНОПКА СТАРТ (жесты) ---
    "camera_start_button": """
        QPushButton {
            background-color: #4CAF50;
            border-radius: 8px;
            color: #FFFFFF;
            font-size: 14px;
            font-family: "Roboto";
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #388E3C;
        }
    """,

    # --- КНОПКА СТОП (жесты) ---
    "camera_stop_button": """
        QPushButton {
            background-color: #f44336;
            border-radius: 8px;
            color: #FFFFFF;
            font-size: 14px;
            font-family: "Roboto";
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #da190b;
        }
        QPushButton:pressed {
            background-color: #c62828;
        }
    """,
}


# ============================================================
# DARK THEME (заготовка — цвета те же, просто переименован)
# ============================================================
# Пока пустая заготовка, чтобы структура была готова.
# Заполнишь цветами когда будет нужно.
DARK = {
    key: value for key, value in LIGHT.items()
}

# ============================================================
# СЛОВАРЬ ВСЕХ ТЕМ
# ============================================================
THEMES = {
    "light": LIGHT,
    "dark": DARK,
}
