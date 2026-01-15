"""Pinch valve controller (Arduino-based) over serial.

This module mirrors the simple interface in `valve.py` but is named
for a pinch valve connected to an Arduino. The default hardware pin is 9,
but the pin is ultimately defined in the Arduino sketch.

Serial protocol (must match Arduino firmware):
  - "ON"       -> energize valve
  - "OFF"      -> de-energize valve
  - "TOGGLE"  -> toggle state
  - "STATE?"  -> report current state ("STATE ON" / "STATE OFF")
  - "PULSE {ms}" (optional if supported by firmware)

Usage:
  from src.pinch_valve import PinchValveController
  v = PinchValveController(port="COM6", baudrate=115200)
  v.on(); v.off(); v.toggle(); v.state(); v.pulse(150)

Arduino firmware notes:
  - Ensure your sketch drives the correct pin for the pinch valve. For pin 9,
    set e.g. `const int RELAY_PIN = 9;` and implement the same serial commands.
  - Many relay boards are active-LOW. If your valve engages when you send OFF,
    swap the HIGH/LOW logic in the sketch for ON/OFF.
"""

from __future__ import annotations

from typing import Optional
import logging

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore


class PinchValveController:
    """Controller for a pinch valve via Arduino using simple serial commands.

    This class intentionally mirrors the `ValveController` API for drop-in use
    in existing YAML protocols and scripts.
    """

    def __init__(self, port: str, baudrate: int = 115200, *, pin: int = 9, init_pulse: bool = True, shared_serial=None) -> None:
        self.port: str = port
        self.baudrate: int = baudrate
        self.pin: int = pin  # informational; firmware controls actual pin
        self.ser: Optional["serial.Serial"] = shared_serial
        if shared_serial is None:
            self._initialize(init_pulse=init_pulse)

    def _initialize(self, *, init_pulse: bool) -> None:
        """Initialize serial connection to the Arduino valve controller."""
        if serial is None:
            logging.error("pyserial is not installed; cannot open serial port")
            self.ser = None
            return
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=2)
            logging.info(f"Pinch valve connected on {self.port} (baud {self.baudrate}, pin {self.pin})")
            if init_pulse:
                self._perform_initialization_test()
        except Exception as e:  # serial.SerialException and others
            logging.error(f"No pinch valve found on {self.port}: {e}")
            self.ser = None

    def _perform_initialization_test(self) -> None:
        """Optional quick on/off pulse for audible confirmation of connectivity."""
        if self.ser is None:
            return
        import time
        logging.info("PINCH Valve init test: ON for 300ms")
        self.on()
        time.sleep(0.3)
        self.off()
        logging.info("PINCH Valve init test complete")

    def close(self) -> None:
        """Close serial connection."""
        if self.ser is not None:
            try:
                self.ser.close()
                logging.info("Pinch valve connection closed")
            except Exception:
                pass

    # Public API
    def on(self) -> str:
        """Turn valve ON (energize)."""
        return self._send("ON")

    def off(self) -> str:
        """Turn valve OFF (de-energize)."""
        return self._send("OFF")

    def toggle(self) -> str:
        """Toggle valve state."""
        return self._send("TOGGLE")

    def state(self) -> str:
        """Query valve state."""
        return self._send("STATE?")

    def pulse(self, ms: int) -> str:
        """Pulse valve for `ms` milliseconds (requires firmware support)."""
        return self._send(f"PULSE {int(ms)}")

    # Internals
    def _send(self, command: str) -> str:
        """Send a command and return the response (or error string)."""
        if self.ser is None:
            logging.error("Pinch valve serial not initialized")
            return "Serial not initialized"
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            # Prefix with PINCH for multi-relay Arduino firmware
            full_command = f"PINCH {command.strip()}"
            line = (full_command + "\n").encode("ascii", errors="ignore")
            self.ser.write(line)
            self.ser.flush()
            resp = self.ser.readline().decode("ascii", errors="ignore").strip()
            logging.info(f"[PINCH] Sent '{command}', got '{resp}'")
            return resp
        except Exception as e:
            logging.error(f"Pinch valve serial error: {e}")
            return f"Serial error: {e}"
