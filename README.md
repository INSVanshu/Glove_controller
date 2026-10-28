# Glove-Controlled Gesture Gaming 🎮

A wearable IoT glove that controls a Python-based Dino-style game using five flex sensors and an Arduino. Finger gestures are detected by the Arduino and sent to the PC over USB serial communication, allowing the player to jump, duck, and restart the game. LEDs, a buzzer, and a vibration motor provide feedback.

## Features

- **Gesture-based controls:** Use finger movements instead of relying only on a keyboard.
- **Five flex sensors:** One sensor for each finger.
- **Jump:** Bend the index finger.
- **Duck:** Curl the middle, ring, and pinky fingers together.
- **Restart/select:** Bend the thumb on the game-over screen.
- **Multi-sensory feedback:** Green, blue, and red LEDs, buzzer tones, and vibration.
- **Fallback controls:** Physical buttons and keyboard controls can be used if needed.
- **Dino-style game:** Obstacles, collision detection, score tracking, and gradually increasing speed.

## How It Works

```text
Five Flex Sensors + Fallback Buttons
                 |
                 v
        Arduino Gesture Detection
                 |
                 v
        USB Serial Communication
              (9600 baud)
                 |
                 v
      Python Serial Reader (PySerial)
                 |
                 v
          Pygame Dino Game
                 |
                 v
     Feedback Commands to Arduino
                 |
                 v
      LEDs + Buzzer + Vibration
```

1. Flex sensors produce analog readings as fingers bend.
2. The Arduino compares readings with calibrated thresholds and detects gestures.
3. Gesture commands are sent to the computer through USB serial.
4. Python receives the commands and updates the game controls.
5. The game sends feedback commands to the Arduino to indicate running, action, or game-over states.

## Gesture Mapping

| Gesture / Input | Serial command | Action |
|---|---|---|
| Bend index finger | `J` | Jump |
| Curl middle + ring + pinky | `D` | Begin ducking |
| Release duck gesture | `d` | Stop ducking |
| Bend thumb | `T` | Restart/select command; used to restart on game-over screen |
| Press jump button | `J` | Jump |
| Hold duck button | `D` / `d` | Duck while held |
| Press both buttons together | `T` | Restart/select command |

The Arduino also receives feedback commands from the Python game:

| Command | Meaning | Hardware feedback |
|---|---|---|
| `G` | Running / idle | Green LED |
| `A` | Successful action | Brief blue LED flash, buzzer beep, vibration pulse |
| `L` | Game over | Red LED, buzzer, vibration |

## Hardware Requirements

- Arduino Uno or Nano (as stated in the sketch comments)
- 5 flex sensors
- 3 LEDs: green, red, and blue
- 220 Ω resistors for the LEDs
- Buzzer
- Vibration motor
- NPN transistor to drive the vibration motor
- 2 push buttons for fallback jump and duck controls
- Breadboard and jumper wires
- USB cable
- Computer capable of running Python and Pygame

> **Important:** The flex-sensor wiring and use of `INPUT_PULLUP` must match your actual circuit. Analog readings and thresholds can vary by sensor and board, so calibrate the values before gameplay. Do not power a vibration motor directly from an Arduino I/O pin; use a suitable transistor driver and appropriate protection components.

## Pin Connections

### Flex Sensors

| Finger | Arduino pin |
|---|---|
| Thumb | `A0` |
| Index | `A1` |
| Middle | `A2` |
| Ring | `A3` |
| Pinky | `A4` |

### Feedback Components and Buttons

| Component | Arduino pin |
|---|---|
| Green LED | `D2` |
| Red LED | `D3` |
| Blue LED | `D6` |
| Buzzer | `D4` |
| Vibration motor driver | `D5` |
| Jump button | `D8` |
| Duck button | `D9` |

For each fallback button, connect one terminal to its assigned digital pin and the other to GND; the sketch uses `INPUT_PULLUP`.

## Software Requirements

- Arduino IDE
- Python 3
- Pygame
- PySerial

Install the Python dependencies:

```bash
pip install pygame pyserial
```

## Setup and Run

### 1. Upload the Arduino sketch

1. Open the Arduino code in the Arduino IDE.
2. Select the correct board and port.
3. Check that the sensor and feedback pins match your wiring.
4. Calibrate the flat and bent values for each flex sensor.
5. Upload the sketch.

### 2. Configure the serial port

Open the Python game file and set `SERIAL_PORT` to the port used by your Arduino. The current code uses:

```python
SERIAL_PORT = "COM3"
BAUD_RATE = 9600
```

On Windows, the port may be `COM3`, `COM4`, or another COM port. On Linux or macOS, it may look like `/dev/ttyUSB0` or `/dev/ttyACM0`.

**Close the Arduino Serial Monitor before starting the Python game**, because the serial port usually cannot be used by both programs at once.

### 3. Run the game

Save the Python code in a file such as `glove_dino.py`, then run:

```bash
python glove_dino.py
```

If the Arduino or PySerial is unavailable, the game attempts to run in keyboard-only fallback mode.

## Keyboard Controls

| Key | Action |
|---|---|
| `Space` | Jump |
| `Down Arrow` | Duck while held |
| `R` | Restart on the game-over screen |

## Calibration

The sketch includes initial calibration values:

- Flat reading: `300`
- Thumb bent reading: `600`
- Other fingers bent reading: `650`

The bending threshold is calculated as:

```cpp
flat + (bent - flat) * 0.6
```

These values are only starting points. Check the analog readings for your actual sensors in flat and bent positions, then update the values in the sketch. Ensure bending produces readings consistent with the `isBent()` logic before relying on the glove.

## Project Structure

A suggested repository layout:

```text
glove-controlled-gesture-gaming/
├── arduino/
│   └── glove_controller.ino
├── python/
│   └── glove_dino.py
├── images/
│   └── demo.png
└── README.md
```

Adjust the filenames and folders to match the files you actually upload to the repository.

## Current Implementation Notes

- Gesture detection uses calibrated thresholds and state changes; it does **not** currently use machine learning, deep learning, computer vision, or NLP.
- The Arduino sketch uses `millis()`-based timing for LED pulses and vibration feedback.
- The Arduino loop includes a 20 ms delay, corresponding to a nominal loop interval of about 50 Hz before processing overhead.
- The game runs its Pygame loop at up to 60 frames per second.
- Restart gestures are handled by the game-over logic.

## Future Improvements

- Replace USB serial with Bluetooth or an ESP32-based wireless connection.
- Add machine-learning-based recognition for more personalized gestures.
- Add an IMU for hand orientation and 3D motion tracking.
- Create a mobile companion app for live sensor visualization.
- Add two-glove multiplayer gameplay.
- Design a compact PCB and wearable enclosure.
- Evaluate gesture accuracy, response time, reliability, and user comfort through structured testing.

## Applications

Potential areas for further exploration include:

- Gesture-controlled gaming and entertainment
- Assistive human-computer interaction
- Rehabilitation and finger-flexion exercises
- Robotics teleoperation
- Virtual and augmented reality interfaces
- Gesture-to-text interfaces

These are potential applications, not validated outcomes of the current prototype.

## Team

- **Team name:** _Add team name_
- **Team members:** _Add names and contributions_
- **Institution / department:** _Add details_

## Repository and Demo

- **GitHub repository:** _Add repository URL_
- **Demo video:** _Add demo link_
- **Project presentation:** _Add presentation link_

## License

Choose and add a license before distributing or reusing this project. For example, you may select an open-source license that matches your team's intentions.
