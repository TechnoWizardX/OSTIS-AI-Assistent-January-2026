# -*- coding: utf-8 -*-
import cv2
import mediapipe as mp
import math
import numpy as np
import sys
import json
import os

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except ImportError:
    BRIGHTNESS_AVAILABLE = False

try:
    import pycaw.pycaw as pycaw
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================
current_mode = None  # None, "brightness", "sound"
pending_mode = None  # Режим, ожидающий подтверждения
brightness_value = 50
sound_value = 50
smoothed_brightness = 50  # Для плавности
smoothed_sound = 50  # Для плавности

# ============================================================
# ИНИЦИАЛИЗАЦИЯ MEDIAPIPE
# ============================================================
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

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
        self.device = None
        self.interface = None
        self.initialized = False
        
        if not SOUND_AVAILABLE:
            return
        
        try:
            devices = AudioUtilities.GetSpeakers()
            if devices is None:
                return
            self.device = devices
            self.interface = self.device.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.interface = cast(self.interface, POINTER(IAudioEndpointVolume))
            self.initialized = True
        except Exception as e:
            print(f"Ошибка инициализации звука: {e}")
            self.initialized = False
    
    def set_volume(self, value):
        """Устанавливает громкость (0-100)."""
        if not self.initialized:
            return
        
        try:
            volume = value / 100.0
            self.interface.SetMasterVolumeLevelScalar(volume, None)
        except Exception as e:
            print(f"Ошибка установки звука: {e}")
    
    def get_volume(self):
        """Получает текущую громкость (0-100)."""
        if not self.initialized:
            return 50
        
        try:
            volume = self.interface.GetMasterVolumeLevelScalar()
            return int(volume * 100)
        except Exception:
            return 50

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def distance(p1, p2):
    """Евклидово расстояние между двумя точками."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_finger_states(hand_landmarks, handedness_label):
    """
    Определяет, какие пальцы подняты.
    Возвращает список [thumb, index, middle, ring, pinky] — True/False.
    """
    lm = hand_landmarks.landmark
    fingers = []

    # Большой палец — проверяем, отведён ли от ладони
    # Сравниваем расстояние от кончика большого до указательного
    thumb_index_dist = math.sqrt(
        (lm[4].x - lm[8].x) ** 2 + 
        (lm[4].y - lm[8].y) ** 2
    )
    # Если большой палец далеко от указательного - он поднят
    fingers.append(thumb_index_dist > 0.15)

    # Остальные 4 пальца — кончик выше PIP-сустава по Y
    # Используем более надёжную проверку с порогом
    for tip, pip_ in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        # Палец поднят, если кончик значительно выше сустава
        is_extended = lm[tip].y < lm[pip_].y - 0.02
        fingers.append(is_extended)

    return fingers  # [thumb, index, middle, ring, pinky]


def match_gesture(finger_states, pattern):
    """Проверяет, соответствует ли жест шаблону."""
    if len(finger_states) != len(pattern):
        return False
    # Считаем количество совпадений
    matches = sum(1 for fs, pat in zip(finger_states, pattern) if fs == pat)
    # Требуется хотя бы 4 из 5 совпадений (80%)
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
    
    # Координаты кончиков пальцев
    p1 = (int(lm[finger_indices[0]].x * w), int(lm[finger_indices[0]].y * h))
    p2 = (int(lm[finger_indices[1]].x * w), int(lm[finger_indices[1]].y * h))
    
    # Расстояние между пальцами
    dist = distance(p1, p2)
    
    # Нормализуем расстояние
    value = np.clip((dist - min_dist) / (max_dist - min_dist) * 100, 0, 100)
    
    # Рисуем линию между пальцами
    thickness = 3
    cv2.line(frame, p1, p2, color, thickness)
    cv2.circle(frame, p1, 8, color, -1)
    cv2.circle(frame, p2, 8, color, -1)
    
    # Рисуем индикатор уровня справа
    slider_x = w - 60
    slider_y = h // 2
    slider_height = 200
    slider_width = 30
    
    # Фон слайдера
    cv2.rectangle(frame, 
                  (slider_x, slider_y - slider_height // 2), 
                  (slider_x + slider_width, slider_y + slider_height // 2), 
                  (50, 50, 50), -1)
    
    # Заполненная часть слайдера
    fill_height = int(value / 100 * slider_height)
    cv2.rectangle(frame,
                  (slider_x + 3, slider_y + slider_height // 2 - fill_height),
                  (slider_x + slider_width - 3, slider_y + slider_height // 2),
                  color, -1)
    
    # Граница слайдера
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
        # Фолбэк на OpenCV
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
    
    # Полупрозрачный фон
    overlay = np.array(image)
    cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
    image = Image.fromarray(cv2.addWeighted(overlay, 0.5, np.array(image), 0.5, 0))
    draw = ImageDraw.Draw(image)
    
    # Заголовок
    draw.text((w // 2 - 80, 10), mode_config["name"], font=font_title, fill=(255, 255, 255))
    
    # Статус
    draw.text((w // 2 - 60, 45), UI_TEXTS["mode_active"], font=font_small, fill=(0, 255, 0))
    
    # Значение
    value_text = mode_config["label"].format(value)
    draw.text((w // 2 - 60, 75), value_text, font=font_small, fill=(255, 255, 0))
    
    # Подсказка про выход
    draw.text((10, h - 35), "2 пальца - выход", font=font_small, fill=(0, 255, 255))
    
    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr


def draw_confirm_ui(frame, pending_mode_name, font_small=None):
    """Рисует UI для подтверждения активации режима."""
    h, w, _ = frame.shape
    
    if not PIL_AVAILABLE:
        # Фолбэк на OpenCV
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
    
    # Полупрозрачный фон
    overlay = np.array(image)
    cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
    image = Image.fromarray(cv2.addWeighted(overlay, 0.5, np.array(image), 0.5, 0))
    draw = ImageDraw.Draw(image)
    
    # Вопрос
    question = f"Активировать: {pending_mode_name}?"
    bbox = draw.textbbox((0, 0), question, font=font_medium)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 25), question, font=font_medium, fill=(255, 255, 0))
    
    # Подсказка
    hint = "Лайк - подтвердить | Дизлайк - отмена"
    bbox = draw.textbbox((0, 0), hint, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((w // 2 - tw // 2, 70), hint, font=font_small, fill=(0, 255, 255))
    
    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
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
    confirm_timer = 0  # Таймер ожидания подтверждения
    
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
    
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=settings["max_hands"],
        min_detection_confidence=settings["detection_confidence"],
        min_tracking_confidence=settings["tracking_confidence"],
    ) as hands:
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
            
            # Зеркалим кадр
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            # Конвертируем BGR → RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            hands_data = {}
            
            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness_info in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness,
                ):
                    label = handedness_info.classification[0].label
                    
                    # Рисуем скелет руки
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )
                    
                    finger_states = get_finger_states(hand_landmarks, label)
                    
                    # Отладка: выводим состояние пальцев
                    print_finger_states(finger_states)

                    hands_data[label] = {
                        "landmarks": hand_landmarks.landmark,
                        "label": label,
                        "finger_states": finger_states,
                    }
            
            # ====================================================
            # ЛОГИКА УПРАВЛЕНИЯ
            # ====================================================
            detected_gesture = ""
            detected_action = ""

            # Проверяем жесты для каждой руки
            for hand_key, hand_info in hands_data.items():
                fs = hand_info["finger_states"]
                lm = hand_info["landmarks"]

                # Сопоставляем с известными жестами
                for gesture_name, gesture_config in gestures.items():
                    if match_gesture(fs, gesture_config["finger_pattern"]):
                        action = gesture_config["action"]

                        # Обработка жестов активации режимов (требуется подтверждение)
                        if action == "activate_brightness" and gesture_cooldown <= 0:
                            if current_mode is None and pending_mode is None:
                                pending_mode = "brightness"
                                confirm_timer = 180  # 3 секунды на подтверждение
                                print("  >>> Ожидание подтверждения для яркости...")
                                detected_gesture = gesture_config["name"]
                                detected_action = "Покажите лайк для подтверждения или дизлайк для отказа"

                        elif action == "activate_sound" and gesture_cooldown <= 0:
                            if current_mode is None and pending_mode is None:
                                pending_mode = "sound"
                                confirm_timer = 180  # 3 секунды на подтверждение
                                print("  >>> Ожидание подтверждения для звука...")
                                detected_gesture = gesture_config["name"]
                                detected_action = "Покажите лайк для подтверждения или дизлайк для отказа"

                        # Подтверждение (лайк)
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

                        # Отмена (дизлайк)
                        elif action == "deactivate" and gesture_cooldown <= 0:
                            if pending_mode is not None:
                                # Отмена ожидания подтверждения
                                pending_mode = None
                                confirm_timer = 0
                                print("  >>> Отмена активации")
                                gesture_cooldown = settings["gesture_cooldown"]
                                detected_gesture = gesture_config["name"]
                                detected_action = "Отменено"
                            elif current_mode is not None:
                                # Выход из активного режима
                                current_mode = None
                                print("  >>> Режим ДЕЗАКТИВИРОВАН")
                                gesture_cooldown = settings["gesture_cooldown"]
                                detected_gesture = gesture_config["name"]
                                detected_action = gesture_config["hint"]

                        # Выход из режима (2 пальца)
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
            
            # Таймер ожидания подтверждения
            if confirm_timer > 0:
                confirm_timer -= 1
                if confirm_timer <= 0 and pending_mode is not None:
                    # Время вышло - отменяем
                    pending_mode = None
                    print("  >>> Время подтверждения вышло")
            
            # Обновляем значение в активном режиме
            current_value = brightness_value if current_mode == "brightness" else sound_value
            
            if current_mode == "brightness" and "Right" in hands_data:
                lm = hands_data["Right"]["landmarks"]
                raw_value = draw_slider(
                    frame, lm, brightness_fingers,
                    MODES["brightness"]["slider_color"],
                    settings["min_distance"], settings["max_distance"]
                )
                # Плавное изменение
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
                # Плавное изменение
                smoothed_sound = smooth_value(smoothed_sound, raw_value, smoothing_factor)
                sound_value = int(smoothed_sound)
                current_value = sound_value
                
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
                # Режим ожидания подтверждения
                mode_name = "Яркость" if pending_mode == "brightness" else "Звук"
                frame = draw_confirm_ui(frame, mode_name, font_small)
            elif current_mode is not None:
                # Активный режим
                frame = draw_mode_ui(frame, current_mode, current_value, font_small)
            
            # Рисуем информацию о жесте
            if gesture_timer > 0 and current_gesture and current_action:
                frame = draw_gesture_info(frame, current_gesture, current_action, font_small)
            
            cv2.imshow(CONFIG["ui_texts"]["title"], frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"\n  Финальное значение яркости: {brightness_value}%")
        print(f"  Финальное значение звука: {sound_value}%")
        print("  Программа завершена.")


if __name__ == "__main__":
    main()
