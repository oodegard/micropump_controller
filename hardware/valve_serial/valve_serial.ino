// valve_serial.ino
// Arduino sketch for controlling multiple relays (valves) via serial commands.
//
// Commands (send over Serial Monitor or from Python):
//   VALVE ON        -> energize solenoid valve (pin 7)
//   VALVE OFF       -> de-energize solenoid valve
//   VALVE TOGGLE    -> toggle solenoid valve state
//   VALVE STATE?    -> print solenoid valve state
//   PINCH ON        -> energize pinch valve (pin 9)
//   PINCH OFF       -> de-energize pinch valve
//   PINCH TOGGLE    -> toggle pinch valve state
//   PINCH STATE?    -> print pinch valve state
//
// Legacy commands (for backwards compatibility, default to VALVE):
//   ON        -> VALVE ON
//   OFF       -> VALVE OFF
//   TOGGLE    -> VALVE TOGGLE
//   STATE?    -> VALVE STATE?
//
// Baud rate: 115200

const int VALVE_PIN = 7;      // Pin driving the solenoid valve relay
const int PINCH_PIN = 9;      // Pin driving the pinch valve relay
const bool RELAY_ACTIVE_LOW = true; // Set to true if your relay board is active-LOW

bool valveState = false;      // Track solenoid valve ON/OFF state
bool pinchState = false;      // Track pinch valve ON/OFF state

inline void setRelay(int pin, bool on) {
  // Handle boards that energize on LOW (active-LOW) vs HIGH (active-HIGH)
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, on ? LOW : HIGH);
  } else {
    digitalWrite(pin, on ? HIGH : LOW);
  }
}

void setup() {
  pinMode(VALVE_PIN, OUTPUT);
  pinMode(PINCH_PIN, OUTPUT);
  setRelay(VALVE_PIN, false);  // start OFF
  setRelay(PINCH_PIN, false);  // start OFF
  Serial.begin(115200);
  Serial.println("Multi-valve controller ready.");
  Serial.println("Commands: VALVE/PINCH {ON|OFF|TOGGLE|STATE?}");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();

    // Parse device and action
    String device = "";
    String action = "";
    
    // Check for device prefix (VALVE or PINCH)
    if (cmd.startsWith("VALVE ")) {
      device = "VALVE";
      action = cmd.substring(6);  // Remove "VALVE "
    } else if (cmd.startsWith("PINCH ")) {
      device = "PINCH";
      action = cmd.substring(6);  // Remove "PINCH "
    } else {
      // Legacy: treat bare commands as VALVE commands
      device = "VALVE";
      action = cmd;
    }

    action.trim();
    Serial.print("[DBG] device=");
    Serial.print(device);
    Serial.print(" action=");
    Serial.println(action);

    // Process VALVE commands
    if (device == "VALVE") {
      if (action == "ON") {
        valveState = true;
        setRelay(VALVE_PIN, true);
        Serial.println("OK VALVE ON");
      }
      else if (action == "OFF") {
        valveState = false;
        setRelay(VALVE_PIN, false);
        Serial.println("OK VALVE OFF");
      }
      else if (action == "TOGGLE") {
        valveState = !valveState;
        setRelay(VALVE_PIN, valveState);
        Serial.println(valveState ? "OK VALVE ON" : "OK VALVE OFF");
      }
      else if (action == "STATE?" || action == "STATE") {
        Serial.println(valveState ? "STATE VALVE ON" : "STATE VALVE OFF");
      }
      else {
        Serial.println("ERR Unknown VALVE command");
      }
    }
    // Process PINCH commands
    else if (device == "PINCH") {
      if (action == "ON") {
        pinchState = true;
        setRelay(PINCH_PIN, true);
        Serial.println("OK PINCH ON");
      }
      else if (action == "OFF") {
        pinchState = false;
        setRelay(PINCH_PIN, false);
        Serial.println("OK PINCH OFF");
      }
      else if (action == "TOGGLE") {
        pinchState = !pinchState;
        setRelay(PINCH_PIN, pinchState);
        Serial.println(pinchState ? "OK PINCH ON" : "OK PINCH OFF");
      }
      else if (action == "STATE?" || action == "STATE") {
        Serial.println(pinchState ? "STATE PINCH ON" : "STATE PINCH OFF");
      }
      else {
        Serial.println("ERR Unknown PINCH command");
      }
    }
    else {
      Serial.println("ERR Unknown device");
    }
  }
}
