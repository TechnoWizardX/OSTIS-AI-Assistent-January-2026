import cv2
import mediapipe as mp
import math
import sys
print(sys.executable)
# ============================================================
# ПЕРЕМЕННАЯ ДЛЯ ХРАНЕНИЯ РАСПОЗНАННОЙ БУКВЫ
# ============================================================
recognized_letter = ""
# ============================================================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


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


def main():
    global recognized_letter

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

        print("=" * 50)
        print("  Распознавание жестов ASL запущено!")
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
                recognized_letter = current_letter

                # Выводим в консоль только при смене буквы
                if recognized_letter != prev_letter:
                    print(f"  >>> Распознана буква: {recognized_letter}")
                    prev_letter = recognized_letter
            # ====================================================

            # ---------- ОТРИСОВКА НА ЭКРАНЕ ----------

            # Полупрозрачный фон для текста (левый верхний угол)
            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (200, 120), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

            # Показываем текущую букву крупно
            display = recognized_letter if recognized_letter else "-"
            cv2.putText(
                frame,
                display,
                (40, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                3.0,
                (0, 255, 0),
                5,
                cv2.LINE_AA,
            )

            # Подпись
            cv2.putText(
                frame,
                "ASL Letter",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )

            # Подсказка внизу
            cv2.putText(
                frame,
                "Press 'q' to quit | 'c' to clear",
                (w // 2 - 200, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (180, 180, 180),
                1,
                cv2.LINE_AA,
            )

            cv2.imshow("Hand Gesture Recognition (ASL)", frame)

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