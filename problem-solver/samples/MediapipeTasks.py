from pathlib import Path

import cv2
import mediapipe as mp

MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")


def draw_landmarks(frame, hand_landmarks_list):
    height, width, _ = frame.shape

    for hand_landmarks in hand_landmarks_list:
        for i, landmark in enumerate(hand_landmarks):
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)
        pos_0 = hand_landmarks[0]
        finger_1 = hand_landmarks[0:5]   # Большой: 0,1,2,3,4
        finger_2 = [hand_landmarks[0]] + hand_landmarks[5:9]   # Указательный: 0, 5,6,7,8
        finger_3 = [hand_landmarks[0]] + hand_landmarks[9:13]  # Средний: 0, 9,10,11,12
        finger_4 = [hand_landmarks[0]] + hand_landmarks[13:17] # Безымянный: 0, 13,14,15,16
        finger_5 = [hand_landmarks[0]] + hand_landmarks[17:21]
        hand = [finger_1, finger_2, finger_3, finger_4, finger_5]
        color = [(233, 150, 122), (127, 255, 0), (32, 178, 170), (240, 230, 140), (186, 85, 211)]
        for j, finger in enumerate(hand):
            for i in range(len(finger) - 1):
                x1 = int(finger[i].x * width)
                y1 = int(finger[i].y * height)
                x2 = int(finger[i+1].x * width)
                y2 = int(finger[i+1].y * height)
                cv2.line(frame, (x1, y1), (x2, y2), color[j], 2)
                


        


def main():
    if not MODEL_PATH.exists():
        print("Model not found")
        return
    BaseOptions = mp.tasks.BaseOptions
    vision = mp.tasks.vision
    HandLandmarker = vision.HandLandmarker
    HandLandmarkerOptions = vision.HandLandmarkerOptions
    RunningMode = vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
    )

    hand_landmarker = HandLandmarker.create_from_options(options)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        hand_landmarker.close()
        return

    print("Camera open: OK")
    print("Press ESC to exit")

    timestamp_ms = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Camera frame read: FAILED")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.hand_landmarks:
            draw_landmarks(frame, result.hand_landmarks)
            cv2.putText(
                frame,
                f"Hands detected: {len(result.hand_landmarks)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
        else:
            cv2.putText(
                frame,
                "Hands detected: 0",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

        cv2.imshow("MediaPipe HandLandmarker Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            break

        timestamp_ms += 33

    cap.release()
    cv2.destroyAllWindows()
    hand_landmarker.close()
    print("HandLandmarker close: OK")


if __name__ == "__main__":
    main()
