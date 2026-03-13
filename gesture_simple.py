import cv2
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from reachy_mini import ReachyMini

model_path = "pose_landmarker_lite.task"

options = vision.PoseLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=model_path),
    running_mode=vision.RunningMode.VIDEO
)
landmarker = vision.PoseLandmarker.create_from_options(options)
cap = cv2.VideoCapture(0)

print("Connecting to Reachy Mini...")
reachy = ReachyMini(spawn_daemon=True)
print("Connected!")

timestamp = 0

left_hand_is_up     = False
right_hand_is_up    = False
left_hand_up_start  = None
right_hand_up_start = None

fall_detected    = False
fall_start_time  = None
alert_triggered  = False
person_lost_count = 0

ANTENNA_UP   = 1.0
ANTENNA_DOWN = 0.0
FALL_THRESHOLD = 0.7 

print("Running — raise hands to move antennas. ESC to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect_for_video(mp_image, timestamp)
    timestamp += 1

    now = time.time()
    h, w, _ = frame.shape

    if result.pose_landmarks:
        landmarks = result.pose_landmarks[0]
        person_lost_count = 0

        nose           = landmarks[0]
        left_shoulder  = landmarks[11]
        right_shoulder = landmarks[12]
        left_wrist     = landmarks[15]
        right_wrist    = landmarks[16]

        # Draw dots
        cv2.circle(frame, (int(nose.x * w),           int(nose.y * h)),           8, (0, 255, 0),   -1)
        cv2.circle(frame, (int(left_wrist.x * w),     int(left_wrist.y * h)),     8, (255, 0, 0),   -1)
        cv2.circle(frame, (int(right_wrist.x * w),    int(right_wrist.y * h)),    8, (255, 0, 0),   -1)
        cv2.circle(frame, (int(left_shoulder.x * w),  int(left_shoulder.y * h)),  8, (0, 255, 255), -1)
        cv2.circle(frame, (int(right_shoulder.x * w), int(right_shoulder.y * h)), 8, (0, 255, 255), -1)

        nose_low = nose.y          > FALL_THRESHOLD
        ls_low   = left_shoulder.y  > FALL_THRESHOLD
        rs_low   = right_shoulder.y > FALL_THRESHOLD
        low_count = sum([nose_low, ls_low, rs_low])
        fall_condition = nose_low and ls_low and rs_low

        if fall_condition:
            if fall_start_time is None:
                fall_start_time = now
                print(f"⚠ Fall position detected ({low_count}/3 points low), monitoring...")
            elif now - fall_start_time > 1.5 and not alert_triggered:
                print("FALL DETECTED — EMERGENCY!")
                for _ in range(3):
                    reachy.goto_target(antennas=[ANTENNA_UP, ANTENNA_UP],     body_yaw=None, duration=0.2)
                    reachy.goto_target(antennas=[ANTENNA_DOWN, ANTENNA_DOWN], body_yaw=None, duration=0.2)
                alert_triggered = True
            fall_detected = True
        else:
            fall_start_time = None
            if alert_triggered:
                print("Person recovered — resuming normal operation")
                reachy.goto_target(antennas=[ANTENNA_DOWN, ANTENNA_DOWN], body_yaw=None, duration=0.5)
            fall_detected    = False
            alert_triggered  = False

        if fall_detected:
            cv2.putText(frame, "FALL DETECTED!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.rectangle(frame, (40, 10), (w-40, 90), (0, 0, 255), 3)
    
        if not fall_detected:

            left_up  = right_wrist.y < nose.y
            right_up = left_wrist.y  < nose.y

            if left_up:
                if left_hand_up_start is None:
                    left_hand_up_start = now
                elif now - left_hand_up_start > 0.5 and not left_hand_is_up:
                    print("LEFT HAND UP")
                    left_hand_is_up = True
            else:
                left_hand_up_start = None
                if left_hand_is_up:
                    print("LEFT HAND DOWN")
                    left_hand_is_up = False

            if right_up:
                if right_hand_up_start is None:
                    right_hand_up_start = now
                elif now - right_hand_up_start > 0.5 and not right_hand_is_up:
                    print("RIGHT HAND UP")
                    right_hand_is_up = True
            else:
                right_hand_up_start = None
                if right_hand_is_up:
                    print("RIGHT HAND DOWN")
                    right_hand_is_up = False

            left_antenna  = ANTENNA_UP if left_hand_is_up  else ANTENNA_DOWN
            right_antenna = ANTENNA_UP if right_hand_is_up else ANTENNA_DOWN

            reachy.goto_target(
                antennas=[right_antenna, left_antenna], 
                body_yaw=None,
                duration=0.3
            )

            status = " + ".join(filter(None, [
                "LEFT UP"  if left_hand_is_up  else "",
                "RIGHT UP" if right_hand_is_up else ""
            ])) or "HANDS DOWN"
            cv2.putText(frame, status, (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        cv2.putText(frame, f"Fall detection: {low_count}/3 low", (10, h-15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)

    else:
        person_lost_count += 1

        if person_lost_count > 30:
            if fall_start_time is None:
                fall_start_time = now
                print("Person lost from frame, monitoring...")
            elif now - fall_start_time > 2.0 and not alert_triggered:
                print("PERSON LOST — possible fall!")
                for _ in range(3):
                    reachy.goto_target(antennas=[ANTENNA_UP, ANTENNA_UP],     body_yaw=None, duration=0.2)
                    reachy.goto_target(antennas=[ANTENNA_DOWN, ANTENNA_DOWN], body_yaw=None, duration=0.2)
                alert_triggered = True
            cv2.putText(frame, "PERSON LOST - FALL?", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            cv2.rectangle(frame, (40, 10), (w-40, 90), (0, 0, 255), 3)
        else:
            cv2.putText(frame, "Searching for person...", (50, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    cv2.imshow("Reachy Mini — Antenna + Fall Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
reachy.disconnect()
print("Done.")