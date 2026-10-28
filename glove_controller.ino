/*
  Flex Sensor Glove Controller - Dino Game
  Board: Arduino Uno / Nano

  Wiring:
    Each flex sensor: one leg -> analog pin, other leg -> GND.
    (No external divider resistor needed - the ATmega's internal pull-up
    resistor on each analog pin does that job instead, enabled below.)
      A0 Thumb flex    A1 Index flex
      A2 Middle flex   A3 Ring flex
      A4 Pinky flex
    D2 Green LED (+220R)   D3 Red LED (+220R)   D6 Blue LED (+220R)
    D4 Buzzer               D5 Vibration motor (via NPN transistor)

    FALLBACK BUTTONS (used alongside the flex sensors, not instead of them):
    D8 Jump button   -> one leg to D8, other leg to GND (internal pull-up, no resistor)
    D9 Duck button   -> one leg to D9, other leg to GND
    Press both together to restart.

  NOTE: with the internal pull-up, bending a finger still INCREASES the
  analogRead() value, so the isBent() logic and calibration steps below
  are unchanged - just the sensor wiring is simpler.

  Serial protocol:
    Arduino -> PC (one char + newline):
      'J' = Jump triggered (index finger bent)
      'D' = Duck start (middle+ring+pinky curled)
      'd' = Duck release
      'T' = Thumb trigger (restart / select)

    PC -> Arduino (single char):
      'G' = Running / idle   -> Green LED on, everything else off
      'A' = Action (jump/duck) -> brief Blue LED flash + buzzer beep + vibration pulse,
                                    then automatically returns to green
      'L' = Lose              -> Red LED on (stays on until next 'G') + buzzer + vibration

  IMPORTANT: run the calibration steps below before relying on this sketch -
  flex sensors vary a lot from unit to unit.

  This version avoids delay() inside the feedback handling so that rapid
  jump/duck events (which arrive often) never block sensor reading or
  gesture detection - timing is done with millis() instead.
*/

const int THUMB_PIN  = A0;
const int INDEX_PIN  = A1;
const int MIDDLE_PIN = A2;
const int RING_PIN   = A3;
const int PINKY_PIN  = A4;

const int GREEN_LED = 2;
const int RED_LED   = 3;
const int BLUE_LED  = 6;
const int BUZZER    = 4;
const int VIBRATOR  = 5;

const int JUMP_BUTTON_PIN = 8;  
const int DUCK_BUTTON_PIN = 9; 

// ---- Calibration values----------------
int thumbFlat = 300,  thumbBent = 600;
int indexFlat = 300,  indexBent = 650;
int midFlat   = 300,  midBent   = 650;
int ringFlat  = 300,  ringBent  = 650;
int pinkyFlat = 300,  pinkyBent = 650;

bool indexWasBent = false;
bool duckActive   = false;
bool thumbWasBent = false;

// ---- Fallback button state ----
bool btnJumpWasPressed = false;
bool btnDuckHeld = false;
bool btnDuckWasHeld = false;
bool btnBothWasPressed = false;

// ---- Non-blocking LED / vibration state machine ----
enum LedMode { MODE_GREEN, MODE_BLUE_PULSE, MODE_RED };
LedMode ledMode = MODE_GREEN;
unsigned long bluePulseStart = 0;
const unsigned long BLUE_PULSE_MS = 200;

bool vibrating = false;
unsigned long vibrateStart = 0;
unsigned long vibrateDurationMs = 0;

int bentThreshold(int flat, int bent) {
  return flat + (int)((bent - flat) * 0.6);
}

bool isBent(int pin, int flat, int bent) {
  int val = analogRead(pin);
  return val > bentThreshold(flat, bent);
}

void setLeds(bool g, bool b, bool r) {
  digitalWrite(GREEN_LED, g ? HIGH : LOW);
  digitalWrite(BLUE_LED,  b ? HIGH : LOW);
  digitalWrite(RED_LED,   r ? HIGH : LOW);
}

void startVibration(unsigned long durationMs) {
  digitalWrite(VIBRATOR, HIGH);
  vibrating = true;
  vibrateStart = millis();
  vibrateDurationMs = durationMs;
}

void setup() {
  Serial.begin(9600);

  pinMode(THUMB_PIN, INPUT_PULLUP);
  pinMode(INDEX_PIN, INPUT_PULLUP);
  pinMode(MIDDLE_PIN, INPUT_PULLUP);
  pinMode(RING_PIN, INPUT_PULLUP);
  pinMode(PINKY_PIN, INPUT_PULLUP);

  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
  pinMode(VIBRATOR, OUTPUT);

  pinMode(JUMP_BUTTON_PIN, INPUT_PULLUP);
  pinMode(DUCK_BUTTON_PIN, INPUT_PULLUP);

  setLeds(true, false, false); 
}

void loop() {
  bool thumbBentNow = isBent(THUMB_PIN, thumbFlat, thumbBent);
  bool indexBentNow = isBent(INDEX_PIN, indexFlat, indexBent);
  bool midBentNow   = isBent(MIDDLE_PIN, midFlat, midBent);
  bool ringBentNow  = isBent(RING_PIN, ringFlat, ringBent);
  bool pinkyBentNow = isBent(PINKY_PIN, pinkyFlat, pinkyBent);

  if (indexBentNow && !indexWasBent) {
    Serial.println("J");
  }
  indexWasBent = indexBentNow;

  bool duckNow = midBentNow && ringBentNow && pinkyBentNow;
  if (duckNow && !duckActive) {
    Serial.println("D");
    duckActive = true;
  } else if (!duckNow && duckActive) {
    Serial.println("d");
    duckActive = false;
  }

  if (thumbBentNow && !thumbWasBent) {
    Serial.println("T");
  }
  thumbWasBent = thumbBentNow;

  // ---- Fallback buttons ----
  bool jumpBtnPressed = (digitalRead(JUMP_BUTTON_PIN) == LOW); 
  bool duckBtnPressed = (digitalRead(DUCK_BUTTON_PIN) == LOW);

  bool bothBtnPressed = jumpBtnPressed && duckBtnPressed;
  if (bothBtnPressed && !btnBothWasPressed) {
    Serial.println("T"); 
  }
  btnBothWasPressed = bothBtnPressed;

  if (jumpBtnPressed && !btnJumpWasPressed && !duckBtnPressed) {
    Serial.println("J");
  }
  btnJumpWasPressed = jumpBtnPressed;

  btnDuckHeld = duckBtnPressed && !jumpBtnPressed;
  if (btnDuckHeld && !btnDuckWasHeld) {
    Serial.println("D");
  } else if (!btnDuckHeld && btnDuckWasHeld) {
    Serial.println("d");
  }
  btnDuckWasHeld = btnDuckHeld;

  if (Serial.available() > 0) {
    char cmd = Serial.read();
    handleFeedback(cmd);
  }

  updateTimers();

  delay(20); 
}

void handleFeedback(char cmd) {
  if (cmd == 'G') {
    ledMode = MODE_GREEN;
    setLeds(true, false, false);
    noTone(BUZZER);
  } else if (cmd == 'A') {
    ledMode = MODE_BLUE_PULSE;
    bluePulseStart = millis();
    setLeds(false, true, false);
    tone(BUZZER, 1200, 100);
    startVibration(150);
  } else if (cmd == 'L') {
    ledMode = MODE_RED;
    setLeds(false, false, true);
    tone(BUZZER, 400, 500);
    startVibration(500);
  }
}

void updateTimers() {
  // Auto-return from a blue action flash back to green 
  if (ledMode == MODE_BLUE_PULSE && millis() - bluePulseStart >= BLUE_PULSE_MS) {
    ledMode = MODE_GREEN;
    setLeds(true, false, false);
  }

  if (vibrating && millis() - vibrateStart >= vibrateDurationMs) {
    digitalWrite(VIBRATOR, LOW);
    vibrating = false;
  }
}
