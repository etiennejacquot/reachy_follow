import cv2
import time
import datetime
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import pyttsx3
import threading

tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150) 

USE_REAL_REACHY = True

MODE = 1  

class MockReachyMini:
    """Simulates ReachyMini for development without real robot"""

    def __init__(self):
        print("🤖 [MOCK] Connecting to Reachy Mini...")
        print("🤖 [MOCK] Connection successful (simulated)")

    def goto_target(self, head=None, antennas=None, body_yaw=None, duration=1.0):
        print(f"⚙ [MOCK] goto_target: head={head}, antennas={antennas}, body_yaw={body_yaw}, duration={duration}s")

    def set_target(self, head=None, antennas=None, body_yaw=None):
        print(f"⚙ [MOCK] set_target: head={head}, antennas={antennas}, body_yaw={body_yaw}")

    def disconnect(self):
        print("🤖 [MOCK] Disconnecting from Reachy Mini...")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()

if USE_REAL_REACHY:
    from reachy_mini import ReachyMini
    print("Using REAL Reachy Mini")
else:
    ReachyMini = MockReachyMini
    print("Using MOCK Reachy Mini (simulation mode)")

if MODE == 1:
    print("\n" + "="*60)
    print("MODE 1: Gitamini LEADS — Reachy faces user BEHIND it")
    print("  Camera points backward toward user")
    print("  Reachy tracks face and responds to hand gestures:")
    print("    Left hand up  → Left antenna raises")
    print("    Right hand up → Right antenna raises")
    print("    Both hands up → Both antennas raise")
    print("="*60 + "\n")
    BODY_YAW_OFFSET = 3.14159  
    FLIP_TRACKING_X = True    
else:
    print("\n" + "="*60)
    print("MODE 2: Gitamini FOLLOWS — Reachy looks at user's BACK")
    print("  Camera points forward toward user")
    print("  Raise ONE hand (held 1s) → Reachy announces the time")
    print("="*60 + "\n")
    BODY_YAW_OFFSET = 0.0
    FLIP_TRACKING_X = False

model_path = "pose_landmarker_lite.task"

BaseOptions = python.BaseOptions
PoseLandmarker = vision.PoseLandmarker
PoseLandmarkerOptions = vision.PoseLandmarkerOptions
VisionRunningMode = vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.VIDEO
)

landmarker = PoseLandmarker.create_from_options(options)
cap = cv2.VideoCapture(0)

reachy = ReachyMini(spawn_daemon=True)
reachy.goto_target(body_yaw=BODY_YAW_OFFSET, duration=2.0)

timestamp = 0

left_hand_is_up = False
right_hand_is_up = False
left_hand_up_start = None
right_hand_up_start = None

fall_detected = False
fall_start_time = None
alert_triggered = False

last_nose_x = 0.5
last_nose_y = 0.4
HEAD_DEAD_ZONE = 0.05  

time_announced = False
time_announce_cooldown = 0
current_time_display = ""
current_time_timer = 0

person_lost_count = 0

def announce_time():
    now_dt = datetime.datetime.now()
    time_str = now_dt.strftime("%I:%M %p")
    print(f"🕐 TIME REQUESTED — Current time is: {time_str}")
    
    def speak():
        tts_engine.say(f"The time is {time_str}")
        tts_engine.runAndWait()
    threading.Thread(target=speak, daemon=True).start()
    
    return time_str


print("\n" + "="*60)
print("Gesture Control System Active — Press ESC to quit")
print("="*60 + "\n")

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

    mode_label = "MODE 1: Reachy faces USER" if MODE == 1 else "MODE 2: Reachy follows USER"
    cv2.putText(frame, mode_label, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)

    if result.pose_landmarks:
        landmarks = result.pose_landmarks[0]
        person_lost_count = 0

        nose           = landmarks[0]
        left_shoulder  = landmarks[11]
        right_shoulder = landmarks[12]
        left_hip       = landmarks[23]
        right_hip      = landmarks[24]
        left_wrist     = landmarks[15]
        right_wrist    = landmarks[16]

        cv2.circle(frame, (int(nose.x * w),           int(nose.y * h)),           5, (0, 255, 0),   -1)
        cv2.circle(frame, (int(left_wrist.x * w),     int(left_wrist.y * h)),     5, (255, 0, 0),   -1)
        cv2.circle(frame, (int(right_wrist.x * w),    int(right_wrist.y * h)),    5, (255, 0, 0),   -1)
        cv2.circle(frame, (int(left_shoulder.x * w),  int(left_shoulder.y * h)),  5, (0, 255, 255), -1)
        cv2.circle(frame, (int(right_shoulder.x * w), int(right_shoulder.y * h)), 5, (0, 255, 255), -1)
        cv2.circle(frame, (int(left_hip.x * w),       int(left_hip.y * h)),       5, (255, 255, 0), -1)
        cv2.circle(frame, (int(right_hip.x * w),      int(right_hip.y * h)),      5, (255, 255, 0), -1)

        FALL_THRESHOLD = 0.7
        nose_low = nose.y > FALL_THRESHOLD
        ls_low   = left_shoulder.y > FALL_THRESHOLD
        rs_low   = right_shoulder.y > FALL_THRESHOLD
        low_count = sum([nose_low, ls_low, rs_low])
        fall_condition = nose_low and ls_low and rs_low

        if fall_condition:
            if fall_start_time is None:
                fall_start_time = now
                print(f"Fall position detected ({low_count}/3 points low), monitoring...")
            elif now - fall_start_time > 1.5 and not alert_triggered:
                print("FALL DETECTED — EMERGENCY!")
                reachy.goto_target(head={"pitch": 15}, antennas=[1.0, 1.0], duration=0.3)
                for _ in range(3):
                    reachy.goto_target(antennas=[0.0, 0.0], duration=0.2)
                    reachy.goto_target(antennas=[1.0, 1.0], duration=0.2)
                alert_triggered = True
            fall_detected = True
        else:
            fall_start_time = None
            if alert_triggered:
                print("Person recovered — resuming normal operation")
                reachy.goto_target(head={"pitch": 0}, antennas=[0.0, 0.0], duration=1.0)
            fall_detected = False
            alert_triggered = False

        cv2.putText(frame, f"Nose Y: {nose.y:.2f}",         (w-200, 30),  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"L Shoulder Y: {left_shoulder.y:.2f}",  (w-200, 60),  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"R Shoulder Y: {right_shoulder.y:.2f}", (w-200, 90),  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Threshold: {FALL_THRESHOLD}",   (w-200, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255),   1)

        if fall_detected:
            cv2.putText(frame, "FALL DETECTED!", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.rectangle(frame, (40, 10), (w-40, 90), (0, 0, 255), 3)

        if not fall_detected:
            nose_x = (1.0 - nose.x) if FLIP_TRACKING_X else nose.x

            target_yaw   = (nose_x - 0.5) * -60
            target_pitch = (nose.y - 0.4) * 40

            nose_moved = (
                abs(nose_x - last_nose_x) > HEAD_DEAD_ZONE or
                abs(nose.y - last_nose_y) > HEAD_DEAD_ZONE
            )

            if nose_moved:
                last_nose_x = nose_x
                last_nose_y = nose.y

        if MODE == 1 and not fall_detected:
            left_hand_up  = right_wrist.y < nose.y
            right_hand_up = left_wrist.y < nose.y

            if left_hand_up:
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

            if right_hand_up:
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

            left_antenna  = 0.8 if left_hand_is_up else 0.0
            right_antenna = 0.8 if right_hand_is_up else 0.0

            if nose_moved:
                reachy.goto_target(
                    head={"pitch": target_pitch, "yaw": target_yaw},
                    antennas=[left_antenna, right_antenna],
                    duration=0.1
                )
            else:
                reachy.goto_target(antennas=[left_antenna, right_antenna], duration=0.3)

            status = " + ".join(filter(None, [
                "LEFT UP"  if left_hand_is_up  else "",
                "RIGHT UP" if right_hand_is_up else ""
            ])) or "HANDS DOWN"
            cv2.putText(frame, status, (50, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, f"Fall Detection: Active ({low_count}/3 low)", (50, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        elif MODE == 2 and not fall_detected:
            left_hand_up  = right_wrist.y < right_shoulder.y
            right_hand_up = left_wrist.y  < left_shoulder.y
            either_hand_up = left_hand_up or right_hand_up

            if either_hand_up:
                if left_hand_up_start is None:
                    left_hand_up_start = now
                elif now - left_hand_up_start > 1.0:
                    if not time_announced and now > time_announce_cooldown:
                        current_time_display = announce_time()
                        current_time_timer = now + 4.0
                        time_announced = True
                        time_announce_cooldown = now + 5.0
                        reachy.goto_target(antennas=[0.8, 0.8], duration=0.3)
                        reachy.goto_target(antennas=[0.0, 0.0], duration=0.3)
                        reachy.goto_target(antennas=[0.8, 0.8], duration=0.3)
            else:
                left_hand_up_start = None
                time_announced = False

            if nose_moved:
                reachy.goto_target(
                    head={"pitch": target_pitch, "yaw": target_yaw},
                    duration=0.1
                )

            if now < current_time_timer and current_time_display:
                cv2.putText(frame, f"TIME: {current_time_display}", (50, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

            status = "HAND RAISED — HOLD FOR TIME" if either_hand_up else "RAISE HAND FOR TIME"
            cv2.putText(frame, status, (50, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Fall Detection: Active ({low_count}/3 low)", (50, 170),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    else:
        person_lost_count += 1

        if person_lost_count > 30:
            if fall_start_time is None:
                fall_start_time = now
                print("⚠ Person lost from frame, monitoring...")
            elif now - fall_start_time > 2.0 and not alert_triggered:
                print("FALL DETECTED — Person disappeared from view!")
                for _ in range(3):
                    reachy.goto_target(antennas=[0.0, 0.0], duration=0.2)
                    reachy.goto_target(antennas=[1.0, 1.0], duration=0.2)
                alert_triggered = True
            fall_detected = True
            cv2.putText(frame, "PERSON LOST - FALL?", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.rectangle(frame, (40, 10), (w-40, 90), (0, 0, 255), 3)
        else:
            cv2.putText(frame, "Searching for person...", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    cv2.imshow("Reachy Mini — Gesture + Mode Control", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
reachy.disconnect()
print("System shutdown complete")