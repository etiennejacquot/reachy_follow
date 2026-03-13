# reachy_follow

Assistive interaction software for the **Reachy Mini** robot mounted on a **Gitamini** platform.  
Developed as part of the **SOAR project at the Stanford Robotics Center (SRC)**.

Uses **MediaPipe Pose Landmarker** to recognize gestures and enable simple human–robot interaction for older adults.

## Setup

1. Install the **Reachy Mini app**
2. Connect Reachy Mini via **USB-C**
3. Run the desired script

## Scripts

**gesture_simple.py**
- Left / right hand gesture recognition  
- Fall detection

**gesture_modes.py**
- Full interaction system with two modes:
  - **Leading**
    - Reachy faces the user
    - Gitamini moves forward
    - Reachy tracks the user’s head
    - Hand gestures move the antenna
  - **Following**
    - User walks backwards facing Reachy
    - Reachy follows the user
    - User can stop and interact with Reachy

Fall detection and person-lost detection run in both modes.

## Notes

The system prioritizes direct interaction and may have small perception latency.

Future work could include:
- Integrating both modes into a single adaptive behavior
- Direct gesture control of the Gitamini platform
- Faster perception models (YOLO, HuggingFace vision models)
