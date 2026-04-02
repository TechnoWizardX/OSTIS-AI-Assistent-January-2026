from pathlib import Path
import cv2
import mediapipe as mp

MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")


def draw_landmarks(frame, hand_landmarks_list : list):
    height, width, _ = frame.shape

    for hand_landmarks in hand_landmarks_list:
        for landmark in hand_landmarks:
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
        finger_1 = hand_landmarks[0:5]   # Большой: 0,1,2,3,4
        finger_2 = hand_landmarks[5:9]   # Указательный: 5,6,7,8
        finger_3 = hand_landmarks[9:13]  # Средний: 9,10,11,12
        finger_4 = hand_landmarks[13:17] # Безымянный: 13,14,15,16
        finger_5 = hand_landmarks[17:21]   # Мизинец: 17, 18, 19, 20
        full_hand = [finger_1, finger_2, finger_3, finger_4, finger_5]
        color = [(181, 228, 255), (133, 21, 199), (0, 215, 255), (50, 205, 154), (180, 130, 70)]
        for j, finger in enumerate(full_hand):
            for landmark in finger:
                x = int(landmark.x * width)
                y = int(landmark.y * height)
                cv2.circle(frame, (x, y), 3, color[j], -1)
        for j, finger in enumerate(full_hand):
            for i in range(len(finger) - 1):
                x1 = int(finger[i].x * width)
                y1 = int(finger[i].y * height)
                x2 = int(finger[i+1].x * width)
                y2 = int(finger[i+1].y * height)
                cv2.line(frame, (x1, y1), (x2, y2), color[j], 1, cv2.LINE_AA)
        hand = [hand_landmarks[0], hand_landmarks[5], hand_landmarks[9], hand_landmarks[13], hand_landmarks[17], hand_landmarks[0]]
        for i in range(len(hand) - 1):
            x1 = int(hand[i].x * width)
            y1 = int(hand[i].y * height)
            x2 = int(hand[i+1].x * width)
            y2 = int(hand[i+1].y * height)
            cv2.line(frame, (x1, y1), (x2, y2), (105, 105, 105), 1, cv2.LINE_AA)
    states = check_hand_state(hand_landmarks_list)
    check_gesture(states)
    

                
def check_hand_state(hand_landmarks_list : list) -> list:
    for hand_landmarks in hand_landmarks_list:
        finger_1 = hand_landmarks[0:5]   # Большой: 0,1,2,3,4
        finger_2 = hand_landmarks[5:9]   # Указательный: 5,6,7,8
        finger_3 = hand_landmarks[9:13]  # Средний: 9,10,11,12
        finger_4 = hand_landmarks[13:17] # Безымянный: 13,14,15,16
        finger_5 = hand_landmarks[17:21]   # Мизинец: 17, 18, 19, 20
        # state = 2: палец разогнут, 1: полусогнут, 0: согнут
        state1 = check_thumb_state(finger_1)
        state2 = check_finger_state(finger_2)
        state3 = check_finger_state(finger_3)
        state4 = check_finger_state(finger_4)
        state5 = check_finger_state(finger_5)
        return [state1, state2, state3, state4, state5]
        
def check_finger_state(finger_landmarks: list) -> int:
    state = 2
    if (finger_landmarks[3].y <= finger_landmarks[2].y and
        finger_landmarks[2].y <= finger_landmarks[1].y and
        finger_landmarks[1].y <= finger_landmarks[0].y):
        state = 2

    elif (finger_landmarks[3].y >= finger_landmarks[2].y and
        finger_landmarks[3].y <= finger_landmarks[0].y):
        state = 1
    else:
        state = 0
    return state

def check_thumb_state(thumb_landmarks: list) -> int:
    state = 2
    if ((thumb_landmarks[4].x >= thumb_landmarks[3].x and
        thumb_landmarks[3].x >= thumb_landmarks[2].x and
        thumb_landmarks[2].x >= thumb_landmarks[1].x) or 
        (thumb_landmarks[4].x <= thumb_landmarks[3].x and
        thumb_landmarks[2].x <= thumb_landmarks[2].x and
        thumb_landmarks[1].x <= thumb_landmarks[1].x)):
        state = 2

    elif ((thumb_landmarks[4].x <= thumb_landmarks[3].x and
        thumb_landmarks[4].x >= thumb_landmarks[1].x) or 
        (thumb_landmarks[4].x >= thumb_landmarks[3].x and
        thumb_landmarks[4].x <= thumb_landmarks[1].x)):
        state = 1
    else:
        state = 0
    return state

def check_gesture(states: list) -> str:
    if(states[0] == 2 and states[1] == 0 and states[2] == 0 and states[3] == 0 and states[4] == 0):
        print("close app")
    if(states[0] == 2 and states[1] == 1 and states[2] == 2 and states[3] == 2 and states[4] == 2):
        print("open browser")
    if(states[0] == 0 and states[1] == 1 and states[2] == 2 and states[3] == 0 and states[4] == 0):
        print("up volume")
    if(states[0] == 0 and states[1] == 2 and states[2] == 1 and states[3] == 0 and states[4] == 0):
        print("down volume")
    if(states[0] == 2 and states[1] == 1 and states[2] == 2 and states[3] == 0 and states[4] == 0):
        print("up brightness")
    if(states[0] == 2 and states[1] == 2 and states[2] == 1 and states[3] == 0 and states[4] == 0):
        print("down brightness")
    if(states[0] == 2 and states[1] == 1 and states[2] == 1 and states[3] == 2 and states[4] == 2):
        print("open settings")
    

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
        num_hands=4,
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
