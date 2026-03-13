# reachy_follow

Assistive interaction software for the **Reachy Mini** robot mounted on a **Gitamini** mobile platform, developed as part of the **SOAR project at the Stanford Robotics Center (SRC)**.

The system enables intuitive interaction between older adults and the robot using **vision-based gesture recognition** powered by **MediaPipe Pose Landmarker**.

---

## Overview

The software allows users to interact with Reachy through body gestures and simple visual cues. The robot can operate in two interaction modes: **Leading** and **Following**, designed for guided navigation and conversational interaction.

Additional safety features include **fall detection** and **person lost detection**, which remain active in both modes.

---

## Setup

1. Download and install the **Reachy Mini application**.
2. Connect the **Reachy Mini robot to your computer using a USB-C cable**.
3. Run the main interaction script.

---

## Interaction Modes

### Mode 1: Leading

- Reachy faces the user while the **Gitamini platform moves forward**.
- The robot maintains eye contact by **tracking the user’s head position**.
- The user can control the robot’s antenna using **left or right hand gestures**.

### Mode 2: Following

- The user acts as a **tour guide**, walking backwards while facing Reachy.
- Reachy follows the user during movement.
- The user can **pause and interact with Reachy** (e.g., ask questions such as the time).

---

## Safety Features

Active in both modes:

- **Fall detection**
- **Person lost detection**

These mechanisms ensure that the system reacts appropriately if the user falls or leaves the robot’s field of view.

---

## Future Improvements

Potential next steps include:

- Integrating **Leading and Following modes into a unified interaction framework**
- Adding **direct gesture control of the Gitamini platform**
- Reducing latency using alternative perception models such as:
  - **YOLO-based detectors**
  - **Hugging Face vision models**

The current implementation prioritizes **robust human–robot interaction**, allowing moderate perception latency while maintaining reliable gesture recognition.
