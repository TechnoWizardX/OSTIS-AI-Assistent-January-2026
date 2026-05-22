# -*- coding: utf-8 -*-
"""
Жестовое управление — MediaPipe Tasks API.
Архитектура: GestureProcessor + GestureCameraThread для PyQt интерфейса.
"""

import cv2
import mediapipe as mp
import math
import numpy as np
import sys
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except ImportError:
    BRIGHTNESS_AVAILABLE = False

try:
    from pycaw.pycaw import AudioUtilities
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

print(sys.executable)

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "gestures_config.json")


def load_config() -> dict:
    """Загружает конфигурацию жестов из JSON файла."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return _default_config()


def _default_config() -> dict:
    """Конфигурация по умолчанию."""
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
        "actions": {
            "circle": {
                "name": "Круг (большой + указательный)",
                "description": "Действие: открыть",
                "command_name": "открой",
                "circle_threshold": 0.05,
                "hold_frames": 50
            }
        },
        "objects": {
            "one_finger": {
                "name": "1 палец вверх",
                "description": "Объект: браузер",
                "command_name": "браузер",
                "finger_pattern": [False, True, False, False, False],
                "hold_frames": 50
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
            "confirm_hint": "Удерживайте жест для активации",
            "action_prompt": "Покажите объект",
            "object_selected": "Объект выбран"
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
ACTIONS = CONFIG.get("actions", {})
OBJECTS = CONFIG.get("objects", {})

# ============================================================
# MEDIAPIPE TASKS API
# ============================================================
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Стандартные соединения руки
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]

# Модель
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_FILENAME = "hand_landmarker.task"
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

# Шрифты
FONT_CANDIDATES = [
    "arial.ttf", "segoeui.ttf", "tahoma.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
]

# Индексы кончиков пальцев
FINGER_TIP_MAP = {"thumb": 4, "index": 8, "middle": 12, "ring": 16, "pinky": 20}


# ============================================================
# DATA CLASS'Ы
# ============================================================
@dataclass
class HandData:
    """Данные о обнаруженной руке."""
    landmarks: list
    label: str
    finger_states: list

    @property
    def is_left(self) -> bool:
        return self.label == "Left"


@dataclass
class GestureState:
    """Состояние системы жестов."""
    current_mode: Optional[str] = None
    pending_mode: Optional[str] = None
    brightness_value: int = 50
    sound_value: int = 50
    smoothed_brightness: float = 50.0
    smoothed_sound: float = 50.0
    gesture_cooldown: int = 0
    current_gesture: str = ""
    current_action: str = ""
    gesture_timer: int = 0

    # Удержание жеста
    hold_gesture_name: str = ""
    hold_progress: float = 0.0
    hold_current_frames: int = 0

    # Система "действие + объект"
    action_mode: bool = False        # Ждём выбор объекта после подтверждения действия
    selected_action: str = ""        # Выбранное действие (напр. "открой")
    selected_object: str = ""        # Выбранный объект (напр. "браузер")
    object_hold_frames: int = 0      # Счётчик удержания жеста объекта
    hold_action: bool = False        # Удержание жеста действия (круг)
    hold_action_progress: float = 0.0  # Прогресс удержания действия
    # Буфер стабилизации жестов
    finger_state_buffer: List = field(default_factory=list)
    stable_finger_states: List = field(default_factory=lambda: [False] * 5)
    circle_buffer: List = field(default_factory=list)
    stable_circle: bool = False

    def reset(self):
        """Полный сброс состояния."""
        self.__init__()

    @property
    def current_value(self) -> int:
        """Текущее значение активного режима."""
        return self.brightness_value if self.current_mode == "brightness" else self.sound_value


# ============================================================
# МОДЕЛЬ
# ============================================================
def download_model() -> bool:
    """Скачивает модель hand_landmarker.task, если её нет."""
    if os.path.exists(MODEL_PATH):
        return True

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"  [МОДЕЛЬ] Загрузка модели...")
    try:
        import urllib.request
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"  [МОДЕЛЬ] Модель загружена: {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"  [МОДЕЛЬ] Ошибка загрузки: {e}")
        return False


# ============================================================
# ЗВУК
# ============================================================
class SoundController:
    """Контроллер громкости системы."""

    def __init__(self):
        self.volume_interface = None
        self.initialized = False

        if not SOUND_AVAILABLE:
            return

        try:
            device = AudioUtilities.GetSpeakers()
            if device:
                self.volume_interface = device.EndpointVolume
                self.initialized = True
        except Exception as e:
            print(f"Ошибка инициализации звука: {e}")

    def set_volume(self, value: int):
        if self.initialized:
            self.volume_interface.SetMasterVolumeLevelScalar(value / 100.0, None)

    def get_volume(self) -> int:
        if not self.initialized:
            return 50
        return int(self.volume_interface.GetMasterVolumeLevelScalar() * 100)


# ============================================================
# УТИЛИТЫ: вспомогательные функции и отрисовка UI
# ============================================================
class GestureUtils:
    """Вспомогательные функции: геометрия, распознавание пальцев, модель."""

    @staticmethod
    def distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @staticmethod
    def _vec3(a, b) -> Tuple[float, float, float]:
        """Вектор из точки a в точку b (3D)."""
        return (b.x - a.x, b.y - a.y, b.z - a.z)

    @staticmethod
    def _dot3(u: Tuple, v: Tuple) -> float:
        return u[0]*v[0] + u[1]*v[1] + u[2]*v[2]

    @staticmethod
    def _len3(v: Tuple) -> float:
        return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

    @staticmethod
    def _angle_between(a, vertex, b) -> float:
        """Угол в вершине vertex между точками a и b (в градусах), используя 3D координаты."""
        u = GestureUtils._vec3(vertex, a)
        v = GestureUtils._vec3(vertex, b)
        lu, lv = GestureUtils._len3(u), GestureUtils._len3(v)
        if lu < 1e-6 or lv < 1e-6:
            return 0.0
        cos_a = max(-1.0, min(1.0, GestureUtils._dot3(u, v) / (lu * lv)))
        return math.degrees(math.acos(cos_a))

    @staticmethod
    def _hand_scale(landmarks: list) -> float:
        """Масштаб руки: расстояние от запястья до основания среднего пальца."""
        wrist, mid_mcp = landmarks[0], landmarks[9]
        d = math.hypot(mid_mcp.x - wrist.x, mid_mcp.y - wrist.y)
        return max(d, 1e-5)

    @staticmethod
    def _palm_normal(landmarks: list) -> Tuple[float, float, float]:
        """Нормаль плоскости ладони через три MCP точки (векторное произведение)."""
        p0 = landmarks[0]   # запястье
        p5 = landmarks[5]   # MCP указательного
        p17 = landmarks[17] # MCP мизинца
        u = (p5.x - p0.x, p5.y - p0.y, p5.z - p0.z)
        v = (p17.x - p0.x, p17.y - p0.y, p17.z - p0.z)
        nx = u[1]*v[2] - u[2]*v[1]
        ny = u[2]*v[0] - u[0]*v[2]
        nz = u[0]*v[1] - u[1]*v[0]
        length = math.sqrt(nx**2 + ny**2 + nz**2)
        if length < 1e-6:
            return (0.0, -1.0, 0.0)
        return (nx/length, ny/length, nz/length)

    @staticmethod
    def get_finger_states(landmarks: list) -> list:
        """
        Определяет поднятые пальцы: [thumb, index, middle, ring, pinky].

        Улучшения по сравнению с исходным:
        - Большой палец: угол в IP-суставе + проекция на нормаль ладони,
          что корректно работает при любом наклоне руки.
        - Остальные пальцы: угол сгибания в PIP-суставе (>140° = выпрямлен)
          плюс проверка, что кончик выше MCP вдоль нормали ладони.
          Нормаль ладони делает алгоритм инвариантным к повороту камеры.
        - Масштаб руки не используется в порогах — они в градусах,
          поэтому не зависят от расстояния до камеры.
        """
        scale = GestureUtils._hand_scale(landmarks)
        palm_n = GestureUtils._palm_normal(landmarks)  # нормаль, смотрит «от ладони»

        # ── БОЛЬШОЙ ПАЛЕЦ ──────────────────────────────────────────────────
        # Угол в IP-суставе (lm[3]) между MCP(lm[2]) и кончиком(lm[4])
        thumb_angle = GestureUtils._angle_between(landmarks[2], landmarks[3], landmarks[4])
        # Вектор от CMC(lm[1]) до кончика(lm[4])
        tip_vec = GestureUtils._vec3(landmarks[1], landmarks[4])
        # Проекция кончика на нормаль ладони — если > 0, палец «снаружи» ладони
        tip_proj = GestureUtils._dot3(tip_vec, palm_n)
        # Расстояние от кончика большого до MCP указательного (старый критерий, нормированный)
        thumb_to_index = math.hypot(
            landmarks[4].x - landmarks[5].x,
            landmarks[4].y - landmarks[5].y
        ) / scale
        thumb_up = (thumb_angle > 140 or thumb_to_index > 0.35) and tip_proj > -0.05
        fingers = [thumb_up]

        # ── ЧЕТЫРЕ ПАЛЬЦА ──────────────────────────────────────────────────
        # (tip, dip, pip, mcp) — индексы суставов
        finger_joints = [
            (8,  7,  6,  5),   # указательный
            (12, 11, 10, 9),   # средний
            (16, 15, 14, 13),  # безымянный
            (20, 19, 18, 17),  # мизинец
        ]
        for tip_i, dip_i, pip_i, mcp_i in finger_joints:
            tip_lm  = landmarks[tip_i]
            dip_lm  = landmarks[dip_i]
            pip_lm  = landmarks[pip_i]
            mcp_lm  = landmarks[mcp_i]

            # Угол сгибания в PIP-суставе (MCP → PIP → DIP)
            pip_angle = GestureUtils._angle_between(mcp_lm, pip_lm, dip_lm)

            # Угол сгибания в DIP-суставе (PIP → DIP → TIP)
            dip_angle = GestureUtils._angle_between(pip_lm, dip_lm, tip_lm)

            # Проекция вектора (MCP→TIP) на нормаль ладони
            finger_vec = GestureUtils._vec3(mcp_lm, tip_lm)
            proj = GestureUtils._dot3(finger_vec, palm_n)

            # Выпрямлен: оба сустава почти прямые И кончик «снаружи» ладони
            is_extended = pip_angle > 155 and dip_angle > 150 and proj > 0.0

            # Дополнительная проверка: кончик выше MCP по Y (страховка при горизонтальном кадре)
            tip_above_mcp = (tip_lm.y < mcp_lm.y - 0.025)

            fingers.append(is_extended or (pip_angle > 165 and tip_above_mcp))

        return fingers

    @staticmethod
    def match_gesture(finger_states: list, pattern: list) -> bool:
        """
        Проверяет соответствие жеста шаблону.
        Для открытой ладони достаточно 4 из 5 пальцев.
        Для остальных шаблонов требуется точное совпадение всех 5 позиций,
        но большой палец при вытянутых пальцах не штрафуется
        (он часто неоднозначен при боковом положении руки).
        """
        if pattern == [True] * 5:
            return sum(finger_states) >= 4

        # Считаем несовпадения, игнорируя большой, если он False в шаблоне
        mismatches = 0
        for i, (fs, pat) in enumerate(zip(finger_states, pattern)):
            if fs != pat:
                # Большому пальцу даём +1 допуск, если шаблон его не требует
                if i == 0 and not pat:
                    continue
                mismatches += 1

        return mismatches == 0

    @staticmethod
    def smooth_value(current: float, target: float, factor: float = 0.3) -> float:
        """Экспоненциальное сглаживание."""
        return current + (target - current) * factor

    @staticmethod
    def get_finger_indices(names: list) -> list:
        return [FINGER_TIP_MAP[name] for name in names]

    @staticmethod
    def draw_hand_skeleton(frame, landmarks):
        """Рисует скелет руки на кадре."""
        h, w, _ = frame.shape
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
        for start, end in HAND_CONNECTIONS:
            cv2.line(frame, pts[start], pts[end], (0, 255, 0), 2)
        for pt in pts:
            cv2.circle(frame, pt, 3, (255, 0, 0), -1)

    @staticmethod
    def download_model() -> bool:
        """Скачивает модель, если отсутствует."""
        if os.path.exists(MODEL_PATH):
            return True
        os.makedirs(MODEL_DIR, exist_ok=True)
        print(f"  [МОДЕЛЬ] Загрузка модели...")
        try:
            import urllib.request
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print(f"  [МОДЕЛЬ] Модель загружена: {MODEL_PATH}")
            return True
        except Exception as e:
            print(f"  [МОДЕЛЬ] Ошибка загрузки: {e}")
            return False

    @staticmethod
    def is_circle_gesture(landmarks, threshold: float = 0.05) -> bool:
        """
        Проверяет жест 'круг' (OK-жест):
        - Кончики большого и указательного сомкнуты (dist < threshold).
        - Средний, безымянный и мизинец достаточно выпрямлены
          (угол в PIP > 140°), чтобы исключить кулак и другие жесты.
        """
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
        if dist >= threshold:
            return False

        # Проверяем, что остальные три пальца выпрямлены
        other_joints = [
            (landmarks[9],  landmarks[10], landmarks[11]),  # средний: MCP-PIP-DIP
            (landmarks[13], landmarks[14], landmarks[15]),  # безымянный
            (landmarks[17], landmarks[18], landmarks[19]),  # мизинец
        ]
        extended_count = 0
        for mcp_lm, pip_lm, dip_lm in other_joints:
            angle = GestureUtils._angle_between(mcp_lm, pip_lm, dip_lm)
            if angle > 140:
                extended_count += 1

        return extended_count >= 2  # хотя бы 2 из 3 пальцев выпрямлены


class GestureUI:
    """Отрисовка UI: текст, слайдеры, индикаторы режимов."""

    SLIDER_POS = {"x_offset": 60, "y_center": 0.5, "height": 200, "width": 30, "fill_color": (50, 50, 50)}
    PROGRESS_BAR = {"width": 300, "height": 20, "y": 120, "bg_color": (100, 100, 100),
                    "fg_color": (0, 255, 0), "border_color": (255, 255, 255)}

    @staticmethod
    def get_font(size: int):
        """Возвращает шрифт с поддержкой кириллицы."""
        if not PIL_AVAILABLE:
            return None
        for path in FONT_CANDIDATES:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def draw_slider(frame, landmarks, finger_indices, color, min_dist=30, max_dist=200) -> int:
        """Рисует слайдер между пальцами, возвращает значение 0-100."""
        h, w, _ = frame.shape
        p1 = (int(landmarks[finger_indices[0]].x * w), int(landmarks[finger_indices[0]].y * h))
        p2 = (int(landmarks[finger_indices[1]].x * w), int(landmarks[finger_indices[1]].y * h))

        dist_val = GestureUtils.distance(p1, p2)
        value = int(np.clip((dist_val - min_dist) / (max_dist - min_dist) * 100, 0, 100))

        cv2.line(frame, p1, p2, color, 3)
        cv2.circle(frame, p1, 8, color, -1)
        cv2.circle(frame, p2, 8, color, -1)

        cfg = GestureUI.SLIDER_POS
        sx = w - cfg["x_offset"]
        sy = int(h * cfg["y_center"])
        sh, sw = cfg["height"], cfg["width"]
        fill_h = int(value / 100 * sh)

        cv2.rectangle(frame, (sx, sy - sh // 2), (sx + sw, sy + sh // 2), cfg["fill_color"], -1)
        cv2.rectangle(frame, (sx + 3, sy + sh // 2 - fill_h), (sx + sw - 3, sy + sh // 2), color, -1)
        cv2.rectangle(frame, (sx, sy - sh // 2), (sx + sw, sy + sh // 2), (255, 255, 255), 2)

        return value

    @staticmethod
    def draw_gesture_info(frame, gesture, action, font):
        """Информация о распознанном жесте."""
        if not PIL_AVAILABLE or font is None:
            font_cv = cv2.FONT_HERSHEY_SIMPLEX
            h, w, _ = frame.shape
            cv2.putText(frame, f"Жест: {gesture}", (w // 2 - 100, h - 80), font_cv, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, action, (w // 2 - 120, h - 55), font_cv, 0.6, (0, 255, 255), 2)
            return frame

        text = f"Распознан жест: {gesture}\n{action}"
        return GestureUI._pil_text(frame, text, (frame.shape[1] // 2 - 100, frame.shape[0] - 90), font, (255, 255, 0))

    @staticmethod
    def draw_mode_ui(frame, mode, value, font):
        """UI активного режима."""
        mode_cfg = MODES[mode]
        lines = [
            (mode_cfg["name"], (255, 255, 255)),
            (UI_TEXTS["mode_active"], (0, 255, 0)),
            (mode_cfg["label"].format(value), (255, 255, 0)),
            ("2 пальца - выход", (0, 255, 255)),
        ]
        return GestureUI._overlay_text(frame, lines, font)

    @staticmethod
    def draw_confirm_ui(frame, mode_name, hold_progress, hold_gesture_name, font):
        """UI удержания жеста с прогрессом."""
        h, w, _ = frame.shape
        lines = [
            (f"Удерживайте жест: {hold_gesture_name}", (255, 255, 0)),
            (f"Режим: {mode_name}", (0, 255, 255)),
            (f"{int(hold_progress * 100)}%", (0, 255, 0)),
        ]
        frame = GestureUI._overlay_text(frame, lines, font)

        cfg = GestureUI.PROGRESS_BAR
        bar_x = (w - cfg["width"]) // 2
        cv2.rectangle(frame, (bar_x, cfg["y"]), (bar_x + cfg["width"], cfg["y"] + cfg["height"]), cfg["bg_color"], -1)
        fill_w = int(cfg["width"] * hold_progress)
        if fill_w > 0:
            cv2.rectangle(frame, (bar_x, cfg["y"]), (bar_x + fill_w, cfg["y"] + cfg["height"]), cfg["fg_color"], -1)
        cv2.rectangle(frame, (bar_x, cfg["y"]), (bar_x + cfg["width"], cfg["y"] + cfg["height"]), cfg["border_color"], 2)

        return frame

    @staticmethod
    def draw_action_mode_ui(frame, action_name, font):
        """UI фазы выбора объекта — действие выбрано."""
        h, w, _ = frame.shape
        lines = [
            (f"Действие: {action_name}", (255, 255, 0)),
            (UI_TEXTS.get("action_prompt", "Покажите объект"), (0, 255, 255)),
        ]
        return GestureUI._overlay_text(frame, lines, font)

    @staticmethod
    def draw_object_mode_ui(frame, object_name, hold_progress, font):
        """UI удержания жеста объекта."""
        h, w, _ = frame.shape
        lines = [
            (f"Объект: {object_name}", (255, 255, 0)),
            (f"{int(hold_progress * 100)}%", (0, 255, 0)),
        ]
        frame = GestureUI._overlay_text(frame, lines, font)

        cfg = GestureUI.PROGRESS_BAR
        bar_x = (w - cfg["width"]) // 2
        cv2.rectangle(frame, (bar_x, cfg["y"]), (bar_x + cfg["width"], cfg["y"] + cfg["height"]), cfg["bg_color"], -1)
        fill_w = int(cfg["width"] * hold_progress)
        if fill_w > 0:
            cv2.rectangle(frame, (bar_x, cfg["y"]), (bar_x + fill_w, cfg["y"] + cfg["height"]), cfg["fg_color"], -1)
        cv2.rectangle(frame, (bar_x, cfg["y"]), (bar_x + cfg["width"], cfg["y"] + cfg["height"]), cfg["border_color"], 2)

        return frame

    # --- Внутренние методы ---

    @staticmethod
    def _pil_text(frame, text, pos, font, color):
        """Рисует текст через PIL (кириллица)."""
        if not PIL_AVAILABLE or font is None:
            return frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        ImageDraw.Draw(image).text(pos, text, font=font, fill=color)
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _overlay_text(frame, lines_data, font, line_height=30):
        """Рисует строки текста с полупрозрачным фоном."""
        if not PIL_AVAILABLE or font is None:
            return frame

        h, w, _ = frame.shape
        overlay_h = len(lines_data) * line_height + 10

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        draw = ImageDraw.Draw(image)

        overlay = np.array(image)
        cv2.rectangle(overlay, (0, 0), (w, overlay_h), (0, 0, 0), -1)
        image = Image.fromarray(cv2.addWeighted(overlay, 0.5, np.array(image), 0.5, 0))
        draw = ImageDraw.Draw(image)

        for i, (text, color) in enumerate(lines_data):
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((w // 2 - tw // 2, 10 + i * line_height), text, font=font, fill=color)

        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


# ============================================================
# ОБРАБОТЧИК ЖЕСТОВ
# ============================================================
class GestureProcessor:
    """Инкапсулирует обработку жестов: детекция, распознавание, UI."""

    def __init__(self):
        self.state = GestureState()
        self.sound_controller = SoundController()
        self.thread = None  # Будет установлен из GestureCameraThread

        if self.sound_controller.initialized:
            self.state.sound_value = self.sound_controller.get_volume()
            self.state.smoothed_sound = self.state.sound_value

        # Индексы пальцев
        self.control_fingers = GestureUtils.get_finger_indices(MODES["brightness"]["control_fingers"])
        self.smoothing = SETTINGS.get("smoothing_factor", 0.3)

        # MediaPipe
        self.landmarker = self._init_landmarker()
        self.font_small = GestureUI.get_font(24)

        # Константы удержания
        self.hold_required_frames = 50  # ~0.7 сек при 30 FPS

        # Параметры буфера стабилизации
        self.STABILITY_BUFFER_SIZE = 5   # кадров для голосования
        self.STABILITY_THRESHOLD = 0.6   # доля кадров, при которой состояние считается стабильным

    def _stabilize_finger_states(self, raw_states: list) -> list:
        """
        Буфер стабилизации пальцев: голосование по последним N кадрам.
        Каждый палец считается поднятым только если он поднят в >=60% кадров.
        Это устраняет дёрганье при дрожании руки.
        """
        buf = self.state.finger_state_buffer
        buf.append(raw_states)
        if len(buf) > self.STABILITY_BUFFER_SIZE:
            buf.pop(0)

        n = len(buf)
        stable = []
        for i in range(5):
            votes = sum(1 for frame_states in buf if frame_states[i])
            stable.append(votes / n >= self.STABILITY_THRESHOLD)

        self.state.stable_finger_states = stable
        return stable

    def _stabilize_circle(self, raw_circle: bool) -> bool:
        """Буфер стабилизации для жеста круга."""
        buf = self.state.circle_buffer
        buf.append(raw_circle)
        if len(buf) > self.STABILITY_BUFFER_SIZE:
            buf.pop(0)
        n = len(buf)
        votes = sum(1 for v in buf if v)
        self.state.stable_circle = votes / n >= self.STABILITY_THRESHOLD
        return self.state.stable_circle

    def _is_fist_gesture(self, fs: list, landmarks: list = None) -> bool:
        """
        Кулак: все четыре пальца опущены.
        Если переданы landmarks — дополнительно проверяем, что углы в PIP
        каждого пальца < 100° (реально согнуты), что исключает
        горизонтально вытянутую ладонь, опускающуюся по Y, но не сжатую.
        """
        # Базовая проверка: большой не считаем, т.к. в кулаке он сбоку
        four_down = not fs[1] and not fs[2] and not fs[3] and not fs[4]
        if not four_down:
            return False

        if landmarks is None:
            return True

        # Уточнение: PIP-угол каждого пальца должен быть явно согнутым
        finger_joints = [
            (landmarks[5],  landmarks[6],  landmarks[7]),   # указательный MCP-PIP-DIP
            (landmarks[9],  landmarks[10], landmarks[11]),  # средний
            (landmarks[13], landmarks[14], landmarks[15]),  # безымянный
            (landmarks[17], landmarks[18], landmarks[19]),  # мизинец
        ]
        bent_count = sum(
            1 for mcp_lm, pip_lm, dip_lm in finger_joints
            if GestureUtils._angle_between(mcp_lm, pip_lm, dip_lm) < 120
        )
        return bent_count >= 3

    def _init_landmarker(self):  
        """Инициализирует HandLandmarker."""
        if not GestureUtils.download_model():
            print("Ошибка: не удалось загрузить модель!")
            return None

        try:
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=VisionRunningMode.IMAGE,
                num_hands=SETTINGS["max_hands"],
                min_hand_detection_confidence=SETTINGS["detection_confidence"],
                min_hand_presence_confidence=SETTINGS["tracking_confidence"],
                min_tracking_confidence=SETTINGS["tracking_confidence"],
            )
            return HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Ошибка инициализации HandLandmarker: {e}")
            return None

    def _detect_hands(self, frame) -> Dict[str, HandData]:
        """Детектирует руки и возвращает словарь {label: HandData}."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)

        hands = {}
        for idx, landmarks in enumerate(result.hand_landmarks):
            label = "Right"
            if idx < len(result.handedness) and result.handedness[idx]:
                label = result.handedness[idx][0].category_name

            GestureUtils.draw_hand_skeleton(frame, landmarks)
            raw_states = GestureUtils.get_finger_states(landmarks)
            # Стабилизируем состояние пальцев через буфер голосования
            stable_states = self._stabilize_finger_states(raw_states)
            hands[label] = HandData(landmarks, label, stable_states)

        return hands

    def _update_active_mode(self, frame, hands: Dict[str, HandData]):
        """Обновляет значение в активном режиме (яркость/звук)."""
        if self.state.current_mode not in ("brightness", "sound"):
            return frame

        is_brightness = self.state.current_mode == "brightness"
        mode_cfg = MODES[self.state.current_mode]
        left_hand = hands.get("Left")

        if not left_hand:
            return frame

        raw = GestureUI.draw_slider(frame, left_hand.landmarks, self.control_fingers,
                          mode_cfg["slider_color"], SETTINGS["min_distance"], SETTINGS["max_distance"])

        if is_brightness:
            self.state.smoothed_brightness = GestureUtils.smooth_value(self.state.smoothed_brightness, raw, self.smoothing)
            self.state.brightness_value = int(self.state.smoothed_brightness)

            if BRIGHTNESS_AVAILABLE:
                try:
                    sbc.set_brightness(self.state.brightness_value)
                except Exception as e:
                    print(f"  Ошибка яркости: {e}")
        else:
            self.state.smoothed_sound = GestureUtils.smooth_value(self.state.smoothed_sound, raw, self.smoothing)
            self.state.sound_value = int(self.state.smoothed_sound)
            print(f"  >>> Звук: {self.state.sound_value}% (raw: {raw})")
            self.sound_controller.set_volume(self.state.sound_value)

        return frame

    def _process_gesture_logic(self, hands: Dict[str, HandData]) -> Tuple[str, str]:
        """Логика распознавания жестов. Возвращает (gesture_name, action)."""
        detected_gesture, detected_action = "", ""

        for hand in hands.values():
            fs = hand.finger_states
            lm = hand.landmarks

            # =============================================
            # ФАЗА 2: Выбор объекта (после подтверждения действия)
            # =============================================
            if self.state.action_mode:
                # Проверяем жесты объектов — обычные жесты игнорируются
                for obj_key, obj_cfg in OBJECTS.items():
                    if GestureUtils.match_gesture(fs, obj_cfg["finger_pattern"]):
                        hold_frames = obj_cfg.get("hold_frames", 50)
                        self.state.object_hold_frames += 1
                        progress = min(1.0, self.state.object_hold_frames / hold_frames)

                        if self.state.object_hold_frames >= hold_frames:
                            # Объект выбран — выполняем команду
                            self.state.selected_object = obj_cfg["command_name"]
                            return self._execute_command()

                        detected_gesture = obj_cfg["name"]
                        detected_action = f"Удерживайте... {int(progress * 100)}%"
                        self.state.hold_progress = progress
                        break
                else:
                    # Жест не из объектов — сброс прогресса
                    if self.state.object_hold_frames > 0:
                        self.state.object_hold_frames = 0
                        self.state.hold_progress = 0.0

                # Ладонь — отмена выбора объекта, но остаёмся в action_mode
                if sum(fs) >= 4:
                    self.state.object_hold_frames = 0
                    self.state.hold_progress = 0.0
                    detected_gesture = "Ладонь"
                    detected_action = "Отмена (остаёмся в выборе объекта)"
                    print("  >>> Отмена выбора объекта, жду другой объект")
                    break

                # 2 пальца — выход из action_mode полностью
                if self._two_fingers_gesture(fs):
                    self._exit_action_mode("Выход из режима действий")
                    return "2 пальца", "Выход"

                continue  # Не проверяем обычные жесты в action_mode

            # =============================================
            # ФАЗА 1: Обычный режим — действия и режимы
            # =============================================
            if self.state.pending_mode is not None:
                # --- РЕЖИМ ПОДТВЕРЖДЕНИЯ (яркость/звук) ---
                target_key = "one_finger" if self.state.pending_mode == "brightness" else "three_fingers"
                target_cfg = GESTURES[target_key]

                # Ладонь — выход из подтверждения
                if sum(fs) >= 4:
                    self.state.hold_action = False
                    self.state.hold_action_progress = 0.0
                    self._exit_confirmation("Выход из подтверждения (ладонь)")
                    return "Ладонь", "Выход из подтверждения"

                # Удержание целевого жеста
                if GestureUtils.match_gesture(fs, target_cfg["finger_pattern"]):
                    self.state.hold_current_frames += 1
                    self.state.hold_progress = min(1.0, self.state.hold_current_frames / self.hold_required_frames)

                    if self.state.hold_current_frames >= self.hold_required_frames:
                        self.state.current_mode = self.state.pending_mode
                        print(f"  >>> Режим {'яркости' if self.state.current_mode == 'brightness' else 'звука'} АКТИВИРОВАН")
                        self.state.pending_mode = None
                        self.state.hold_current_frames = 0
                        self.state.hold_progress = 0.0
                        self.state.gesture_cooldown = SETTINGS["gesture_cooldown"]
                        return target_cfg["name"], "Активировано!"

                    return target_cfg["name"], f"Удерживайте... {int(self.state.hold_progress * 100)}%"
                else:
                    if self.state.hold_current_frames > 0:
                        self.state.hold_action = False
                        self.state.hold_action_progress = 0.0
                        print(f"  >>> Удержание прервано (было {self.state.hold_current_frames} кадров)")
                    self.state.hold_current_frames = 0
                    self.state.hold_progress = 0.0
            else:
                            # --- ОБЫЧНЫЙ РЕЖИМ ---
                if self.state.gesture_cooldown > 0:
                    continue

                # 1. Определяем тип жеста действия (Круг или Кулак)
                action_type = None
                hold_frames = 0
                gesture_display_name = ""

                if GestureUtils.is_circle_gesture(lm, ACTIONS.get("circle", {}).get("circle_threshold", 0.05)):
                    if self._stabilize_circle(True):
                        action_type = "circle"
                        hold_frames = ACTIONS.get("circle", {}).get("hold_frames", 50)
                        gesture_display_name = "Круг"
                    else:
                        self._stabilize_circle(False)
                else:
                    self._stabilize_circle(False)

                if action_type is None and self._is_fist_gesture(fs, lm):
                    action_type = "fist_close"
                    hold_frames = ACTIONS.get("fist_close", {}).get("hold_frames", 40)
                    gesture_display_name = "Кулак"

                # Обработка удержания действия
                if action_type:
                    self.state.hold_current_frames += 1
                    progress = min(1.0, self.state.hold_current_frames / hold_frames)
                    self.state.hold_action = True
                    self.state.hold_action_progress = progress
                    self.state.hold_gesture_name = gesture_display_name  # Запоминаем имя для UI

                    if self.state.hold_current_frames >= hold_frames:
                        action_cfg = ACTIONS.get(action_type, {})
                        self.state.selected_action = action_cfg.get("command_name", "действие")
                        self.state.action_mode = True
                        self.state.hold_current_frames = 0
                        self.state.hold_progress = 0.0
                        self.state.hold_action = False
                        self.state.hold_action_progress = 0.0
                        self.state.gesture_cooldown = SETTINGS["gesture_cooldown"]
                        print(f"   > > > Действие '{self.state.selected_action}' выбрано. Жду объект...")
                        return gesture_display_name, "Покажите объект"

                    detected_gesture = gesture_display_name
                    detected_action = f"Удерживайте... {int(progress * 100)}%"
                    break

                # Ладонь — отмена при удержании действия
                if sum(fs) >= 4 and self.state.hold_action:
                    self.state.hold_action = False
                    self.state.hold_action_progress = 0.0
                    self.state.hold_current_frames = 0
                    self.state.gesture_cooldown = SETTINGS["gesture_cooldown"]
                    return "Ладонь", "Отмена"

        return detected_gesture, detected_action

    def _two_fingers_gesture(self, fs: list) -> bool:
        """Проверяет жест '2 пальца' для выхода."""
        two_fingers_cfg = GESTURES.get("two_fingers", {})
        if two_fingers_cfg:
            return GestureUtils.match_gesture(fs, two_fingers_cfg["finger_pattern"])
        return False

    def _execute_command(self) -> Tuple[str, str]:
        """Собирает и выполняет команду."""
        cmd = f"{self.state.selected_action.capitalize()} {self.state.selected_object}"
        print(f"  >>> КОМАНДА: {cmd}")

        # Отправляем команду в UI через сигнал
        if self.thread is not None:
            print(f"  >>> Отправляю command_ready сигнал: '{cmd}'")
            self.thread.command_ready.emit(cmd)

        # Сброс после выполнения
        self.state.action_mode = False
        self.state.selected_action = ""
        self.state.selected_object = ""
        self.state.object_hold_frames = 0
        self.state.hold_progress = 0.0
        self.state.gesture_cooldown = SETTINGS["gesture_cooldown"]

        return cmd, "Выполнено!"

    def _exit_action_mode(self, reason: str):
        """Выход из режима действий."""
        self.state.action_mode = False
        self.state.selected_action = ""
        self.state.selected_object = ""
        self.state.object_hold_frames = 0
        self.state.hold_progress = 0.0
        self.state.hold_action = False
        self.state.hold_action_progress = 0.0
        self.state.gesture_cooldown = SETTINGS["gesture_cooldown"]
        print(f"  >>> {reason}")

    def _exit_confirmation(self, reason: str):
        """Сбрасывает состояние подтверждения."""
        self.state.pending_mode = None
        self.state.hold_gesture_name = ""
        self.state.hold_progress = 0.0
        self.state.hold_current_frames = 0
        self.state.gesture_cooldown = SETTINGS["gesture_cooldown"]
        print(f"  >>> {reason}")

    def process_frame(self, frame) -> Optional[np.ndarray]:
        """Обрабатывает кадр и возвращает кадр с UI."""
        if frame is None or self.landmarker is None:
            return frame

        frame = cv2.flip(frame, 1)
        hands = self._detect_hands(frame)

        # Распознавание жестов
        gesture, action = self._process_gesture_logic(hands)

        # Обновление активного режима
        frame = self._update_active_mode(frame, hands)

        # Обновление таймеров
        if gesture:
            self.state.current_gesture = gesture
            self.state.current_action = action
            self.state.gesture_timer = SETTINGS["gesture_display_time"]

        if self.state.gesture_cooldown > 0:
            self.state.gesture_cooldown -= 1
        if self.state.gesture_timer > 0:
            self.state.gesture_timer -= 1

        # Отрисовка UI
        if self.state.action_mode:
            # Фаза выбора объекта
            if self.state.object_hold_frames > 0:
                # Удерживаем жест объекта
                obj_name = OBJECTS.get("one_finger", {}).get("name", "объект")
                frame = GestureUI.draw_object_mode_ui(frame, obj_name, self.state.hold_progress, self.font_small)
            else:
                # Ждём объект
                frame = GestureUI.draw_action_mode_ui(frame, self.state.selected_action, self.font_small)
        elif self.state.hold_action:
            # Удержание жеста "круг" — прогресс-бар действия
            frame = GestureUI.draw_confirm_ui(frame, "Действие", self.state.hold_action_progress, self.state.hold_gesture_name, self.font_small)
        elif self.state.pending_mode is not None:
            mode_name = "Яркость" if self.state.pending_mode == "brightness" else "Звук"
            hold_gesture = "1 палец" if self.state.pending_mode == "brightness" else "3 пальца"
            frame = GestureUI.draw_confirm_ui(frame, mode_name, self.state.hold_progress, hold_gesture, self.font_small)
        elif self.state.current_mode is not None:
            frame = GestureUI.draw_mode_ui(frame, self.state.current_mode, self.state.current_value, self.font_small)

        if self.state.gesture_timer > 0 and self.state.current_gesture:
            frame = GestureUI.draw_gesture_info(frame, self.state.current_gesture, self.state.current_action, self.font_small)

        return frame

    def get_status_text(self) -> str:
        """Текст статуса для GUI."""
        parts = []

        if self.state.action_mode:
            parts.append(f"Действие: {self.state.selected_action}")
            if self.state.object_hold_frames > 0:
                parts.append(f"Прогресс: {int(self.state.hold_progress * 100)}%")
            else:
                parts.append(UI_TEXTS.get("action_prompt", "Покажите объект"))
            parts.append("Ладонь — отмена | 2 пальца — выход")
        elif self.state.pending_mode is not None:
            mode = "Яркость" if self.state.pending_mode == "brightness" else "Звук"
            gesture = "1 палец" if self.state.pending_mode == "brightness" else "3 пальца"
            parts.extend([f"Удерживайте: {gesture}", f"Режим: {mode}",
                          f"Прогресс: {int(self.state.hold_progress * 100)}%",
                          "Ладонь — выход из подтверждения"])
        elif self.state.current_mode is not None:
            mode_cfg = MODES[self.state.current_mode]
            value = self.state.current_value
            parts.extend([f"{mode_cfg['name']}: {value}%", "РЕЖИМ АКТИВЕН", "2 пальца — выход из режима"])

        if self.state.gesture_timer > 0 and self.state.current_gesture:
            parts.extend([f"Жест: {self.state.current_gesture}", self.state.current_action])

        if not parts:
            parts.extend(["Покажите жест для управления",
                          "1 палец — яркость | 3 пальца — звук",
                          "Круг (большой+указательный) — действие открыть"])

        return "\n".join(parts)

    def shutdown(self):
        if self.landmarker:
            self.landmarker.close()
            self.landmarker = None

    def reset(self):
        self.state.reset()


# ============================================================
# ПОТОК КАМЕРЫ
# ============================================================
class GestureCameraThread(QThread):
    """Фоновый поток камеры для PyQt."""
    frame_ready = pyqtSignal(QImage)
    status_ready = pyqtSignal(str)
    command_ready = pyqtSignal(str)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.processor = None
        self.cap = None
        self._running = False

    def run(self):
        self._running = True
        self.processor = GestureProcessor()
        self.processor.thread = self  # Обратная ссылка для сигналов

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.status_ready.emit("Ошибка: не удалось открыть камеру!")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, SETTINGS["camera_width"])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SETTINGS["camera_height"])

        self._print_instructions()

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            processed = self.processor.process_frame(frame)
            if processed is None or not self._running:
                break

            rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            q_image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(q_image)
            self.status_ready.emit(self.processor.get_status_text())
            self.msleep(33)

        self.cap.release()
        self.processor.shutdown()

    def stop(self):
        self._running = False
        self.wait()

    @staticmethod
    def _print_instructions():
        print("=" * 50)
        print("  Жестовое управление запущено!")
        print("  1 палец — яркость | 3 пальца — звук")
        print("  Удерживайте жест 3 секунды для активации")
        print("  Ладонь — выход из подтверждения")
        print("  2 пальца — выход из режима")
        print("=" * 50)


# ============================================================
# STANDALONE ЗАПУСК
# ============================================================
def main():
    """Простая обёртка над GestureProcessor для запуска без PyQt."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, SETTINGS["camera_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SETTINGS["camera_height"])

    processor = GestureProcessor()
    if processor.landmarker is None:
        return

    GestureCameraThread._print_instructions()
    print("  Нажмите 'q' для выхода.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        processed = processor.process_frame(frame)
        if processed is None:
            break

        cv2.imshow(UI_TEXTS["title"], processed)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    processor.shutdown()
    cv2.destroyAllWindows()
    print(f"\n  Финальное значение яркости: {processor.state.brightness_value}%")
    print(f"  Финальное значение звука: {processor.state.sound_value}%")


if __name__ == "__main__":
    main()