# -*- coding: utf-8 -*-
"""
Жестовое управление — MediaPipe Tasks API.
Архитектура: единый GestureProcessor + GestureCameraThread для PyQt интерфейса.
"""

import cv2
import mediapipe as mp
import math
import numpy as np
import sys
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except ImportError:
    BRIGHTNESS_AVAILABLE = False

try:
    import pycaw.pycaw as pycaw
    from pycaw.pycaw import AudioUtilities
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# PyQt для сигналов и потоков
from PyQt6.QtCore import QThread, pyqtSignal, QSize
from PyQt6.QtGui import QImage

print(sys.executable)

# ============================================================
# ЗАГРУЗКА КОНФИГУРАЦИИ
# ============================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "gestures_config.json")

def load_config():
    """Загружает конфигурацию жестов из JSON файла."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: файл конфигурации не найден: {CONFIG_PATH}")
        return get_default_config()
    except json.JSONDecodeError as e:
        print(f"Ошибка JSON в конфигурации: {e}")
        return get_default_config()

def get_default_config():
    """Возвращает конфигурацию по умолчанию."""
    return {
        "gestures": {
            "one_finger": {
                "name": "1 палец",
                "finger_pattern": [False, True, False, False, False],
                "action": "activate_brightness",
                "hint": "Режим яркости"
            },
            "three_fingers": {
                "name": "3 пальца",
                "finger_pattern": [False, True, True, True, False],
                "action": "activate_sound",
                "hint": "Режим звука"
            },
            "two_fingers": {
                "name": "2 пальца",
                "finger_pattern": [False, True, True, False, False],
                "action": "exit",
                "hint": "Выход из режима"
            },
            "open_hand": {
                "name": "Ладонь",
                "finger_pattern": [True, True, True, True, True],
                "action": "cancel",
                "hint": "Отмена"
            }
        },
        "modes": {
            "brightness": {
                "name": "Яркость",
                "control_fingers": ["thumb", "index"],
                "slider_color": [0, 255, 0],
                "label": "Яркость: {}%"
            },
            "sound": {
                "name": "Звук",
                "control_fingers": ["thumb", "index"],
                "slider_color": [255, 165, 0],
                "label": "Звук: {}%"
            }
        },
        "ui_texts": {
            "title": "Жестовое управление",
            "mode_active": "РЕЖИМ АКТИВЕН",
            "confirm_hint": "Лайк - подтвердить | Дизлайк - отмена"
        },
        "settings": {
            "gesture_cooldown": 30,
            "gesture_display_time": 60,
            "min_distance": 30,
            "max_distance": 200,
            "camera_width": 1280,
            "camera_height": 720,
            "detection_confidence": 0.7,
            "tracking_confidence": 0.6,
            "max_hands": 2,
            "smoothing_factor": 0.3
        }
    }

CONFIG = load_config()
SETTINGS = CONFIG["settings"]
UI_TEXTS = CONFIG["ui_texts"]
MODES = CONFIG["modes"]
GESTURES = CONFIG["gestures"]

# ============================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (для обратной совместимости)
# ============================================================
current_mode = None
pending_mode = None
brightness_value = 50
sound_value = 50
smoothed_brightness = 50
smoothed_sound = 50

# ============================================================
# MEDIAPIPE TASKS (Tasks API, без solutions)
# ============================================================
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode
BaseOptions = mp.tasks.BaseOptions

# ============================================================
# ЗАГРУЗКА МОДЕЛИ HAND LANDMARKER
# ============================================================
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_FILENAME = "hand_landmarker.task"
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

def download_model():
    """Скачивает модель hand_landmarker.task, если её нет."""
    if os.path.exists(MODEL_PATH):
        print(f"  [МОДЕЛЬ] Найдена: {MODEL_PATH}")
        return True

    os.makedirs(MODEL_DIR, exist_ok=True)

    print(f"  [МОДЕЛЬ] Загрузка модели...")
    try:
        import urllib.request
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"  [МОДЕЛЬ] Модель загручена: {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"  [МОДЕЛЬ] Ошибка загрузки: {e}")
        return False

# ============================================================
# ШРИФТЫ
# ============================================================
FONT_CANDIDATES = [
    "arial.ttf",
    "segoeui.ttf",
    "tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
]

# ============================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ СО ЗВУКОМ
# ============================================================
class SoundController:
    """Контроллер для управления звуком системы."""

    def __init__(self):
        self.volume_interface = None
        self.initialized = False

        if not SOUND_AVAILABLE:
            print("  [ЗВУК] pycaw не установлен (SOUND_AVAILABLE = False)")
            return

        try:
            print("  [ЗВУК] Попытка инициализации...")
            from pycaw.pycaw import AudioUtilities
            device = AudioUtilities.GetSpeakers()
            if device is None:
                print("  [ЗВУК] GetSpeakers() вернул None")
                return
            self.volume_interface = device.EndpointVolume
            self.initialized = True
            current_vol = self.get_volume()
            print(f"  [ЗВУК] Инициализация успешна! Текущая громкость: {current_vol}%")
        except Exception as e:
            print(f"Ошибка инициализации звука: {e}")
            import traceback
            traceback.print_exc()
            self.initialized = False

    def set_volume(self, value):
        """Устанавливает громкость (0-100)."""
        if not self.initialized:
            print(f"  [ЗВУК] Не инициализирован, пропускаю установку {value}%")
            return
        try:
            volume = value / 100.0
            self.volume_interface.SetMasterVolumeLevelScalar(volume, None)
        except Exception as e:
            print(f"Ошибка установки звука: {e}")

    def get_volume(self):
        """Получает текущую громкость (0-100)."""
        if not self.initialized:
            return 50
        try:
            volume = self.volume_interface.GetMasterVolumeLevelScalar()
            return int(volume * 100)
        except Exception:
            return 50

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def distance(p1, p2):
    """Евклидово расстояние между двумя точками."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_finger_states(landmarks):
    """
    Определяет, какие пальцы подняты.
    landmarks — список из 21 точки (MediaPipe HandLandmarkerResult).
    Возвращает [thumb, index, middle, ring, pinky] — True/False.
    """
    fingers = []

    # Большой палец — улучшенное распознавание для ладони
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]  # IP сустав большого пальца
    thumb_mcp = landmarks[2]  # MCP сустав большого пальца
    index_mcp = landmarks[5]  # MCP сустав указательного
    
    # Расстояние от кончика большого до MCP указательного (для определения отведения)
    thumb_palm_dist = math.sqrt(
        (thumb_tip.x - index_mcp.x) ** 2 + (thumb_tip.y - index_mcp.y) ** 2
    )
    # Расстояние от IP до MCP большого пальца (для определения разогнутости)
    thumb_extension = math.sqrt(
        (thumb_tip.x - thumb_ip.x) ** 2 + (thumb_tip.y - thumb_ip.y) ** 2
    )
    # Вертикальная позиция: кончик большого пальца выше MCP
    thumb_above_mcp = thumb_tip.y < thumb_mcp.y - 0.01
    
    # Комбинированный критерий: большой палец поднят
    fingers.append(thumb_palm_dist > 0.10 and thumb_extension > 0.06)

    # Остальные 4 пальца — улучшенное распознавание для ладони
    for tip, pip_, dip_, mcp_ in [(8, 6, 7, 5), (12, 10, 11, 9), (16, 14, 15, 13), (20, 18, 19, 17)]:
        tip_point = landmarks[tip]
        pip_point = landmarks[pip_]
        dip_point = landmarks[dip_]
        mcp_point = landmarks[mcp_]
        
        # Критерий 1: кончик выше PIP (основной) - более мягкий порог
        is_above_pip = tip_point.y < pip_point.y - 0.005
        
        # Критерий 2: палец разогнут (DIP выше PIP) - более мягкий порог
        is_straight = dip_point.y < pip_point.y - 0.002
        
        # Критерий 3: кончик выше MCP (дополнительный) - более мягкий порог
        is_above_mcp = tip_point.y < mcp_point.y - 0.01
        
        # Комбинируем: нужно хотя бы 2 из 3 критериев
        criteria_met = sum([is_above_pip, is_straight, is_above_mcp]) >= 2
        fingers.append(criteria_met)

    return fingers


def match_gesture(finger_states, pattern):
    """Проверяет, соответствует ли жест шаблону."""
    if len(finger_states) != len(pattern):
        return False
    # Для ладони (все пальцы вверх) - мягкое соответствие (4 из 5)
    if pattern == [True, True, True, True, True]:
        matches = sum(1 for fs in finger_states if fs)
        return matches >= 4
    
    # Для остальных жестов - строгое соответствие (все 5)
    matches = sum(1 for fs, pat in zip(finger_states, pattern) if fs == pat)
    return matches == 5


def is_open_hand(finger_states):
    """Специальная проверка на ладонь (все 5 пальцев вверх)."""
    # Для ладони достаточно 4 из 5 пальцев
    raised_count = sum(1 for fs in finger_states if fs)
    return raised_count >= 4


def print_finger_states(finger_states):
    """Выводит состояние пальцев для отладки."""
    labels = ['большой', 'указательный', 'средний', 'безымянный', 'мизинец']
    states_str = ', '.join(f"{lbl}: {'↑' if st else '↓'}" for lbl, st in zip(labels, finger_states))
    print(f"  Пальцы: {states_str}")


def get_finger_indices(finger_names):
    """Возвращает индексы кончиков пальцев по названиям."""
    finger_map = {
        "thumb": 4,
        "index": 8,
        "middle": 12,
        "ring": 16,
        "pinky": 20
    }
    return [finger_map[name] for name in finger_names]


def smooth_value(current, target, factor=0.3):
    """Плавное изменение значения (экспоненциальное сглаживание)."""
    return current + (target - current) * factor


def _draw_landmarks(frame, landmarks, connections):
    """Рисует landmarks и соединения на кадре (аналог mp_drawing.draw_landmarks)."""
    h, w, _ = frame.shape

    # Рисуем соединения
    for conn in connections:
        start_idx, end_idx = conn
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            start = landmarks[start_idx]
            end = landmarks[end_idx]
            pt1 = (int(start.x * w), int(start.y * h))
            pt2 = (int(end.x * w), int(end.y * h))
            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

    # Рисуем точки
    for lm in landmarks:
        pt = (int(lm.x * w), int(lm.y * h))
        cv2.circle(frame, pt, 3, (255, 0, 0), -1)


# Стандартные соединения руки (из MediaPipe)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # Большой
    (0, 5), (5, 6), (6, 7), (7, 8),          # Указательный
    (0, 9), (9, 10), (10, 11), (11, 12),     # Средний
    (0, 13), (13, 14), (14, 15), (15, 16),   # Безымянный
    (0, 17), (17, 18), (18, 19), (19, 20),   # Мизинец
    (5, 9), (9, 13), (13, 17),               # Ладонь
]


# ============================================================
# ОТРИСОВКА
# ============================================================
def get_font(size):
    """Возвращает шрифт с поддержкой кириллицы (если найден)."""
    if not PIL_AVAILABLE:
        return None
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_slider(frame, lm, finger_indices, color, min_dist=30, max_dist=200):
    """
    Рисует полоску между двумя пальцами.
    Возвращает значение (0-100) на основе расстояния.
    """
    h, w, _ = frame.shape

    p1 = (int(lm[finger_indices[0]].x * w), int(lm[finger_indices[0]].y * h))
    p2 = (int(lm[finger_indices[1]].x * w), int(lm[finger_indices[1]].y * h))

    dist = distance(p1, p2)
    value = np.clip((dist - min_dist) / (max_dist - min_dist) * 100, 0, 100)

    thickness = 3
    cv2.line(frame, p1, p2, color, thickness)
    cv2.circle(frame, p1, 8, color, -1)
    cv2.circle(frame, p2, 8, color, -1)

    slider_x = w - 60
    slider_y = h // 2
    slider_height = 200
    slider_width = 30

    cv2.rectangle(frame,
                  (slider_x, slider_y - slider_height // 2),
                  (slider_x + slider_width, slider_y + slider_height // 2),
                  (50, 50, 50), -1)

    fill_height = int(value / 100 * slider_height)
    cv2.rectangle(frame,
                  (slider_x + 3, slider_y + slider_height // 2 - fill_height),
                  (slider_x + slider_width - 3, slider_y + slider_height // 2),
                  color, -1)

    cv2.rectangle(frame,
                  (slider_x, slider_y - slider_height // 2),
                  (slider_x + slider_width, slider_y + slider_height // 2),
                  (255, 255, 255), 2)

    return int(value)


def draw_gesture_info(frame, gesture, action, font_small=None):
    """Рисует информацию о распознанном жесте."""
    h, w, _ = frame.shape

    if not gesture or not action:
        return frame

    if not PIL_AVAILABLE:
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, f"Жест: {gesture}", (w // 2 - 100, h - 80),
                    font, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, action, (w // 2 - 120, h - 55),
                    font, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
        return frame

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(image)

    if font_small is None:
        font_small = get_font(24)

    font_medium = get_font(28)

    gesture_text = f"Распознан жест: {gesture}"
    bbox = draw.textbbox((0, 0), gesture_text, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, h - 90), gesture_text, font=font_medium, fill=(255, 255, 0))

    bbox = draw.textbbox((0, 0), action, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, h - 60), action, font=font_small, fill=(0, 255, 255))

    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr


def draw_mode_ui(frame, mode, value, font_small=None):
    """Рисует UI для активного режима (яркость или звук)."""
    h, w, _ = frame.shape
    mode_config = MODES[mode]

    if not PIL_AVAILABLE:
        cv2.rectangle(frame, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.putText(frame, mode_config["name"], (w // 2 - 100, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, UI_TEXTS["mode_active"], (w // 2 - 80, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, mode_config["label"].format(value), (w // 2 - 70, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2, cv2.LINE_AA)
        return frame

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(image)

    if font_small is None:
        font_small = get_font(24)

    font_title = get_font(32)

    overlay = np.array(image)
    cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
    image = Image.fromarray(cv2.addWeighted(overlay, 0.5, np.array(image), 0.5, 0))
    draw = ImageDraw.Draw(image)

    draw.text((w // 2 - 80, 10), mode_config["name"], font=font_title, fill=(255, 255, 255))
    draw.text((w // 2 - 60, 45), UI_TEXTS["mode_active"], font=font_small, fill=(0, 255, 0))

    value_text = mode_config["label"].format(value)
    draw.text((w // 2 - 60, 75), value_text, font=font_small, fill=(255, 255, 0))

    draw.text((10, h - 35), "2 пальца - выход", font=font_small, fill=(0, 255, 255))

    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr


def draw_confirm_ui(frame, pending_mode_name, hold_progress, hold_gesture_name, font_small=None):
    """Рисует UI для удержания жеста с прогрессом."""
    h, w, _ = frame.shape

    if not PIL_AVAILABLE:
        # Фолбэк на OpenCV
        cv2.rectangle(frame, (0, 0), (w, 150), (0, 0, 0), -1)
        text1 = f"Удерживайте жест: {hold_gesture_name}"
        text2 = f"Режим: {pending_mode_name}"
        text3 = f"Прогресс: {int(hold_progress * 100)}%"
        cv2.putText(frame, text1, (w // 2 - 150, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, text2, (w // 2 - 100, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, text3, (w // 2 - 80, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        
        # Рисуем полосу прогресса
        bar_width = 300
        bar_height = 20
        bar_x = (w - bar_width) // 2
        bar_y = 125
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
        fill_width = int(bar_width * hold_progress)
        if fill_width > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_width, bar_y + bar_height), (0, 255, 0), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (255, 255, 255), 2)
        
        return frame

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(image)

    if font_small is None:
        font_small = get_font(24)

    font_medium = get_font(28)
    font_large = get_font(32)

    # Полупрозрачный фон
    overlay = np.array(image)
    cv2.rectangle(overlay, (0, 0), (w, 150), (0, 0, 0), -1)
    image = Image.fromarray(cv2.addWeighted(overlay, 0.5, np.array(image), 0.5, 0))
    draw = ImageDraw.Draw(image)

    # Заголовок
    title = f"Удерживайте жест: {hold_gesture_name}"
    bbox = draw.textbbox((0, 0), title, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 10), title, font=font_medium, fill=(255, 255, 0))

    # Режим
    mode_text = f"Режим: {pending_mode_name}"
    bbox = draw.textbbox((0, 0), mode_text, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 50), mode_text, font=font_small, fill=(0, 255, 255))

    # Прогресс в процентах
    progress_text = f"{int(hold_progress * 100)}%"
    bbox = draw.textbbox((0, 0), progress_text, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 80), progress_text, font=font_large, fill=(0, 255, 0))

    # Полоса прогресса
    bar_width = 300
    bar_height = 20
    bar_x = (w - bar_width) // 2
    bar_y = 120
    
    # Фон полосы
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(100, 100, 100))
    # Заполненная часть
    fill_width = int(bar_width * hold_progress)
    if fill_width > 0:
        draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=(0, 255, 0))
    # Граница
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], outline=(255, 255, 255), width=2)

    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr


# ============================================================
# КЛАСС: ОБРАБОТЧИК ЖЕСТОВ
# ============================================================
class GestureProcessor:
    """
    Инкапсулирует всю логику обработки жестов:
    - MediaPipe HandLandmarker (Tasks API)
    - Распознавание жестов
    - Управление яркостью/звуком
    - Отрисовка UI поверх кадра
    """

    def __init__(self):
        self.config = CONFIG
        self.gestures = GESTURES
        self.settings = SETTINGS
        self.modes = MODES
        self.ui_texts = UI_TEXTS

        # Состояние
        self.current_mode = None
        self.pending_mode = None
        self.brightness_value = 50
        self.sound_value = 50
        self.smoothed_brightness = 50
        self.smoothed_sound = 50
        self.gesture_cooldown = 0
        self.current_gesture = ""
        self.current_action = ""
        self.gesture_timer = 0
        self.confirm_timer = 0
        
        # Новая система удержания
        self.hold_gesture_name = ""  # Жест который нужно удерживать
        self.hold_progress = 0.0  # Прогресс удержания (0.0 - 1.0)
        self.hold_required_frames = 90  # ~3 секунды при 30 FPS
        self.hold_current_frames = 0  # Текущее количество удержанных кадров
        self.last_detected_fs = None  # Последние состояния пальцев

        # Контроллер звука
        self.sound_controller = SoundController()
        if self.sound_controller.initialized:
            self.sound_value = self.sound_controller.get_volume()
            self.smoothed_sound = self.sound_value

        # Индексы пальцев для режимов
        self.brightness_fingers = get_finger_indices(self.modes["brightness"]["control_fingers"])
        self.sound_fingers = get_finger_indices(self.modes["sound"]["control_fingers"])
        self.smoothing_factor = self.settings.get("smoothing_factor", 0.3)

        # MediaPipe HandLandmarker (Tasks API)
        self.landmarker = None

        # Загружаем модель, если её нет
        if not download_model():
            print("Ошибка: не удалось загрузить модель!")
            return

        try:
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=VisionRunningMode.IMAGE,
                num_hands=self.settings["max_hands"],
                min_hand_detection_confidence=self.settings["detection_confidence"],
                min_hand_presence_confidence=self.settings["tracking_confidence"],
                min_tracking_confidence=self.settings["tracking_confidence"],
            )
            self.landmarker = HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Ошибка инициализации HandLandmarker: {e}")

        self.font_small = get_font(24)

    def process_frame(self, frame):
        """
        Принимает кадр (BGR numpy array), возвращает кадр с отрисованным UI.
        """
        if frame is None:
            return frame

        # Зеркалим кадр
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Конвертируем BGR → RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Детектируем руки через Tasks API
        detection_result = self.landmarker.detect(mp_image)

        hands_data = {}

        if detection_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                # Определяем левую/правую руку
                handedness_list = detection_result.handedness
                if idx < len(handedness_list) and len(handedness_list[idx]) > 0:
                    category = handedness_list[idx][0]
                    label = "Right" if category.category_name == "Right" else "Left"
                else:
                    label = "Right"

                # Рисуем скелет руки
                _draw_landmarks(frame, hand_landmarks, HAND_CONNECTIONS)

                # Определяем состояние пальцев
                finger_states = get_finger_states(hand_landmarks)

                hands_data[label] = {
                    "landmarks": hand_landmarks,
                    "label": label,
                    "finger_states": finger_states,
                }

        # ====================================================
        # ЛОГИКА УПРАВЛЕНИЯ (новая система удержания)
        # ====================================================
        detected_gesture = ""
        detected_action = ""
        
        # Проверяем жесты на ЛЮБОЙ руке
        for hand_key, hand_info in hands_data.items():
            current_fs = hand_info["finger_states"]
            
            # Если есть pending_mode, проверяем удержание жеста
            if self.pending_mode is not None:
                # Определяем какой жест нужно удерживать
                target_gesture_key = "one_finger" if self.pending_mode == "brightness" else "three_fingers"
                target_gesture_config = self.gestures[target_gesture_key]
                
                # Проверяем жест выхода из подтверждения (ладонь) - приоритетнее удержания
                if is_open_hand(current_fs):
                    # Выход из подтверждения
                    self.pending_mode = None
                    self.hold_gesture_name = ""
                    self.hold_progress = 0.0
                    self.hold_current_frames = 0
                    self.gesture_cooldown = self.settings["gesture_cooldown"]
                    detected_gesture = "Ладонь"
                    detected_action = "Выход из подтверждения"
                    print("  >>> Выход из подтверждения (ладонь)")
                    break
                
                # Проверяем, соответствует ли текущий жест целевому для удержания
                if match_gesture(current_fs, target_gesture_config["finger_pattern"]):
                    # Удерживаем жест
                    self.hold_current_frames += 1
                    self.hold_progress = min(1.0, self.hold_current_frames / self.hold_required_frames)
                    
                    detected_gesture = target_gesture_config["name"]
                    detected_action = f"Удерживайте... {int(self.hold_progress * 100)}%"
                    
                    # Если удержание завершено
                    if self.hold_current_frames >= self.hold_required_frames:
                        if self.pending_mode == "brightness":
                            self.current_mode = "brightness"
                            print("  >>> Режим яркости АКТИВИРОВАН")
                        elif self.pending_mode == "sound":
                            self.current_mode = "sound"
                            print("  >>> Режим звука АКТИВИРОВАН")
                        self.pending_mode = None
                        self.hold_gesture_name = ""
                        self.hold_progress = 0.0
                        self.hold_current_frames = 0
                        self.gesture_cooldown = self.settings["gesture_cooldown"]
                        detected_gesture = target_gesture_config["name"]
                        detected_action = "Активировано!"
                else:
                    # Жест не удерживается или это другой жест - сброс прогресса
                    if self.hold_current_frames > 0:
                        print(f"  >>> Удержание прервано (было {self.hold_current_frames} кадров)")
                    self.hold_current_frames = 0
                    self.hold_progress = 0.0
            else:
                # Нет pending_mode - проверяем жесты активации
                if self.gesture_cooldown <= 0:
                    for gesture_name, gesture_config in self.gestures.items():
                        if match_gesture(current_fs, gesture_config["finger_pattern"]):
                            action = gesture_config["action"]

                            # Активация режима яркости
                            if action == "activate_brightness":
                                if self.current_mode is None and self.pending_mode is None:
                                    self.pending_mode = "brightness"
                                    self.hold_gesture_name = gesture_config["name"]
                                    self.hold_current_frames = 0
                                    self.hold_progress = 0.0
                                    print("  >>> Удерживайте 1 палец для активации яркости...")
                                    detected_gesture = gesture_config["name"]
                                    detected_action = "Удерживайте 3 секунды для активации"

                            # Активация режима звука
                            elif action == "activate_sound":
                                if self.current_mode is None and self.pending_mode is None:
                                    self.pending_mode = "sound"
                                    self.hold_gesture_name = gesture_config["name"]
                                    self.hold_current_frames = 0
                                    self.hold_progress = 0.0
                                    print("  >>> Удерживайте 3 пальца для активации звука...")
                                    detected_gesture = gesture_config["name"]
                                    detected_action = "Удерживайте 3 секунды для активации"

                            # Выход из режима (2 пальца)
                            elif action == "exit":
                                if self.current_mode is not None:
                                    self.current_mode = None
                                    self.pending_mode = None
                                    self.hold_gesture_name = ""
                                    self.hold_progress = 0.0
                                    self.hold_current_frames = 0
                                    print("  >>> Выход из режима")
                                    self.gesture_cooldown = self.settings["gesture_cooldown"]
                                    detected_gesture = gesture_config["name"]
                                    detected_action = gesture_config["hint"]

                            break


        # Обновляем значение в активном режиме
        current_value = self.brightness_value if self.current_mode == "brightness" else self.sound_value

        if self.current_mode == "brightness" and "Left" in hands_data:
            lm = hands_data["Left"]["landmarks"]
            raw_value = draw_slider(
                frame, lm, self.brightness_fingers,
                self.modes["brightness"]["slider_color"],
                self.settings["min_distance"], self.settings["max_distance"]
            )
            self.smoothed_brightness = smooth_value(self.smoothed_brightness, raw_value, self.smoothing_factor)
            self.brightness_value = int(self.smoothed_brightness)
            current_value = self.brightness_value

            if BRIGHTNESS_AVAILABLE:
                try:
                    sbc.set_brightness(self.brightness_value)
                except Exception as e:
                    print(f"  Ошибка яркости: {e}")

        elif self.current_mode == "sound" and "Left" in hands_data:
            lm = hands_data["Left"]["landmarks"]
            raw_value = draw_slider(
                frame, lm, self.sound_fingers,
                self.modes["sound"]["slider_color"],
                self.settings["min_distance"], self.settings["max_distance"]
            )
            self.smoothed_sound = smooth_value(self.smoothed_sound, raw_value, self.smoothing_factor)
            self.sound_value = int(self.smoothed_sound)
            current_value = self.sound_value

            print(f"  >>> Звук: {self.sound_value}% (raw: {raw_value})")

            self.sound_controller.set_volume(self.sound_value)

        # Сохраняем распознанный жест
        if detected_gesture:
            self.current_gesture = detected_gesture
            self.current_action = detected_action
            self.gesture_timer = self.settings["gesture_display_time"]

        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1

        if self.gesture_timer > 0:
            self.gesture_timer -= 1

        # ====================================================
        # ОТРИСОВКА UI
        # ====================================================
        if self.pending_mode is not None:
            mode_name = "Яркость" if self.pending_mode == "brightness" else "Звук"
            hold_gesture = "1 палец" if self.pending_mode == "brightness" else "3 пальца"
            frame = draw_confirm_ui(frame, mode_name, self.hold_progress, hold_gesture, self.font_small)
        elif self.current_mode is not None:
            frame = draw_mode_ui(frame, self.current_mode, current_value, self.font_small)

        # Рисуем информацию о жесте
        if self.gesture_timer > 0 and self.current_gesture and self.current_action:
            frame = draw_gesture_info(frame, self.current_gesture, self.current_action, self.font_small)

        return frame

    def get_status_text(self):
        """Возвращает строку статуса для отображения в GUI."""
        parts = []

        if self.pending_mode is not None:
            mode_name = "Яркость" if self.pending_mode == "brightness" else "Звук"
            hold_gesture = "1 палец" if self.pending_mode == "brightness" else "3 пальца"
            parts.append(f"Удерживайте: {hold_gesture}")
            parts.append(f"Режим: {mode_name}")
            parts.append(f"Прогресс: {int(self.hold_progress * 100)}%")
            parts.append("Ладонь — выход из подтверждения")
        elif self.current_mode is not None:
            mode_config = self.modes[self.current_mode]
            value = self.brightness_value if self.current_mode == "brightness" else self.sound_value
            parts.append(f"{mode_config['name']}: {value}%")
            parts.append("РЕЖИМ АКТИВЕН")
            parts.append("2 пальца — выход из режима")

        if self.gesture_timer > 0 and self.current_gesture and self.current_action:
            parts.append(f"Жест: {self.current_gesture}")
            parts.append(self.current_action)

        if not parts:
            parts.append("Покажите жест для управления")
            parts.append("1 палец — яркость | 3 пальца — звук")
            parts.append("Ладонь — выход из подтверждения")

        return "\n".join(parts)

    def shutdown(self):
        """Освобождает ресурсы."""
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def reset(self):
        """Сбрасывает состояние обработчика."""
        self.current_mode = None
        self.pending_mode = None
        self.brightness_value = 50
        self.sound_value = 50
        self.smoothed_brightness = 50
        self.smoothed_sound = 50
        self.gesture_cooldown = 0
        self.current_gesture = ""
        self.current_action = ""
        self.gesture_timer = 0
        self.confirm_timer = 0
        self.hold_gesture_name = ""
        self.hold_progress = 0.0
        self.hold_current_frames = 0
        self.last_detected_fs = None


# ============================================================
# КЛАСС: ПОТОК КАМЕРЫ ДЛЯ ЖЕСТОВ
# ============================================================
class GestureCameraThread(QThread):
    """
    Фоновый поток для работы с камерой.
    Сигналы:
        frame_ready(QImage) — готовый кадр с отрисованным UI
        status_ready(str) — текстовый статус
    """
    frame_ready = pyqtSignal(QImage)
    status_ready = pyqtSignal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.processor = None
        self.cap = None
        self._running = False

    def run(self):
        self._running = True
        self.processor = GestureProcessor()

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.status_ready.emit("Ошибка: не удалось открыть камеру!")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.processor.settings["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.processor.settings["camera_height"])

        print("=" * 50)
        print("  Жестовое управление запущено!")
        print("  1 палец (указательный вверх) - режим яркости")
        print("  3 пальца (указательный, средний, безымянный) - режим звука")
        print("  Удерживайте жест 3 секунды для активации")
        print("  Ладонь (все пальцы вверх) - выход из подтверждения")
        print("  2 пальца - выход из режима")
        print("=" * 50)

        if not BRIGHTNESS_AVAILABLE:
            print("  Предупреждение: screen-brightness-control не установлен")
        if not self.processor.sound_controller.initialized:
            print("  Предупреждение: управление звуком недоступно")

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            # Проверяем, не остановили ли нас
            if not self._running:
                break

            # Обрабатываем кадр
            processed_frame = self.processor.process_frame(frame)

            # Конвертируем BGR → RGB → QImage
            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            if self._running:
                self.frame_ready.emit(q_image)

            # Эмитим статус
            status = self.processor.get_status_text()
            if self._running:
                self.status_ready.emit(status)

            # ~30 FPS
            self.msleep(33)

        # Очистка
        self.cap.release()
        self.processor.shutdown()
        self.processor = None
        self.cap = None

    def stop(self):
        """Останавливает поток."""
        self._running = False
        self.wait()


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ (standalone запуск)
# ============================================================
def main():
    global current_mode, pending_mode, brightness_value, sound_value, smoothed_brightness, smoothed_sound

    # Загружаем конфигурацию
    config = CONFIG
    gestures = GESTURES
    settings = SETTINGS

    # Инициализация камеры
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings["camera_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings["camera_height"])

    # Состояние
    gesture_cooldown = 0
    current_gesture = ""
    current_action = ""
    gesture_timer = 0
    
    # Новая система удержания
    hold_progress = 0.0
    hold_current_frames = 0
    hold_required_frames = 90  # ~3 секунды при 30 FPS

    # Контроллер звука
    sound_controller = SoundController()
    if sound_controller.initialized:
        sound_value = sound_controller.get_volume()
        smoothed_sound = sound_value

    smoothed_brightness = brightness_value

    # Индексы пальцев для режимов
    brightness_fingers = get_finger_indices(MODES["brightness"]["control_fingers"])
    sound_fingers = get_finger_indices(MODES["sound"]["control_fingers"])

    smoothing_factor = settings.get("smoothing_factor", 0.3)

    # Загружаем модель, если её нет
    if not download_model():
        print("Ошибка: не удалось загрузить модель!")
        return

    # Создаём HandLandmarker через Tasks API
    try:
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=VisionRunningMode.IMAGE,
            num_hands=settings["max_hands"],
            min_hand_detection_confidence=settings["detection_confidence"],
            min_hand_presence_confidence=settings["tracking_confidence"],
            min_tracking_confidence=settings["tracking_confidence"],
        )
        landmarker = HandLandmarker.create_from_options(options)
    except Exception as e:
        print(f"Ошибка создания HandLandmarker: {e}")
        return

    font_small = get_font(24)

    print("=" * 50)
    print("  Жестовое управление запущено!")
    print("  1 палец (указательный вверх) - режим яркости")
    print("  3 пальца (указательный, средний, безымянный) - режим звука")
    print("  Удерживайте жест 3 секунды для активации")
    print("  Ладонь (все пальцы вверх) - выход из подтверждения")
    print("  2 пальца - выход из режима")
    print("  Нажмите 'q' для выхода.")
    print("=" * 50)

    if not BRIGHTNESS_AVAILABLE:
        print("  Предупреждение: screen-brightness-control не установлен")
    if not sound_controller.initialized:
        print("  Предупреждение: управление звуком недоступно")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Зеркалим кадр
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Конвертируем BGR → RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Детектируем руки через Tasks API
        detection_result = landmarker.detect(mp_image)

        hands_data = {}

        if detection_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                handedness_list = detection_result.handedness
                if idx < len(handedness_list) and len(handedness_list[idx]) > 0:
                    category = handedness_list[idx][0]
                    label = "Right" if category.category_name == "Right" else "Left"
                else:
                    label = "Right"

                # Рисуем скелет руки
                _draw_landmarks(frame, hand_landmarks, HAND_CONNECTIONS)

                finger_states = get_finger_states(hand_landmarks)
                print_finger_states(finger_states)

                hands_data[label] = {
                    "landmarks": hand_landmarks,
                    "label": label,
                    "finger_states": finger_states,
                }

        detected_gesture = ""
        detected_action = ""
        
        # Проверяем жесты на ЛЮБОЙ руке
        for hand_key, hand_info in hands_data.items():
            current_fs = hand_info["finger_states"]
            
            # Если есть pending_mode, проверяем удержание жеста
            if pending_mode is not None:
                # Определяем какой жест нужно удерживать
                target_gesture_key = "one_finger" if pending_mode == "brightness" else "three_fingers"
                target_gesture_config = gestures[target_gesture_key]
                
                # Проверяем жест выхода из подтверждения (ладонь) - приоритетнее удержания
                if is_open_hand(current_fs):
                    # Выход из подтверждения
                    pending_mode = None
                    hold_progress = 0.0
                    hold_current_frames = 0
                    gesture_cooldown = settings["gesture_cooldown"]
                    detected_gesture = "Ладонь"
                    detected_action = "Выход из подтверждения"
                    print("  >>> Выход из подтверждения (ладонь)")
                    break
                
                # Проверяем, соответствует ли текущий жест целевому для удержания
                if match_gesture(current_fs, target_gesture_config["finger_pattern"]):
                    # Удерживаем жест
                    hold_current_frames += 1
                    hold_progress = min(1.0, hold_current_frames / hold_required_frames)
                    
                    detected_gesture = target_gesture_config["name"]
                    detected_action = f"Удерживайте... {int(hold_progress * 100)}%"
                    
                    # Если удержание завершено
                    if hold_current_frames >= hold_required_frames:
                        if pending_mode == "brightness":
                            current_mode = "brightness"
                            print("  >>> Режим яркости АКТИВИРОВАН")
                        elif pending_mode == "sound":
                            current_mode = "sound"
                            print("  >>> Режим звука АКТИВИРОВАН")
                        pending_mode = None
                        hold_progress = 0.0
                        hold_current_frames = 0
                        gesture_cooldown = settings["gesture_cooldown"]
                        detected_gesture = target_gesture_config["name"]
                        detected_action = "Активировано!"
                else:
                    # Жест не удерживается или это другой жест - сброс прогресса
                    if hold_current_frames > 0:
                        print(f"  >>> Удержание прервано (было {hold_current_frames} кадров)")
                    hold_current_frames = 0
                    hold_progress = 0.0
            else:
                # Нет pending_mode - проверяем жесты активации
                if gesture_cooldown <= 0:
                    for gesture_name, gesture_config in gestures.items():
                        if match_gesture(current_fs, gesture_config["finger_pattern"]):
                            action = gesture_config["action"]

                            # Активация режима яркости
                            if action == "activate_brightness":
                                if current_mode is None and pending_mode is None:
                                    pending_mode = "brightness"
                                    hold_current_frames = 0
                                    hold_progress = 0.0
                                    print("  >>> Удерживайте 1 палец для активации яркости...")
                                    detected_gesture = gesture_config["name"]
                                    detected_action = "Удерживайте 3 секунды для активации"

                            # Активация режима звука
                            elif action == "activate_sound":
                                if current_mode is None and pending_mode is None:
                                    pending_mode = "sound"
                                    hold_current_frames = 0
                                    hold_progress = 0.0
                                    print("  >>> Удерживайте 3 пальца для активации звука...")
                                    detected_gesture = gesture_config["name"]
                                    detected_action = "Удерживайте 3 секунды для активации"

                            # Выход из режима (2 пальца)
                            elif action == "exit":
                                if current_mode is not None:
                                    current_mode = None
                                    pending_mode = None
                                    hold_progress = 0.0
                                    hold_current_frames = 0
                                    print("  >>> Выход из режима")
                                    gesture_cooldown = settings["gesture_cooldown"]
                                    detected_gesture = gesture_config["name"]
                                    detected_action = gesture_config["hint"]

                            break


        # Обновляем значение в активном режиме
        current_value = brightness_value if current_mode == "brightness" else sound_value

        if current_mode == "brightness" and "Left" in hands_data:
            lm = hands_data["Left"]["landmarks"]
            raw_value = draw_slider(
                frame, lm, brightness_fingers,
                MODES["brightness"]["slider_color"],
                settings["min_distance"], settings["max_distance"]
            )
            smoothed_brightness = smooth_value(smoothed_brightness, raw_value, smoothing_factor)
            brightness_value = int(smoothed_brightness)
            current_value = brightness_value

            if BRIGHTNESS_AVAILABLE:
                try:
                    sbc.set_brightness(brightness_value)
                except Exception as e:
                    print(f"  Ошибка яркости: {e}")

        elif current_mode == "sound" and "Left" in hands_data:
            lm = hands_data["Left"]["landmarks"]
            raw_value = draw_slider(
                frame, lm, sound_fingers,
                MODES["sound"]["slider_color"],
                settings["min_distance"], settings["max_distance"]
            )
            smoothed_sound = smooth_value(smoothed_sound, raw_value, smoothing_factor)
            sound_value = int(smoothed_sound)
            current_value = sound_value

            print(f"  >>> Звук: {sound_value}% (raw: {raw_value})")
            sound_controller.set_volume(sound_value)

        # Сохраняем распознанный жест
        if detected_gesture:
            current_gesture = detected_gesture
            current_action = detected_action
            gesture_timer = settings["gesture_display_time"]

        if gesture_cooldown > 0:
            gesture_cooldown -= 1

        if gesture_timer > 0:
            gesture_timer -= 1

        # ====================================================
        # ОТРИСОВКА UI
        # ====================================================
        if pending_mode is not None:
            mode_name = "Яркость" if pending_mode == "brightness" else "Звук"
            hold_gesture = "1 палец" if pending_mode == "brightness" else "3 пальца"
            frame = draw_confirm_ui(frame, mode_name, hold_progress, hold_gesture, font_small)
        elif current_mode is not None:
            frame = draw_mode_ui(frame, current_mode, current_value, font_small)

        # Рисуем информацию о жесте
        if gesture_timer > 0 and current_gesture and current_action:
            frame = draw_gesture_info(frame, current_gesture, current_action, font_small)

        cv2.imshow(CONFIG["ui_texts"]["title"], frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    cap.release()
    landmarker.close()
    cv2.destroyAllWindows()

    print(f"\n  Финальное значение яркости: {brightness_value}%")
    print(f"  Финальное значение звука: {sound_value}%")
    print("  Программа завершена.")


if __name__ == "__main__":
    main()
