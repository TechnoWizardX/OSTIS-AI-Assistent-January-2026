# -*- coding: utf-8 -*-
"""
Жестовое управление — архитектура на основе Tasks.
MediaPipe Tasks API (без solutions).
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
                "hint": "Режим яркости активирован"
            },
            "three_fingers": {
                "name": "3 пальца",
                "finger_pattern": [False, True, True, True, False],
                "action": "activate_sound",
                "hint": "Режим звука активирован"
            },
            "like": {
                "name": "Лайк",
                "finger_pattern": [True, False, False, False, False],
                "action": "confirm",
                "hint": "Подтверждено"
            },
            "dislike": {
                "name": "Дизлайк",
                "finger_pattern": [False, False, False, False, False],
                "action": "deactivate",
                "hint": "Режим деактивирован"
            },
            "two_fingers": {
                "name": "2 пальца",
                "finger_pattern": [False, True, True, False, False],
                "action": "exit",
                "hint": "Выход из режима"
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
# MEDIAPIPE TASKS (только Tasks API, без solutions)
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
# Модель хранится в папке без кириллицы (Windows не открывает файлы с кириллицей)
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

def download_model():
    """Скачивает модель hand_landmarker.task, если её нет."""
    if os.path.exists(MODEL_PATH):
        print(f"  [МОДЕЛЬ] Найдена: {MODEL_PATH}")
        return True

    # Создаём папку models, если нет
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
# КОНТЕКСТ ЗАДАЧ (передаётся между задачами)
# ============================================================
@dataclass
class TaskContext:
    """Контейнер состояния, передаваемый между задачами."""
    frame: Optional[np.ndarray] = None
    hands_data: Dict[str, Dict] = field(default_factory=dict)

    current_mode: Optional[str] = None
    pending_mode: Optional[str] = None
    brightness_value: int = 50
    sound_value: int = 50
    smoothed_brightness: float = 50.0
    smoothed_sound: float = 50.0

    gesture_cooldown: int = 0
    gesture_timer: int = 0
    confirm_timer: int = 0
    current_gesture: str = ""
    current_action: str = ""

    status_text: str = ""

# ============================================================
# БАЗОВЫЙ КЛАСС ЗАДАЧИ
# ============================================================
class BaseTask:
    """Базовый класс для всех задач."""
    def __init__(self, name: str):
        self.name = name
        self.enabled: bool = True

    def execute(self, ctx: TaskContext) -> None:
        pass

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

    # Большой палец — расстояние от кончика большого (4) до IP сустава указательного (5)
    thumb_tip = landmarks[4]
    index_ip = landmarks[5]
    thumb_index_dist = math.sqrt(
        (thumb_tip.x - index_ip.x) ** 2 + (thumb_tip.y - index_ip.y) ** 2
    )
    fingers.append(thumb_index_dist > 0.15)

    # Остальные 4 пальца — кончик выше PIP
    for tip, pip_ in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        is_extended = landmarks[tip].y < landmarks[pip_].y - 0.02
        fingers.append(is_extended)

    return fingers


def match_gesture(finger_states, pattern):
    """Проверяет, соответствует ли жест шаблону."""
    if len(finger_states) != len(pattern):
        return False
    matches = sum(1 for fs, pat in zip(finger_states, pattern) if fs == pat)
    return matches >= 4


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


def draw_confirm_ui(frame, pending_mode_name, font_small=None):
    """Рисует UI для подтверждения активации режима."""
    h, w, _ = frame.shape

    if not PIL_AVAILABLE:
        cv2.rectangle(frame, (0, 0), (w, 120), (0, 0, 0), -1)
        text1 = f"Активировать: {pending_mode_name}?"
        text2 = "Лайк - подтвердить | Дизлайк - отмена"
        cv2.putText(frame, text1, (w // 2 - 150, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, text2, (w // 2 - 200, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)
        return frame

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(image)

    if font_small is None:
        font_small = get_font(24)

    font_medium = get_font(28)

    overlay = np.array(image)
    cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
    image = Image.fromarray(cv2.addWeighted(overlay, 0.5, np.array(image), 0.5, 0))
    draw = ImageDraw.Draw(image)

    question = f"Активировать: {pending_mode_name}?"
    bbox = draw.textbbox((0, 0), question, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 25), question, font=font_medium, fill=(255, 255, 0))

    hint = "Лайк - подтвердить | Дизлайк - отмена"
    bbox = draw.textbbox((0, 0), hint, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 70), hint, font=font_small, fill=(0, 255, 255))

    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr


# ============================================================
# ЗАДАЧИ (Tasks)
# ============================================================

# --- TASK 1: Обнаружение рук (MediaPipe Tasks API) ---
class HandDetectionTask(BaseTask):
    """Обнаруживает руки через MediaPipe HandLandmarker Task."""
    def __init__(self):
        super().__init__("HandDetection")
        self.landmarker = None

    def init(self, settings: dict):
        """Инициализирует HandLandmarker через Tasks API."""
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=VisionRunningMode.IMAGE,
            num_hands=settings["max_hands"],
            min_hand_detection_confidence=settings["detection_confidence"],
            min_hand_presence_confidence=settings["tracking_confidence"],
            min_tracking_confidence=settings["tracking_confidence"],
        )
        self.landmarker = HandLandmarker.create_from_options(options)

    def execute(self, ctx: TaskContext) -> None:
        if self.landmarker is None or ctx.frame is None:
            return

        frame = ctx.frame
        h, w, _ = frame.shape

        # Конвертируем BGR → RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Детектируем
        detection_result = self.landmarker.detect(mp_image)

        ctx.hands_data = {}

        if detection_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                # Определяем левую/правую руку
                handedness_list = detection_result.handedness
                if idx < len(handedness_list) and len(handedness_list[idx]) > 0:
                    category = handedness_list[idx][0]
                    # MediaPipe Tasks возвращает "Left"/"Right"
                    label = "Right" if category.category_name == "Right" else "Left"
                else:
                    label = "Right"

                # Рисуем скелет руки
                _draw_landmarks(frame, hand_landmarks, HAND_CONNECTIONS)

                # Определяем состояние пальцев
                finger_states = get_finger_states(hand_landmarks)

                ctx.hands_data[label] = {
                    "landmarks": hand_landmarks,
                    "label": label,
                    "finger_states": finger_states,
                }

    def shutdown(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None


# --- TASK 2: Распознавание жестов ---
class GestureRecognitionTask(BaseTask):
    """Распознаёт жесты по состоянию пальцев."""
    def __init__(self, gestures: dict, settings: dict):
        super().__init__("GestureRecognition")
        self.gestures = gestures
        self.settings = settings

    def execute(self, ctx: TaskContext) -> None:
        if ctx.gesture_cooldown > 0:
            return

        detected_gesture = ""
        detected_action = ""

        for hand_key, hand_info in ctx.hands_data.items():
            fs = hand_info["finger_states"]

            for gesture_name, gesture_config in self.gestures.items():
                if match_gesture(fs, gesture_config["finger_pattern"]):
                    action = gesture_config["action"]

                    if action == "activate_brightness":
                        if ctx.current_mode is None and ctx.pending_mode is None:
                            ctx.pending_mode = "brightness"
                            ctx.confirm_timer = 180
                            print("  >>> Ожидание подтверждения для яркости...")
                            detected_gesture = gesture_config["name"]
                            detected_action = "Покажите лайк для подтверждения или дизлайк для отказа"

                    elif action == "activate_sound":
                        if ctx.current_mode is None and ctx.pending_mode is None:
                            ctx.pending_mode = "sound"
                            ctx.confirm_timer = 180
                            print("  >>> Ожидание подтверждения для звука...")
                            detected_gesture = gesture_config["name"]
                            detected_action = "Покажите лайк для подтверждения или дизлайк для отказа"

                    elif action == "confirm" and ctx.pending_mode is not None:
                        if ctx.pending_mode == "brightness":
                            ctx.current_mode = "brightness"
                            print("  >>> Режим яркости АКТИВИРОВАН")
                        elif ctx.pending_mode == "sound":
                            ctx.current_mode = "sound"
                            print("  >>> Режим звука АКТИВИРОВАН")
                        ctx.pending_mode = None
                        ctx.confirm_timer = 0
                        ctx.gesture_cooldown = self.settings["gesture_cooldown"]
                        detected_gesture = gesture_config["name"]
                        detected_action = gesture_config["hint"]

                    elif action == "deactivate":
                        if ctx.pending_mode is not None:
                            ctx.pending_mode = None
                            ctx.confirm_timer = 0
                            print("  >>> Отмена активации")
                            ctx.gesture_cooldown = self.settings["gesture_cooldown"]
                            detected_gesture = gesture_config["name"]
                            detected_action = "Отменено"
                        elif ctx.current_mode is not None:
                            ctx.current_mode = None
                            print("  >>> Режим ДЕЗАКТИВИРОВАН")
                            ctx.gesture_cooldown = self.settings["gesture_cooldown"]
                            detected_gesture = gesture_config["name"]
                            detected_action = gesture_config["hint"]

                    elif action == "exit" and ctx.current_mode is not None:
                        ctx.current_mode = None
                        ctx.pending_mode = None
                        ctx.confirm_timer = 0
                        print("  >>> Выход из режима")
                        ctx.gesture_cooldown = self.settings["gesture_cooldown"]
                        detected_gesture = gesture_config["name"]
                        detected_action = gesture_config["hint"]

                    break

        if detected_gesture:
            ctx.current_gesture = detected_gesture
            ctx.current_action = detected_action
            ctx.gesture_timer = self.settings["gesture_display_time"]


# --- TASK 3: Таймеры ---
class TimerTask(BaseTask):
    """Управляет таймерами."""
    def __init__(self, settings: dict):
        super().__init__("Timers")
        self.settings = settings

    def execute(self, ctx: TaskContext) -> None:
        if ctx.confirm_timer > 0:
            ctx.confirm_timer -= 1
            if ctx.confirm_timer <= 0 and ctx.pending_mode is not None:
                ctx.pending_mode = None
                print("  >>> Время подтверждения вышло")

        if ctx.gesture_cooldown > 0:
            ctx.gesture_cooldown -= 1

        if ctx.gesture_timer > 0:
            ctx.gesture_timer -= 1


# --- TASK 4: Управление яркостью ---
class BrightnessControlTask(BaseTask):
    """Управляет яркостью экрана."""
    def __init__(self, modes: dict, settings: dict):
        super().__init__("BrightnessControl")
        self.modes = modes
        self.settings = settings
        self.brightness_fingers = get_finger_indices(modes["brightness"]["control_fingers"])
        self.smoothing_factor = settings.get("smoothing_factor", 0.3)

    def execute(self, ctx: TaskContext) -> None:
        if ctx.current_mode != "brightness":
            return
        if "Right" not in ctx.hands_data:
            return

        lm = ctx.hands_data["Right"]["landmarks"]
        raw_value = draw_slider(
            ctx.frame, lm, self.brightness_fingers,
            self.modes["brightness"]["slider_color"],
            self.settings["min_distance"], self.settings["max_distance"]
        )
        ctx.smoothed_brightness = smooth_value(ctx.smoothed_brightness, raw_value, self.smoothing_factor)
        ctx.brightness_value = int(ctx.smoothed_brightness)

        if BRIGHTNESS_AVAILABLE:
            try:
                sbc.set_brightness(ctx.brightness_value)
            except Exception as e:
                print(f"  Ошибка яркости: {e}")


# --- TASK 5: Управление звуком ---
class SoundControlTask(BaseTask):
    """Управляет громкостью системы."""
    def __init__(self, modes: dict, settings: dict):
        super().__init__("SoundControl")
        self.modes = modes
        self.settings = settings
        self.sound_fingers = get_finger_indices(modes["sound"]["control_fingers"])
        self.smoothing_factor = settings.get("smoothing_factor", 0.3)
        self.sound_controller = SoundController()

    def execute(self, ctx: TaskContext) -> None:
        if ctx.current_mode != "sound":
            return
        if "Right" not in ctx.hands_data:
            return

        lm = ctx.hands_data["Right"]["landmarks"]
        raw_value = draw_slider(
            ctx.frame, lm, self.sound_fingers,
            self.modes["sound"]["slider_color"],
            self.settings["min_distance"], self.settings["max_distance"]
        )
        ctx.smoothed_sound = smooth_value(ctx.smoothed_sound, raw_value, self.smoothing_factor)
        ctx.sound_value = int(ctx.smoothed_sound)

        print(f"  >>> Звук: {ctx.sound_value}% (raw: {raw_value})")
        self.sound_controller.set_volume(ctx.sound_value)


# --- TASK 6: Отрисовка UI ---
class UIDrawingTask(BaseTask):
    """Отрисовывает интерфейс поверх кадра."""
    def __init__(self, modes: dict, ui_texts: dict):
        super().__init__("UIDrawing")
        self.modes = modes
        self.ui_texts = ui_texts
        self.font_small = get_font(24)

    def execute(self, ctx: TaskContext) -> None:
        frame = ctx.frame
        if frame is None:
            return

        if ctx.pending_mode is not None:
            mode_name = "Яркость" if ctx.pending_mode == "brightness" else "Звук"
            draw_confirm_ui(frame, mode_name, self.font_small)
        elif ctx.current_mode is not None:
            current_value = ctx.brightness_value if ctx.current_mode == "brightness" else ctx.sound_value
            draw_mode_ui(frame, ctx.current_mode, current_value, self.font_small)

        if ctx.gesture_timer > 0 and ctx.current_gesture and ctx.current_action:
            draw_gesture_info(frame, ctx.current_gesture, ctx.current_action, self.font_small)

    def get_status_text(self, ctx: TaskContext) -> str:
        """Возвращает строку статуса для отображения в GUI."""
        parts = []

        if ctx.pending_mode is not None:
            mode_name = "Яркость" if ctx.pending_mode == "brightness" else "Звук"
            parts.append(f"Ожидание подтверждения: {mode_name}")
            parts.append("Лайк — подтвердить | Дизлайк — отмена")
        elif ctx.current_mode is not None:
            mode_config = self.modes[ctx.current_mode]
            value = ctx.brightness_value if ctx.current_mode == "brightness" else ctx.sound_value
            parts.append(f"{mode_config['name']}: {value}%")
            parts.append("РЕЖИМ АКТИВЕН")
            parts.append("2 пальца — выход")

        if ctx.gesture_timer > 0 and ctx.current_gesture and ctx.current_action:
            parts.append(f"Жест: {ctx.current_gesture}")
            parts.append(ctx.current_action)

        if not parts:
            parts.append("Покажите жест для управления")
            parts.append("1 палец — яркость | 3 пальца — звук")
            parts.append("Лайк — подтвердить | Дизлайк — отмена")

        return "\n".join(parts)


# ============================================================
# TASK PIPELINE
# ============================================================
class TaskPipeline:
    """Выполняет все задачи последовательно."""
    def __init__(self):
        self.tasks: List[BaseTask] = []

    def add_task(self, task: BaseTask) -> None:
        self.tasks.append(task)

    def execute(self, ctx: TaskContext) -> TaskContext:
        for task in self.tasks:
            if task.enabled:
                task.execute(ctx)
        return ctx

    def shutdown_all(self) -> None:
        for task in self.tasks:
            if hasattr(task, "shutdown"):
                task.shutdown()


# ============================================================
# КЛАСС: ОБРАБОТЧИК ЖЕСТОВ (делегирование Tasks)
# ============================================================
class GestureProcessor:
    """
    Инкапсулирует всю логику обработки жестов.
    Делегирует работу TaskPipeline.
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

        # Контроллер звука
        self.sound_controller = SoundController()
        if self.sound_controller.initialized:
            self.sound_value = self.sound_controller.get_volume()
            self.smoothed_sound = self.sound_value

        # Индексы пальцев
        self.brightness_fingers = get_finger_indices(self.modes["brightness"]["control_fingers"])
        self.sound_fingers = get_finger_indices(self.modes["sound"]["control_fingers"])
        self.smoothing_factor = self.settings.get("smoothing_factor", 0.3)

        # MediaPipe HandLandmarker (Tasks API)
        self.hand_landmarker = None
        
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
            self.hand_landmarker = HandLandmarker.create_from_options(options)
        except Exception as e:
            print(f"Ошибка инициализации HandLandmarker: {e}")

        self.font_small = get_font(24)

        # === TASK PIPELINE ===
        self.pipeline = TaskPipeline()

        # Task 1: Обнаружение рук
        hand_task = HandDetectionTask()
        # Передаём уже созданный landmarker
        hand_task.landmarker = self.hand_landmarker
        self.pipeline.add_task(hand_task)

        # Task 2: Распознавание жестов
        self.pipeline.add_task(GestureRecognitionTask(self.gestures, self.settings))

        # Task 3: Таймеры
        self.pipeline.add_task(TimerTask(self.settings))

        # Task 4: Яркость
        self.pipeline.add_task(BrightnessControlTask(self.modes, self.settings))

        # Task 5: Звук
        sound_task = SoundControlTask(self.modes, self.settings)
        sound_task.sound_controller = self.sound_controller
        self.pipeline.add_task(sound_task)

        # Task 6: Отрисовка UI
        self.pipeline.add_task(UIDrawingTask(self.modes, self.ui_texts))

    def process_frame(self, frame):
        """
        Принимает кадр (BGR numpy array), возвращает кадр с отрисованным UI.
        """
        if frame is None:
            return frame

        frame = cv2.flip(frame, 1)

        ctx = TaskContext()
        ctx.frame = frame
        ctx.current_mode = self.current_mode
        ctx.pending_mode = self.pending_mode
        ctx.brightness_value = self.brightness_value
        ctx.sound_value = self.sound_value
        ctx.smoothed_brightness = self.smoothed_brightness
        ctx.smoothed_sound = self.smoothed_sound
        ctx.gesture_cooldown = self.gesture_cooldown
        ctx.gesture_timer = self.gesture_timer
        ctx.confirm_timer = self.confirm_timer
        ctx.current_gesture = self.current_gesture
        ctx.current_action = self.current_action

        self.pipeline.execute(ctx)

        self.current_mode = ctx.current_mode
        self.pending_mode = ctx.pending_mode
        self.brightness_value = ctx.brightness_value
        self.sound_value = ctx.sound_value
        self.smoothed_brightness = ctx.smoothed_brightness
        self.smoothed_sound = ctx.smoothed_sound
        self.gesture_cooldown = ctx.gesture_cooldown
        self.gesture_timer = ctx.gesture_timer
        self.confirm_timer = ctx.confirm_timer
        self.current_gesture = ctx.current_gesture
        self.current_action = ctx.current_action

        return frame

    def get_status_text(self):
        """Возвращает строку статуса для отображения в GUI."""
        ctx = TaskContext()
        ctx.current_mode = self.current_mode
        ctx.pending_mode = self.pending_mode
        ctx.brightness_value = self.brightness_value
        ctx.sound_value = self.sound_value
        ctx.gesture_timer = self.gesture_timer
        ctx.current_gesture = self.current_gesture
        ctx.current_action = self.current_action

        for task in self.pipeline.tasks:
            if isinstance(task, UIDrawingTask):
                return task.get_status_text(ctx)

        parts = []
        if self.pending_mode is not None:
            mode_name = "Яркость" if self.pending_mode == "brightness" else "Звук"
            parts.append(f"Ожидание подтверждения: {mode_name}")
            parts.append("Лайк — подтвердить | Дизлайк — отмена")
        elif self.current_mode is not None:
            mode_config = self.modes[self.current_mode]
            value = self.brightness_value if self.current_mode == "brightness" else self.sound_value
            parts.append(f"{mode_config['name']}: {value}%")
            parts.append("РЕЖИМ АКТИВЕН")
            parts.append("2 пальца — выход")

        if self.gesture_timer > 0 and self.current_gesture and self.current_action:
            parts.append(f"Жест: {self.current_gesture}")
            parts.append(self.current_action)

        if not parts:
            parts.append("Покажите жест для управления")
            parts.append("1 палец — яркость | 3 пальца — звук")
            parts.append("Лайк — подтвердить | Дизлайк — отмена")

        return "\n".join(parts)

    def shutdown(self):
        """Освобождает ресурсы."""
        if self.hand_landmarker is not None:
            self.hand_landmarker.close()
        self.pipeline.shutdown_all()

    def reset(self):
        """Сбрасывает состояние."""
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


# ============================================================
# КЛАСС: ПОТОК КАМЕРЫ
# ============================================================
class GestureCameraThread(QThread):
    """
    Фоновый поток для работы с камерой.
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
        print("  Лайк (большой вверх) - подтвердить активацию")
        print("  Дизлайк (кулак) - отмена / деактивация")
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

            if not self._running:
                break

            processed_frame = self.processor.process_frame(frame)

            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            if self._running:
                self.frame_ready.emit(q_image)

            status = self.processor.get_status_text()
            if self._running:
                self.status_ready.emit(status)

            self.msleep(33)

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

    config = CONFIG
    gestures = GESTURES
    settings = SETTINGS

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings["camera_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings["camera_height"])

    gesture_cooldown = 0
    current_gesture = ""
    current_action = ""
    gesture_timer = 0
    confirm_timer = 0

    sound_controller = SoundController()
    if sound_controller.initialized:
        sound_value = sound_controller.get_volume()
        smoothed_sound = sound_value

    smoothed_brightness = brightness_value

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
    print("  Лайк (большой вверх) - подтвердить активацию")
    print("  Дизлайк (кулак) - отмена / деактивация")
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

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Конвертируем BGR → RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Детектируем руки
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

                # Рисуем скелет
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

        for hand_key, hand_info in hands_data.items():
            fs = hand_info["finger_states"]
            lm = hand_info["landmarks"]

            for gesture_name, gesture_config in gestures.items():
                if match_gesture(fs, gesture_config["finger_pattern"]):
                    action = gesture_config["action"]

                    if action == "activate_brightness" and gesture_cooldown <= 0:
                        if current_mode is None and pending_mode is None:
                            pending_mode = "brightness"
                            confirm_timer = 180
                            print("  >>> Ожидание подтверждения для яркости...")
                            detected_gesture = gesture_config["name"]
                            detected_action = "Покажите лайк для подтверждения или дизлайк для отказа"

                    elif action == "activate_sound" and gesture_cooldown <= 0:
                        if current_mode is None and pending_mode is None:
                            pending_mode = "sound"
                            confirm_timer = 180
                            print("  >>> Ожидание подтверждения для звука...")
                            detected_gesture = gesture_config["name"]
                            detected_action = "Покажите лайк для подтверждения или дизлайк для отказа"

                    elif action == "confirm" and pending_mode is not None and gesture_cooldown <= 0:
                        if pending_mode == "brightness":
                            current_mode = "brightness"
                            print("  >>> Режим яркости АКТИВИРОВАН")
                        elif pending_mode == "sound":
                            current_mode = "sound"
                            print("  >>> Режим звука АКТИВИРОВАН")
                        pending_mode = None
                        confirm_timer = 0
                        gesture_cooldown = settings["gesture_cooldown"]
                        detected_gesture = gesture_config["name"]
                        detected_action = gesture_config["hint"]

                    elif action == "deactivate" and gesture_cooldown <= 0:
                        if pending_mode is not None:
                            pending_mode = None
                            confirm_timer = 0
                            print("  >>> Отмена активации")
                            gesture_cooldown = settings["gesture_cooldown"]
                            detected_gesture = gesture_config["name"]
                            detected_action = "Отменено"
                        elif current_mode is not None:
                            current_mode = None
                            print("  >>> Режим ДЕЗАКТИВИРОВАН")
                            gesture_cooldown = settings["gesture_cooldown"]
                            detected_gesture = gesture_config["name"]
                            detected_action = gesture_config["hint"]

                    elif action == "exit" and gesture_cooldown <= 0:
                        if current_mode is not None:
                            current_mode = None
                            pending_mode = None
                            confirm_timer = 0
                            print("  >>> Выход из режима")
                            gesture_cooldown = settings["gesture_cooldown"]
                            detected_gesture = gesture_config["name"]
                            detected_action = gesture_config["hint"]

                    break

        if confirm_timer > 0:
            confirm_timer -= 1
            if confirm_timer <= 0 and pending_mode is not None:
                pending_mode = None
                print("  >>> Время подтверждения вышло")

        current_value = brightness_value if current_mode == "brightness" else sound_value

        if current_mode == "brightness" and "Right" in hands_data:
            lm = hands_data["Right"]["landmarks"]
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

        elif current_mode == "sound" and "Right" in hands_data:
            lm = hands_data["Right"]["landmarks"]
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

        if detected_gesture:
            current_gesture = detected_gesture
            current_action = detected_action
            gesture_timer = settings["gesture_display_time"]

        if gesture_cooldown > 0:
            gesture_cooldown -= 1

        if gesture_timer > 0:
            gesture_timer -= 1

        if pending_mode is not None:
            mode_name = "Яркость" if pending_mode == "brightness" else "Звук"
            frame = draw_confirm_ui(frame, mode_name, font_small)
        elif current_mode is not None:
            frame = draw_mode_ui(frame, current_mode, current_value, font_small)

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
