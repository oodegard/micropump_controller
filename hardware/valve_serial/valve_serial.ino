// valve_serial.ino
// Arduino sketch for controlling a relay (valve) via serial commands.
//
// Commands (send over Serial Monitor or from Python):
//   ON        -> energize relay (valve ON)
//   OFF       -> de-energize relay (valve OFF)
//   TOGGLE    -> switch state
//   STATE?    -> print current state
//
// Baud rate: 115200

const int RELAY_PIN = 7;      // Pin driving the relay module
bool relayState = false;      // Track ON/OFF state

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // start OFF
  Serial.begin(115200);
  Serial.println("Valve controller ready. Send ON / OFF / TOGGLE / STATE?");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();   // remove whitespace/newlines
    cmd.toUpperCase();

    if (cmd == "ON") {
      relayState = true;
      digitalWrite(RELAY_PIN, HIGH);   // NOTE: if relay is active-LOW, change to LOW
      Serial.println("OK ON");
    }
    else if (cmd == "OFF") {
      relayState = false;
      digitalWrite(RELAY_PIN, LOW);    // NOTE: if relay is active-LOW, change to HIGH
      Serial.println("OK OFF");
    }
    else if (cmd == "TOGGLE") {
      relayState = !relayState;
      digitalWrite(RELAY_PIN, relayState ? HIGH : LOW);
      Serial.println(relayState ? "OK ON" : "OK OFF");
    }
    else if (cmd == "STATE?" || cmd == "STATE") {
      Serial.println(relayState ? "STATE ON" : "STATE OFF");
    }
    else {
      Serial.println("ERR Unknown command");
    }
  }
}
