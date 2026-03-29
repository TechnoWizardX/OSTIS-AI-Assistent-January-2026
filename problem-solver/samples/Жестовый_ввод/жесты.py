import cv2
import mediapipe as mp
import math
import numpy as np
import os
import sys
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
print(sys.executable)
# ============================================================
# НАСТРОЙКИ РАСПОЗНАВАНИЯ И ХРАНЕНИЯ РЕЗУЛЬТАТА
# ============================================================
# Выбор языка вывода распознанной буквы: "en" или "ru"
GESTURE_LANGUAGE = "ru"
recognized_letter = ""
# ============================================================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

SUPPORTED_LANGUAGES = {"en", "ru"}
RU_LETTER_MAP = {
    "A": "А",
    "B": "Б",
    "C": "С",
    "D": "Д",
    "F": "Ф",
    "I": "И",
    "K": "К",
    "L": "Л",
    "O": "О",
    "R": "Р",
    "S": "С",
    "U": "У",
    "V": "В",
    "W": "Ш",
    "Y": "Ы",
}

UI_TEXTS = {
    "en": {
        "title": "ASL Letter",
        "hint": "Press 'q' to quit | 'c' to clear",
        "window": "Hand Gesture Recognition (ASL)",
    },
    "ru": {
        "title": "Буква ASL",
        "hint": "Нажмите 'q' для выхода | 'c' очистить",
        "window": "Hand Gesture Recognition (ASL)",
    },
}

FONT_CANDIDATES = [
    "arial.ttf",
    "segoeui.ttf",
    "tahoma.ttf",
    os.path.join("C:\\", "Windows", "Fonts", "arial.ttf"),
    os.path.join("C:\\", "Windows", "Fonts", "segoeui.ttf"),
    os.path.join("C:\\", "Windows", "Fonts", "tahoma.ttf"),
]

LETTER_BOX = (10, 10, 200, 120)  # x1, y1, x2, y2


def distance(landmarks, p1, p2):
    """Евклидово расстояние между двумя точками руки."""
    return math.sqrt(
        (landmarks[p1].x - landmarks[p2].x) ** 2
        + (landmarks[p1].y - landmarks[p2].y) ** 2
        + (landmarks[p1].z - landmarks[p2].z) ** 2
    )


def get_finger_states(hand_landmarks, handedness_label):
    """
    Определяет, какие пальцы подняты.
    Возвращает список [thumb, index, middle, ring, pinky] — True/False.
    """
    lm = hand_landmarks.landmark
    fingers = []

    # Большой палец — сравниваем по оси X (зависит от руки)
    if handedness_label == "Right":
        fingers.append(lm[4].x < lm[3].x)
    else:
        fingers.append(lm[4].x > lm[3].x)

    # Остальные 4 пальца — кончик выше PIP-сустава по Y
    for tip, pip_ in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        fingers.append(lm[tip].y < lm[pip_].y)

    return fingers  # [thumb, index, middle, ring, pinky]


def classify_gesture(hand_landmarks, handedness_label):
    """
    Классифицирует жест руки в букву ASL-алфавита.
    Распознаёт: A, B, C, D, F, I, K, L, O, R, U, V, W, Y
    а также «5» (открытая ладонь) и «S» (кулак).
    """
    lm = hand_landmarks.landmark
    fingers = get_finger_states(hand_landmarks, handedness_label)
    thumb, index, middle, ring, pinky = fingers

    # Расстояния между кончиками пальцев и большим пальцем
    d_thumb_index  = distance(lm, 4, 8)
    d_thumb_middle = distance(lm, 4, 12)
    d_thumb_ring   = distance(lm, 4, 16)
    d_thumb_pinky  = distance(lm, 4, 20)
    d_index_middle = distance(lm, 8, 12)

    # Расстояние от кончика пальца до запястья (для определения сгиба)
    d_index_wrist  = distance(lm, 8, 0)
    d_middle_wrist = distance(lm, 12, 0)

    # ------ ОТКРЫТАЯ ЛАДОНЬ (5) ------
    if thumb and index and middle and ring and pinky:
        return "5"

    # ------ Y: большой + мизинец ------
    if thumb and not index and not middle and not ring and pinky:
        return "Y"

    # ------ I: только мизинец ------
    if not thumb and not index and not middle and not ring and pinky:
        return "I"

    # ------ L: большой + указательный (форма «L») ------
    if thumb and index and not middle and not ring and not pinky:
        if d_index_middle > 0.05:
            return "L"

    # ------ F: большой и указательный касаются, остальные подняты ------
    if d_thumb_index < 0.045 and middle and ring and pinky:
        return "F"

    # ------ O: все кончики тянутся к большому пальцу ------
    if (d_thumb_index < 0.055
            and d_thumb_middle < 0.055
            and not ring and not pinky):
        return "O"

    # ------ C: все пальцы полусогнуты (форма «C») ------
    if (not index and not middle and not ring and not pinky
            and thumb
            and d_thumb_index > 0.06
            and d_thumb_index < 0.14):
        return "C"

    # ------ D: указательный вверх, остальные касаются большого ------
    if index and not middle and not ring and not pinky:
        if d_thumb_middle < 0.06:
            return "D"
        return "D"

    # ------ R: указательный и средний скрещены ------
    if (index and middle and not ring and not pinky):
        if d_index_middle < 0.03:
            return "R"
        # ------ U: указательный и средний вместе ------
        if d_index_middle < 0.06:
            return "U"
        # ------ V / K: указательный и средний врозь ------
        if d_index_middle >= 0.06:
            if thumb:
                return "K"
            return "V"

    # ------ W: указательный + средний + безымянный ------
    if not thumb and index and middle and ring and not pinky:
        return "W"

    # ------ B: 4 пальца вверх, большой согнут ------
    if not thumb and index and middle and ring and pinky:
        return "B"

    # ------ A: кулак, большой палец сбоку ------
    if thumb and not index and not middle and not ring and not pinky:
        return "A"

    # ------ S: полный кулак ------
    if not thumb and not index and not middle and not ring and not pinky:
        return "S"

    return "?"


def localize_letter(letter, language):
    """
    Преобразует распознанную букву под выбранный язык.
    Для "en" возвращается исходная буква, для "ru" — соответствие из словаря.
    """
    if language == "en":
        return letter
    if language == "ru":
        return RU_LETTER_MAP.get(letter, letter)
    return letter


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


def draw_ui_text(frame, display, language, w, h, font_big=None, font_small=None):
    """
    Рисует UI-текст через Pillow, чтобы корректно отображать кириллицу.
    """
    texts = UI_TEXTS.get(language, UI_TEXTS["en"])
    x1, y1, x2, y2 = LETTER_BOX
    box_w = x2 - x1
    box_h = y2 - y1

    if not PIL_AVAILABLE:
        cv2.putText(frame, texts["title"], (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        # Фолбэк OpenCV: центрируем букву внутри выделенного квадрата
        font_scale = 2.6
        thickness = 5
        (tw, th), baseline = cv2.getTextSize(display, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        while (tw > box_w - 20 or th > box_h - 35) and font_scale > 0.8:
            font_scale -= 0.2
            (tw, th), baseline = cv2.getTextSize(display, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        tx = x1 + (box_w - tw) // 2
        ty = y1 + (box_h + th) // 2 - baseline
        cv2.putText(frame, display, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)
        cv2.putText(frame, texts["hint"], (w // 2 - 260, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1, cv2.LINE_AA)
        return frame, texts["window"]

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(image)

    if font_big is None:
        font_big = get_font(96)
    if font_small is None:
        font_small = get_font(24)

    draw.text((x1 + 8, y1 + 8), texts["title"], font=font_small, fill=(200, 200, 200))

    # Центрируем букву внутри выделенного квадрата с подстройкой размера
    letter_size = 96
    dyn_font = get_font(letter_size)
    bbox = draw.textbbox((0, 0), display, font=dyn_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    while (tw > box_w - 20 or th > box_h - 40) and letter_size > 36:
        letter_size -= 8
        dyn_font = get_font(letter_size)
        bbox = draw.textbbox((0, 0), display, font=dyn_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

    tx = x1 + (box_w - tw) // 2 - bbox[0]
    ty = y1 + (box_h - th) // 2 - bbox[1] + 10
    draw.text((tx, ty), display, font=dyn_font, fill=(0, 255, 0))
    draw.text((w // 2 - 260, h - 35), texts["hint"], font=font_small, fill=(180, 180, 180))

    frame_bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    return frame_bgr, texts["window"]


def main():
    global recognized_letter, GESTURE_LANGUAGE

    GESTURE_LANGUAGE = GESTURE_LANGUAGE.lower()
    if GESTURE_LANGUAGE not in SUPPORTED_LANGUAGES:
        print(
            f"Предупреждение: язык '{GESTURE_LANGUAGE}' не поддерживается. "
            "Используется 'en'."
        )
        GESTURE_LANGUAGE = "en"
    if not PIL_AVAILABLE and GESTURE_LANGUAGE == "ru":
        print("Предупреждение: Pillow не установлен. Для отображения кириллицы установите: pip install pillow")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Ошибка: не удалось открыть камеру!")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    prev_letter = ""

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    ) as hands:
        font_big = get_font(96)
        font_small = get_font(24)

        print("=" * 50)
        print("  Распознавание жестов ASL запущено!")
        print(f"  Язык отображения: {'Русский' if GESTURE_LANGUAGE == 'ru' else 'English'}")
        print("  Покажите жест перед камерой.")
        print("  Нажмите 'q' для выхода.")
        print("=" * 50)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Зеркалим кадр для удобства
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Конвертируем BGR → RGB для MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            current_letter = ""

            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks, handedness_info in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness,
                ):
                    # Определяем левая/правая рука
                    label = handedness_info.classification[0].label

                    # Рисуем скелет руки
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

                    # Классифицируем жест
                    current_letter = classify_gesture(hand_landmarks, label)

            # ====================================================
            # Сохраняем распознанную букву в переменную
            # ====================================================
            if current_letter and current_letter != "?":
                recognized_letter = localize_letter(current_letter, GESTURE_LANGUAGE)

                # Выводим в консоль только при смене буквы
                if recognized_letter != prev_letter:
                    print(f"  >>> Распознана буква: {recognized_letter}")
                    prev_letter = recognized_letter
            # ====================================================

            # ---------- ОТРИСОВКА НА ЭКРАНЕ ----------

            # Полупрозрачный фон для текста (левый верхний угол)
            overlay = frame.copy()
            cv2.rectangle(overlay, (LETTER_BOX[0], LETTER_BOX[1]), (LETTER_BOX[2], LETTER_BOX[3]), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
            cv2.rectangle(frame, (LETTER_BOX[0], LETTER_BOX[1]), (LETTER_BOX[2], LETTER_BOX[3]), (90, 90, 90), 1)

            # Показываем текущую букву крупно
            display = recognized_letter if recognized_letter else "-"
            frame, window_title = draw_ui_text(
                frame,
                display,
                GESTURE_LANGUAGE,
                w,
                h,
                font_big=font_big,
                font_small=font_small,
            )
            cv2.imshow(window_title, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("c"):
                recognized_letter = ""
                prev_letter = ""
                print("  [Очищено]")

    cap.release()
    cv2.destroyAllWindows()

    print(f"\n  Последняя распознанная буква: '{recognized_letter}'")
    print("  Программа завершена.")


if __name__ == "__main__":
    main()