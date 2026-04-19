"""
Темы интерфейса — цвета отделены от шаблонов.
Новая тема = только словарь из ~40 цветов.
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

# Twilight — мягкие фиолетовые/тёплые тона, золотой акцент
TWILIGHT = {
    "bg_main": "#1D1F21",
    "bg_panel": "#2B2B37",
    "bg_frame": "#353545",
    "bg_button": "#3A3A4A",
    "bg_button_hover": "#4A4A5A",
    "bg_button_pressed": "#55556A",
    "bg_button_checked": "#D4A843",
    "bg_button_checked_border": "#B8922E",
    "bg_chat_box": "#2B2B37",
    "bg_message": "#353545",
    "bg_dialog": "#2B2B37",
    "bg_combo": "#303040",
    "bg_combo_hover": "#3A3A4A",
    "bg_scrollbar": "#303040",
    "bg_scrollbar_handle": "#50506A",
    "bg_camera_preview": "#353545",
    "bg_toggle_off": "#505060",
    "bg_toggle_on": "#D4A843",
    "circle_toggle": "#F0F0E0",
    "text_primary": "#E8E6E3",
    "text_secondary": "#A09E98",
    "text_hint": "#7A7870",
    "text_white": "#FFFFFF",
    "border": "#4A4A5A",
    "border_hover": "#60607A",
    "border_pressed": "#707090",
    "side_border": "#6A6A80",
    "side_checked_text": "#1D1F21",
    "selection_bg": "#4A4A60",
    "selection_text": "#E8E6E3",
    "profile_line": "#7A7870",
    "btn_start": "#C17817",
    "btn_start_hover": "#D4901A",
    "btn_start_pressed": "#A86A10",
    "btn_stop": "#B84D3E",
    "btn_stop_hover": "#CC6655",
    "btn_stop_pressed": "#A04433",
    "voice_checked_bg": "#D4A843",
    "voice_checked_border": "#B8922E",
}

# VS Code Dark+ — синий/фиолетовый акцент, бирюзовая кнопка старт
VS_CODE_DARK = {
    "bg_main": "#1E1E1E",
    "bg_panel": "#252526",
    "bg_frame": "#2D2D30",
    "bg_button": "#2D2D30",
    "bg_button_hover": "#3E3E42",
    "bg_button_pressed": "#505055",
    "bg_button_checked": "#007ACC",
    "bg_button_checked_border": "#005A9E",
    "bg_chat_box": "#252526",
    "bg_message": "#2D2D30",
    "bg_dialog": "#252526",
    "bg_combo": "#3C3C3C",
    "bg_combo_hover": "#444444",
    "bg_scrollbar": "#333333",
    "bg_scrollbar_handle": "#555555",
    "bg_camera_preview": "#2D2D30",
    "bg_toggle_off": "#555555",
    "bg_toggle_on": "#007ACC",
    "circle_toggle": "#D4D4D4",
    "text_primary": "#D4D4D4",
    "text_secondary": "#9CDCFE",
    "text_hint": "#808080",
    "text_white": "#FFFFFF",
    "border": "#404040",
    "border_hover": "#505050",
    "border_pressed": "#606060",
    "side_border": "#606060",
    "side_checked_text": "#1E1E1E",
    "selection_bg": "#264F78",
    "selection_text": "#FFFFFF",
    "profile_line": "#808080",
    "btn_start": "#4EC9B0",
    "btn_start_hover": "#5DD4BB",
    "btn_start_pressed": "#3BA89A",
    "btn_stop": "#F44747",
    "btn_stop_hover": "#FF6060",
    "btn_stop_pressed": "#D03030",
    "voice_checked_bg": "#007ACC",
    "voice_checked_border": "#005A9E",
}

# Nord — холодная арктическая палитра
NORD = {
    "bg_main": "#2E3440",
    "bg_panel": "#3B4252",
    "bg_frame": "#434C5E",
    "bg_button": "#434C5E",
    "bg_button_hover": "#4C566A",
    "bg_button_pressed": "#5A6580",
    "bg_button_checked": "#88C0D0",
    "bg_button_checked_border": "#5E81AC",
    "bg_chat_box": "#3B4252",
    "bg_message": "#434C5E",
    "bg_dialog": "#3B4252",
    "bg_combo": "#3B4252",
    "bg_combo_hover": "#434C5E",
    "bg_scrollbar": "#3B4252",
    "bg_scrollbar_handle": "#4C566A",
    "bg_camera_preview": "#434C5E",
    "bg_toggle_off": "#4C566A",
    "bg_toggle_on": "#88C0D0",
    "circle_toggle": "#ECEFF4",
    "text_primary": "#ECEFF4",
    "text_secondary": "#D8DEE9",
    "text_hint": "#9BA3B0",
    "text_white": "#FFFFFF",
    "border": "#4C566A",
    "border_hover": "#5E6E80",
    "border_pressed": "#6B7E96",
    "side_border": "#5E81AC",
    "side_checked_text": "#2E3440",
    "selection_bg": "#4C566A",
    "selection_text": "#ECEFF4",
    "profile_line": "#6B7E96",
    "btn_start": "#A3BE8C",
    "btn_start_hover": "#B5C99E",
    "btn_start_pressed": "#8DA878",
    "btn_stop": "#BF616A",
    "btn_stop_hover": "#CC7079",
    "btn_stop_pressed": "#A85059",
    "voice_checked_bg": "#88C0D0",
    "voice_checked_border": "#5E81AC",
}

# Gruvbox Dark — тёплая ретро-палитра (зелёный/оранжевый/жёлтый)
GRUVBOX_DARK = {
    "bg_main": "#282828",
    "bg_panel": "#3C3836",
    "bg_frame": "#504945",
    "bg_button": "#504945",
    "bg_button_hover": "#665C54",
    "bg_button_pressed": "#7C6F64",
    "bg_button_checked": "#B8BB26",
    "bg_button_checked_border": "#98971A",
    "bg_chat_box": "#3C3836",
    "bg_message": "#504945",
    "bg_dialog": "#3C3836",
    "bg_combo": "#3C3836",
    "bg_combo_hover": "#504945",
    "bg_scrollbar": "#3C3836",
    "bg_scrollbar_handle": "#665C54",
    "bg_camera_preview": "#504945",
    "bg_toggle_off": "#665C54",
    "bg_toggle_on": "#B8BB26",
    "circle_toggle": "#EBDBB2",
    "text_primary": "#EBDBB2",
    "text_secondary": "#D5C4A1",
    "text_hint": "#928374",
    "text_white": "#FFFFFF",
    "border": "#665C54",
    "border_hover": "#7C6F64",
    "border_pressed": "#928374",
    "side_border": "#928374",
    "side_checked_text": "#282828",
    "selection_bg": "#665C54",
    "selection_text": "#EBDBB2",
    "profile_line": "#928374",
    "btn_start": "#B8BB26",
    "btn_start_hover": "#C6C838",
    "btn_start_pressed": "#A0A21E",
    "btn_stop": "#FB4934",
    "btn_stop_hover": "#FC6550",
    "btn_stop_pressed": "#E03320",
    "voice_checked_bg": "#B8BB26",
    "voice_checked_border": "#98971A",
}

_COLOR_MAP = {
    "light": LIGHT_COLORS,
    "dark": DARK_COLORS,
    "twilight": TWILIGHT,
    "vs_code": VS_CODE_DARK,
    "nord": NORD,
    "gruvbox": GRUVBOX_DARK,
}


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
    "speaker_button": """
        QPushButton {{
            background-color: {bg_button};
            border-radius: 8px;
            border: 3px solid transparent;
            padding: 2px;
        }}
        QPushButton:hover {{
            background-color: {bg_button_hover};
            border: 2px solid {border_hover};
        }}
        QPushButton:pressed {{
            background-color: {bg_button_pressed};
            border: 2px solid {border_pressed};
        }}
        QPushButton:checked {{
            background-color: {voice_checked_bg};
            border: 2px solid {voice_checked_border};
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
    "twilight": get_theme("twilight"),
    "vs_code": get_theme("vs_code"),
    "nord": get_theme("nord"),
    "gruvbox": get_theme("gruvbox"),
}
