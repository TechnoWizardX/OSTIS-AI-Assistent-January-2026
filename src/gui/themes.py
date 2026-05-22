"""
Темы интерфейса — цвета отделены от шаблонов.
Новая тема = только словарь из ~40 цветов.

Соглашение об именах цветов:
  bg_1 … bg_4       — фоны от самого тёмного/светлого к более светлому/тёмному
  text_1 … text_3   — основной, вторичный, подсказка
  border_1 … border_3 — обычная, hover, pressed
  accent_1 … accent_3 — акцентный цвет (нормальный, hover, pressed)
  danger_1 … danger_3 — красный (нормальный, hover, pressed)

Соглашение об именах QSS-шаблонов кнопок:
  btn_1            — основная кнопка (фон bg_3, рамка прозрачная)
  btn_2            — навигационная кнопка боковой панели (с :checked)
  btn_3            — акцентная кнопка «старт» (зелёная/акцентная)
  btn_4            — кнопка «стоп/удалить» (красная/danger)
  btn_transparent  — прозрачная кнопка без фона и рамки (для иконок)
  btn_checkable    — переключаемая кнопка (голосовой/динамик) с :checked
  btn_theme        — кнопка выбора темы (фон bg_2)

Мини-инструкция по добавлению новый элементов:
1. Проверить, подходит ли существующий шаблон
2. Если шаблон подходит, использовать его и при необходимости добавить новый цвет в палитру
3. Если шаблон не подходит, создать новый шаблон с универсальным именем (btn_5, btn_6 и т.д.) и использовать его в коде.
4. Если нужен просто цвет - добавить в подблок и назвать по смыслу (accent_4, danger_4, bg_5 и т.д.) и использовать напрямую в коде.
"""


# ============================================================
# ЦВЕТОВЫЕ ПАЛИТРЫ
# ============================================================
LIGHT_COLORS = {
    # Фоны
    "bg_1": "#D9D9D9",   # главный фон окна
    "bg_2": "#FFFFFF",   # панели, диалоги, чаты
    "bg_3": "#D9D9D9",   # кнопки, фреймы
    "bg_4": "#D3D3D3",   # вторичные фреймы (settings_frame)
    "bg_hover": "#C8C8C8",
    "bg_pressed": "#B8B8B8",
    "bg_checked": "#AAFF00",
    "bg_checked_border": "#666666",
    "bg_combo": "#FFFFFF",
    "bg_combo_hover": "#F9F9F9",
    "bg_scrollbar": "#E0E0E0",
    "bg_scrollbar_handle": "#B0B0B0",
    "bg_camera": "#A8A8A8",
    # Переключатель
    "toggle_off": "#B0B0B0",
    "toggle_on": "#4CAF50",
    "toggle_circle": "#FFFFFF",
    # Индикатор печати (точки)
    "typing_dots": "#4CAF50",
    # Текст
    "text_1": "#000000",
    "text_2": "#666666",
    "text_3": "#999999",
    "text_on_accent": "#FFFFFF",
    # Рамки
    "border_1": "#CCCCCC",
    "border_2": "#888888",
    "border_3": "#666666",
    # Навигация (боковая панель)
    "nav_border": "#666666",
    "nav_checked_text": "#000000",
    # Прочее
    "selection_bg": "#D9D9D9",
    "selection_text": "#000000",
    "divider": "#5A5A5A",
    "glow" : "#00FF00",
    "glow_blur" : 30,
    # Акцент (зелёный)
    "accent_1": "#4CAF50",
    "accent_2": "#45a049",
    "accent_3": "#388E3C",
    # Опасность (красный)
    "danger_1": "#f44336",
    "danger_2": "#da190b",
    "danger_3": "#c62828",
}

DARK_COLORS = {
    "bg_1": "#1E1E1E",
    "bg_2": "#2D2D2D",
    "bg_3": "#404040",
    "bg_4": "#3A3A3A",
    "bg_hover": "#505050",
    "bg_pressed": "#606060",
    "bg_checked": "#AAFF00",
    "bg_checked_border": "#88CC00",
    "bg_combo": "#333333",
    "bg_combo_hover": "#404040",
    "bg_scrollbar": "#333333",
    "bg_scrollbar_handle": "#555555",
    "bg_camera": "#333333",
    "toggle_off": "#555555",
    "toggle_on": "#4CAF50",
    "toggle_circle": "#E0E0E0",
    "typing_dots": "#4CAF50",
    "text_1": "#E0E0E0",
    "text_2": "#999999",
    "text_3": "#777777",
    "text_on_accent": "#FFFFFF",
    "border_1": "#555555",
    "border_2": "#666666",
    "border_3": "#777777",
    "nav_border": "#666666",
    "nav_checked_text": "#1E1E1E",
    "selection_bg": "#505050",
    "selection_text": "#E0E0E0",
    "divider": "#777777",
    "glow" : "#00FF00",
    "glow_blur" : 30,
    "accent_1": "#4CAF50",
    "accent_2": "#45a049",
    "accent_3": "#388E3C",
    "danger_1": "#f44336",
    "danger_2": "#da190b",
    "danger_3": "#c62828",
}

# Twilight — мягкие фиолетовые/тёплые тона, золотой акцент
TWILIGHT = {
    "bg_1": "#1D1F21",
    "bg_2": "#2B2B37",
    "bg_3": "#3A3A4A",
    "bg_4": "#353545",
    "bg_hover": "#4A4A5A",
    "bg_pressed": "#55556A",
    "bg_checked": "#D4A843",
    "bg_checked_border": "#B8922E",
    "bg_combo": "#303040",
    "bg_combo_hover": "#3A3A4A",
    "bg_scrollbar": "#303040",
    "bg_scrollbar_handle": "#50506A",
    "bg_camera": "#353545",
    "toggle_off": "#505060",
    "toggle_on": "#D4A843",
    "toggle_circle": "#F0F0E0",
    "typing_dots": "#D4A843",
    "text_1": "#E8E6E3",
    "text_2": "#A09E98",
    "text_3": "#7A7870",
    "text_on_accent": "#FFFFFF",
    "border_1": "#4A4A5A",
    "border_2": "#60607A",
    "border_3": "#707090",
    "nav_border": "#6A6A80",
    "nav_checked_text": "#1D1F21",
    "selection_bg": "#4A4A60",
    "selection_text": "#E8E6E3",
    "divider": "#7A7870",
    "glow" : "#FFD700",
    "glow_blur" : 30,
    "accent_1": "#C17817",
    "accent_2": "#D4901A",
    "accent_3": "#A86A10",
    "danger_1": "#B84D3E",
    "danger_2": "#CC6655",
    "danger_3": "#A04433",
}

# VS Code Dark+ — синий/фиолетовый акцент
VS_CODE_DARK = {
    "bg_1": "#1E1E1E",
    "bg_2": "#252526",
    "bg_3": "#2D2D30",
    "bg_4": "#2D2D30",
    "bg_hover": "#3E3E42",
    "bg_pressed": "#505055",
    "bg_checked": "#007ACC",
    "bg_checked_border": "#005A9E",
    "bg_combo": "#3C3C3C",
    "bg_combo_hover": "#444444",
    "bg_scrollbar": "#333333",
    "bg_scrollbar_handle": "#555555",
    "bg_camera": "#2D2D30",
    "toggle_off": "#555555",
    "toggle_on": "#007ACC",
    "toggle_circle": "#D4D4D4",
    "typing_dots": "#007ACC",
    "text_1": "#D4D4D4",
    "text_2": "#9CDCFE",
    "text_3": "#808080",
    "text_on_accent": "#FFFFFF",
    "border_1": "#404040",
    "border_2": "#505050",
    "border_3": "#606060",
    "nav_border": "#606060",
    "nav_checked_text": "#1E1E1E",
    "selection_bg": "#264F78",
    "selection_text": "#FFFFFF",
    "divider": "#808080",
    "glow" : "#4EC9B0",
    "glow_blur" : 30,
    "accent_1": "#4EC9B0",
    "accent_2": "#5DD4BB",
    "accent_3": "#3BA89A",
    "danger_1": "#F44747",
    "danger_2": "#FF6060",
    "danger_3": "#D03030",
}

# Nord — холодная арктическая палитра
NORD = {
    "bg_1": "#2E3440",
    "bg_2": "#3B4252",
    "bg_3": "#434C5E",
    "bg_4": "#434C5E",
    "bg_hover": "#4C566A",
    "bg_pressed": "#5A6580",
    "bg_checked": "#88C0D0",
    "bg_checked_border": "#5E81AC",
    "bg_combo": "#3B4252",
    "bg_combo_hover": "#434C5E",
    "bg_scrollbar": "#3B4252",
    "bg_scrollbar_handle": "#4C566A",
    "bg_camera": "#434C5E",
    "toggle_off": "#4C566A",
    "toggle_on": "#88C0D0",
    "toggle_circle": "#ECEFF4",
    "typing_dots": "#88C0D0",
    "text_1": "#ECEFF4",
    "text_2": "#D8DEE9",
    "text_3": "#9BA3B0",
    "text_on_accent": "#FFFFFF",
    "border_1": "#4C566A",
    "border_2": "#5E6E80",
    "border_3": "#6B7E96",
    "nav_border": "#5E81AC",
    "nav_checked_text": "#2E3440",
    "selection_bg": "#4C566A",
    "selection_text": "#ECEFF4",
    "divider": "#6B7E96",
    "glow" : "#88C0D0",
    "glow_blur" : 30,
    "accent_1": "#A3BE8C",
    "accent_2": "#B5C99E",
    "accent_3": "#8DA878",
    "danger_1": "#BF616A",
    "danger_2": "#CC7079",
    "danger_3": "#A85059",
    
}

# Gruvbox Dark — тёплая ретро-палитра
GRUVBOX_DARK = {
    "bg_1": "#282828",
    "bg_2": "#3C3836",
    "bg_3": "#504945",
    "bg_4": "#504945",
    "bg_hover": "#665C54",
    "bg_pressed": "#7C6F64",
    "bg_checked": "#B8BB26",
    "bg_checked_border": "#98971A",
    "bg_combo": "#3C3836",
    "bg_combo_hover": "#504945",
    "bg_scrollbar": "#3C3836",
    "bg_scrollbar_handle": "#665C54",
    "bg_camera": "#504945",
    "toggle_off": "#665C54",
    "toggle_on": "#B8BB26",
    "toggle_circle": "#EBDBB2",
    "typing_dots": "#B8BB26",
    "text_1": "#EBDBB2",
    "text_2": "#D5C4A1",
    "text_3": "#928374",
    "text_on_accent": "#FFFFFF",
    "border_1": "#665C54",
    "border_2": "#7C6F64",
    "border_3": "#928374",
    "nav_border": "#928374",
    "nav_checked_text": "#282828",
    "selection_bg": "#665C54",
    "selection_text": "#EBDBB2",
    "divider": "#928374",
    "glow" : "#B8BB26",
    "glow_blur" : 30,
    "accent_1": "#B8BB26",
    "accent_2": "#C6C838",
    "accent_3": "#A0A21E",
    "danger_1": "#FB4934",
    "danger_2": "#FC6550",
    "danger_3": "#E03320",
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

    # ── Окно / фоны ──────────────────────────────────────────
    "main_window": "background-color: {bg_1};",

    "side_panel": "background-color: {bg_2}; border-radius: 16px;",

    "settings_frame": "background-color: {bg_4}; border-radius: 12px;",

    "dialog_frame": "background-color: {bg_2}; border-radius: 16px;",

    "profile_option_frame": "background-color: {bg_4}; border-radius: 12px;",

    "profile_photo_frame": "background-color: {bg_4}; border-radius: 12px;",

    # ── Простые цвета ───────────────────────────────────────────────
    "accent" : "background-color: {accent_1}; border-radius: 12px;",
    "border": "background-color: {border_1};",
    "glow": "background-color: {glow}; border-radius: 12px;",
    "glow_blur" : "{glow_blur}",

    "input_page": """
        QWidget {{
            background-color: transparent;
            border-radius: 16px;
        }}
    """,

    "gestures_camera_frame": """
        QFrame {{
            background-color: {bg_4};
            border-radius: 12px;
        }}
    """,

    "message_frame": "background-color: {bg_4}; border-radius: 12px;",

    "chat_send_box_frame": "background-color: {bg_2}; border-radius: 16px;",

    "toggle_switch_row": """
        QFrame {{
            background-color: {bg_4};
            border-radius: 12px;
        }}
    """,

    # ── Текст / метки ─────────────────────────────────────────
    "settings_text": 'color: {text_1}; font-size: 14px; font-family: "Roboto";',

    "profile_text": "color: {text_1}; font-size: 16px;",

    "profile_line": "color: {divider}; background-color: {divider};",

    "message_author": """
        color: {text_2};
        font-size: 12px;
        font-family: "Roboto";
        background-color: transparent;
        font-weight: bold;
    """,

    "message_text": """
        color: {text_1};
        font-size: 14px;
        font-family: "Roboto";
        background-color: transparent;
    """,

    "message_time": """
        color: {text_3};
        background-color: transparent;
        font-size: 10px;
        font-family: "Roboto";
    """,

    "toggle_switch_row_label": """
        color: {text_1};
        font-size: 14px;
        font-family: "Roboto";
    """,

    # ── Поля ввода ────────────────────────────────────────────
    "settings_combobox": """
        QComboBox {{
            background-color: {bg_combo};
            border: 1px solid {border_1};
            border-radius: 4px;
            font-size: 14px;
            color: {text_1};
        }}
        QComboBox:hover {{
            border: 1px solid {border_2};
            background-color: {bg_combo_hover};
        }}
        QComboBox:on {{
            border: 1px solid {border_2};
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

    "settings_input": """
        QLineEdit {{
            background-color: {bg_combo};
            border: 1px solid {border_1};
            border-radius: 4px;
            font-size: 14px;
            color: {text_1};
            padding: 4px 8px;
        }}
        QLineEdit:hover {{
            border: 1px solid {border_2};
            background-color: {bg_combo_hover};
        }}
        QLineEdit:focus {{
            border: 1px solid {border_3};
        }}
    """,

    "chat_send_input": """
        QTextEdit {{
            background-color: transparent;
            border: none;
            font-size: 14px;
            font-family: "Roboto";
            color: {text_1};
        }}
    """,

    # ── Прокрутка ─────────────────────────────────────────────
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

    "chat_scroll_area": """
        QScrollArea {{
            border: none;
            background: transparent;
        }}
    """,

    # ── Камера ────────────────────────────────────────────────
    "camera_preview_label": """
        QLabel {{
            background-color: {bg_camera};
            border-radius: 8px;
        }}
    """,

    # ══════════════════════════════════════════════════════════
    # КНОПКИ — универсальные имена
    # ══════════════════════════════════════════════════════════

    # btn_1 — обычная кнопка (отправить, иконка с рамкой)
    "btn_1": """
        QPushButton {{
            background-color: {bg_3};
            border-radius: 12px;
            color: {text_1};
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 10px 10px 10px 20px;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            border: 3px solid {border_2};
        }}
        QPushButton:pressed {{
            background-color: {bg_pressed};
            border: 3px solid {border_3};
        }}
    """,

    # btn_2 — навигационная кнопка боковой панели (с :checked)
    "btn_2": """
        QPushButton {{
            background-color: {bg_3};
            border-radius: 12px;
            color: {text_1};
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 5px 5px 5px 16px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            border: 3px solid {border_2};
        }}
        QPushButton:pressed {{
            background-color: {bg_pressed};
            border: 3px solid {border_3};
        }}
        QPushButton:checked {{
            background-color: {bg_checked};
            border: 3px solid {nav_border};
            color: {nav_checked_text};
        }}
    """,

    # btn_3 — акцентная кнопка «старт»
    "btn_3": """
        QPushButton {{
            background-color: {accent_1};
            border-radius: 8px;
            color: {text_on_accent};
            font-size: 14px;
            font-family: "Roboto";
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {accent_2};
        }}
        QPushButton:pressed {{
            background-color: {accent_3};
        }}
    """,

    # btn_4 — кнопка «стоп / удалить / опасность»
    "btn_4": """
        QPushButton {{
            background-color: {danger_1};
            border-radius: 8px;
            color: {text_on_accent};
            font-size: 14px;
            font-family: "Roboto";
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {danger_2};
        }}
        QPushButton:pressed {{
            background-color: {danger_3};
        }}
    """,

    # btn_transparent — прозрачная кнопка-иконка (карандаш, галочка и т.д.)
    "btn_transparent": """
        QPushButton {{
            background-color: transparent;
            border: none;
            border-radius: 8px;
            color: {text_1};
        }}
        QPushButton:hover {{
            background-color: transparent;
            border: none;
        }}
        QPushButton:pressed {{
            background-color: transparent;
            border: none;
        }}
    """,

    # btn_checkable — переключаемая кнопка (голос, динамик) с состоянием :checked
    "btn_checkable": """
        QPushButton {{
            background-color: {bg_3};
            border-radius: 12px;
            border: 3px solid transparent;
            padding: 8px;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            border: 3px solid {border_2};
        }}
        QPushButton:pressed {{
            background-color: {bg_pressed};
            border: 3px solid {border_3};
        }}
        QPushButton:checked {{
            background-color: {accent_1};
            border: 3px solid {accent_3};
        }}
    """,

    # btn_theme — кнопка выбора темы (фон от панели, без :checked)
    "btn_theme": """
        QPushButton {{
            background-color: {bg_2};
            border-radius: 12px;
            color: {text_1};
            font-size: 14px;
            font-family: "Roboto";
            border: 3px solid transparent;
            padding: 5px 5px 5px 16px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            border: 3px solid {border_2};
        }}
        QPushButton:pressed {{
            background-color: {bg_pressed};
            border: 3px solid {border_3};
        }}
    """,

    "settings_section_label": """
        QLabel {{
            color: {text_2};
            background: transparent;
            border: none;
            font-size: 9px;
            font-weight: normal;
            letter-spacing: 0.5px;
        }}
    """,

    # ── Обратная совместимость (алиасы → новые имена) ─────────
    # Используйте новые имена btn_1…btn_transparent в новом коде.
    # Старые ключи оставлены, чтобы существующий код не сломался.
}

# Алиасы для обратной совместимости (маппинг старых ключей на новые)
_QSS_ALIASES = {
    "side_panel_button":    "btn_2",
    "send_button":          "btn_1",
    "icon_button":          "btn_1",
    "voice_button":         "btn_checkable",
    "speaker_button":       "btn_checkable",
    "camera_start_button":  "btn_3",
    "camera_stop_button":   "btn_4",
    "theme_button":         "btn_theme",
}


# ============================================================
# СБОРКА ГОТОВОЙ ТЕМЫ
# ============================================================
def get_theme(name: str) -> dict:
    """Возвращает готовый словарь QSS-стилей для темы.

    >>> theme = get_theme("dark")
    >>> widget.setStyleSheet(theme["btn_1"])
    >>> widget.setStyleSheet(theme["send_button"])  # обратная совместимость
    """
    colors = _COLOR_MAP.get(name, LIGHT_COLORS)
    theme = {}

    # Основные шаблоны
    for key, template in _QSS.items():
        theme[key] = template.format(**colors)

    # Алиасы (старые имена → значения новых)
    for old_key, new_key in _QSS_ALIASES.items():
        theme[old_key] = theme[new_key]

    # Данные для ToggleSwitch (отдельный словарь, не QSS)
    theme["toggle_switch"] = {
        "bg_off":  colors["toggle_off"],
        "bg_on":   colors["toggle_on"],
        "circle":  colors["toggle_circle"],
    }

    # Данные для TypingDotsWidget (отдельный словарь, не QSS)
    theme["typing_dots"] = {
        "color": colors["typing_dots"],
    }

    # Прямой доступ к цветам (для inline-стилей, напр. api_key_input)
    theme["colors"] = colors

    return theme


# Готовые темы — один вызов при импорте
THEMES = {
    "light":    get_theme("light"),
    "dark":     get_theme("dark"),
    "twilight": get_theme("twilight"),
    "vs_code":  get_theme("vs_code"),
    "nord":     get_theme("nord"),
    "gruvbox":  get_theme("gruvbox"),
}
from src.utils.BasicUtils import BasicUtils
SELECTED_THEME = BasicUtils.get_settings_config_value("theme")