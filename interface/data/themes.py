"""
Темы интерфейса — цвета отделены от шаблонов QSS.
Добавление новой темы = только словарь цветов.
"""
"""
Главное окно	        |   main_window
Боковая панель	        |   side_panel
Кнопки боковой панели	|   side_panel_button
Фреймы настроек	        |   settings_frame
Текст настроек	        |   settings_text
ComboBox настроек	    |   settings_combobox
Переключатель (цвета)   |   toggle_switch
Фрейм отправки	        |   chat_send_box_frame
Поле ввода	            |   chat_send_input
Кнопка голоса	        |   voice_button
Кнопка отправки	        |   send_button
Фрейм сообщения	        |   message_frame
Автор/текст/время	    |   message_author, message_text, message_time
Скроллбар чата	        |   chat_scroll_area + scrollbar
Фрейм диалога	        |   dialog_frame
Строка профиля	        |   profile_option_frame, profile_text, profile_line
Фото профиля	        |   profile_photo_frame
Страницы ввода  	    |   input_page
Камера жестов	        |   gestures_camera_frame, camera_preview_label
Кнопки камеры   	    |   camera_start_button, camera_stop_button
Кнопки смены тем        |   theme_button
"""

# ============================================================
# ЦВЕТОВЫЕ ПАЛИТРЫ
# ============================================================
LIGHT_COLORS = {
    "bg_main": "#D9D9D9",
    "bg_panel": "#FFFFFF",
    "bg_frame": "#D3D3D3",
    "bg_button": "#D9D9D9",
    "bg_button_hover": "#C8C8C8",
    "bg_button_pressed": "#B8B8B8",
    "bg_button_checked": "#AAFF00",
    "bg_button_checked_border": "#666666",
    "bg_chat_box": "#FFFFFF",
    "bg_message": "#D9D9D9",
    "bg_dialog": "#FFFFFF",
    "bg_combo": "#FFFFFF",
    "bg_combo_hover": "#F9F9F9",
    "bg_scrollbar": "#E0E0E0",
    "bg_scrollbar_handle": "#B0B0B0",
    "bg_camera_preview": "#A8A8A8",
    "bg_toggle_off": "#B0B0B0",
    "bg_toggle_on": "#4CAF50",
    "circle_toggle": "#FFFFFF",
    "text_primary": "#000000",
    "text_secondary": "#666666",
    "text_hint": "#999999",
    "text_white": "#FFFFFF",
    "border": "#CCCCCC",
    "border_hover": "#888888",
    "border_pressed": "#666666",
    "side_border": "#666666",
    "side_checked_text": "#000000",
    "selection_bg": "#D9D9D9",
    "selection_text": "#000000",
    "profile_line": "#000000",
    "btn_start": "#4CAF50",
    "btn_start_hover": "#45a049",
    "btn_start_pressed": "#388E3C",
    "btn_stop": "#f44336",
    "btn_stop_hover": "#da190b",
    "btn_stop_pressed": "#c62828",
    "voice_checked_bg": "#4CAF50",
    "voice_checked_border": "#388E3C",
}

DARK_COLORS = {
    "bg_main": "#1E1E1E",
    "bg_panel": "#2D2D2D",
    "bg_frame": "#3A3A3A",
    "bg_button": "#404040",
    "bg_button_hover": "#505050",
    "bg_button_pressed": "#606060",
    "bg_button_checked": "#AAFF00",
    "bg_button_checked_border": "#88CC00",
    "bg_chat_box": "#2D2D2D",
    "bg_message": "#3A3A3A",
    "bg_dialog": "#2D2D2D",
    "bg_combo": "#333333",
    "bg_combo_hover": "#404040",
    "bg_scrollbar": "#333333",
    "bg_scrollbar_handle": "#555555",
    "bg_camera_preview": "#333333",
    "bg_toggle_off": "#555555",
    "bg_toggle_on": "#4CAF50",
    "circle_toggle": "#E0E0E0",
    "text_primary": "#E0E0E0",
    "text_secondary": "#999999",
    "text_hint": "#777777",
    "text_white": "#FFFFFF",
    "border": "#555555",
    "border_hover": "#666666",
    "border_pressed": "#777777",
    "side_border": "#666666",
    "side_checked_text": "#1E1E1E",
    "selection_bg": "#505050",
    "selection_text": "#E0E0E0",
    "profile_line": "#777777",
    "btn_start": "#4CAF50",
    "btn_start_hover": "#45a049",
    "btn_start_pressed": "#388E3C",
    "btn_stop": "#f44336",
    "btn_stop_hover": "#da190b",
    "btn_stop_pressed": "#c62828",
    "voice_checked_bg": "#4CAF50",
    "voice_checked_border": "#388E3C",
}

_COLOR_MAP = {"light": LIGHT_COLORS, "dark": DARK_COLORS}


# ============================================================
# ШАБЛОНЫ QSS (одни на все темы)
# ============================================================
_QSS = {

    "main_window": "background-color: {bg_main};",

    "side_panel": "background-color: {bg_panel}; border-radius: 16px;",

    "side_panel_button": """
        QPushButton {{
            background-color: {bg_button};
            border-radius: 12px;
            color: {text_primary};
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 5px 5px 5px 16px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {bg_button_hover};
            border: 3px solid {border_hover};
        }}
        QPushButton:pressed {{
            background-color: {bg_button_pressed};
            border: 3px solid {border_pressed};
        }}
        QPushButton:checked {{
            background-color: {bg_button_checked};
            border: 3px solid {side_border};
            color: {side_checked_text};
        }}
    """,

    "settings_frame": "background-color: {bg_frame}; border-radius: 12px;",

    "settings_text": "color: {text_primary}; font-size: 14px; font-family: \"Roboto\";",

    "settings_combobox": """
        QComboBox {{
            background-color: {bg_combo};
            border: 1px solid {border};
            border-radius: 4px;
            font-size: 14px;
            color: {text_primary};
        }}
        QComboBox:hover {{
            border: 1px solid {border_hover};
            background-color: {bg_combo_hover};
        }}
        QComboBox:on {{
            border: 1px solid {border_hover};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox QAbstractItemView {{
            background-color: transparent;
            border-radius: 8px;
            selection-background-color: {selection_bg};
            selection-color: {selection_text};
            outline: none;
        }}
    """,

    "chat_send_box_frame": "background-color: {bg_chat_box}; border-radius: 16px;",

    "chat_send_input": """
        QTextEdit {{
            background-color: transparent;
            border: none;
            font-size: 14px;
            font-family: "Roboto";
            color: {text_primary};
        }}
    """,

    "voice_button": """
        QPushButton {{
            background-color: {bg_button};
            border-radius: 12px;
            border: 3px solid transparent;
            padding: 8px;
        }}
        QPushButton:hover {{
            background-color: {bg_button_hover};
            border: 3px solid {border_hover};
        }}
        QPushButton:pressed {{
            background-color: {bg_button_pressed};
            border: 3px solid {border_pressed};
        }}
        QPushButton:checked {{
            background-color: {voice_checked_bg};
            border: 3px solid {voice_checked_border};
        }}
    """,

    "send_button": """
        QPushButton {{
            background-color: {bg_button};
            border-radius: 12px;
            color: {text_primary};
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 10px 10px 10px 20px;
        }}
        QPushButton:hover {{
            background-color: {bg_button_hover};
            border: 3px solid {border_hover};
        }}
        QPushButton:pressed {{
            background-color: {bg_button_pressed};
            border: 3px solid {border_pressed};
        }}
    """,

    "message_frame": "background-color: {bg_message}; border-radius: 12px;",

    "message_author": """
        color: {text_secondary};
        font-size: 12px;
        font-family: "Roboto";
        background-color: transparent;
        font-weight: bold;
    """,

    "message_text": """
        color: {text_primary};
        font-size: 14px;
        font-family: "Roboto";
        background-color: transparent;
    """,

    "message_time": """
        color: {text_hint};
        background-color: transparent;
        font-size: 10px;
        font-family: "Roboto";
    """,

    "chat_scroll_area": """
        QScrollArea {{
            border: none;
            background: transparent;
        }}
    """,

    "scrollbar": """
        QScrollBar:vertical {{
            border: none;
            background-color: {bg_scrollbar};
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {bg_scrollbar_handle};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """,

    "dialog_frame": "background-color: {bg_dialog}; border-radius: 16px;",

    "profile_option_frame": "background-color: {bg_frame}; border-radius: 12px;",

    "profile_text": "color: {text_primary}; font-size: 16px;",

    "profile_line": "color: {profile_line}; background-color: {profile_line};",

    "profile_photo_frame": "background-color: {bg_frame}; border-radius: 12px;",

    "input_page": """
        QWidget {{
            background-color: transparent;
            border-radius: 16px;
        }}
    """,

    "gestures_camera_frame": """
        QFrame {{
            background-color: {bg_frame};
            border-radius: 12px;
        }}
    """,

    "camera_preview_label": """
        QLabel {{
            background-color: {bg_camera_preview};
            border-radius: 8px;
        }}
    """,

    "camera_start_button": """
        QPushButton {{
            background-color: {btn_start};
            border-radius: 8px;
            color: {text_white};
            font-size: 14px;
            font-family: "Roboto";
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {btn_start_hover};
        }}
        QPushButton:pressed {{
            background-color: {btn_start_pressed};
        }}
    """,

    "camera_stop_button": """
        QPushButton {{
            background-color: {btn_stop};
            border-radius: 8px;
            color: {text_white};
            font-size: 14px;
            font-family: "Roboto";
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {btn_stop_hover};
        }}
        QPushButton:pressed {{
            background-color: {btn_stop_pressed};
        }}
    """,
    "theme_button": """
        QPushButton {{
            background-color: {bg_panel};
            border-radius: 12px;
            color: {text_primary};
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 5px 5px 5px 16px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {bg_button_hover};
            border: 3px solid {border_hover};
        }}
        QPushButton:pressed {{
            background-color: {bg_button_pressed};
            border: 3px solid {border_pressed};
        }}
        QPushButton:checked {{
            background-color: {bg_button_checked};
            border: 3px solid {side_border};
            color: {side_checked_text};
        }}
    """,

    "toggle_switch_row": """
        QFrame {{
            background-color: {bg_frame};
            border-radius: 12px;
        }}
    """,

    "toggle_switch_row_label": """
        color: {text_primary};
        font-size: 14px;
        font-family: "Roboto";
    """,
}


# ============================================================
# СБОРКА ГОТОВОЙ ТЕМЫ
# ============================================================
def get_theme(name: str) -> dict:
    """Возвращает готовый словарь QSS-стилей для темы.

    >>> theme = get_theme("dark")
    >>> widget.setStyleSheet(theme["side_panel"])
    """
    colors = _COLOR_MAP.get(name, LIGHT_COLORS)
    theme = {}
    for key, template in _QSS.items():
        theme[key] = template.format(**colors)
    theme["toggle_switch"] = {
        "bg_off": colors["bg_toggle_off"],
        "bg_on": colors["bg_toggle_on"],
        "circle": colors["circle_toggle"],
    }
    return theme


# Обратная совместимость
THEMES = {
    "light": get_theme("light"),
    "dark": get_theme("dark"),
}
