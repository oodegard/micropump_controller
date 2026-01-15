"""Dual valve controller for Arduino with two relays.

Controls two independent relays on a single Arduino:
- Solenoid valve (pin 7): Buffer selector (OFF=Buffer A, ON=Buffer B)
- Pinch valve (pin 9): Flow gate (OFF=blocked, ON=flow enabled)

Serial protocol (must match Arduino firmware):
  Solenoid commands:
    - "VALVE ON"       -> select Buffer B
    - "VALVE OFF"      -> select Buffer A
    - "VALVE TOGGLE"   -> toggle buffer selection
    - "VALVE STATE?"   -> query state
  
  Pinch commands:
    - "PINCH ON"       -> enable flow
    - "PINCH OFF"      -> block flow
    - "PINCH TOGGLE"   -> toggle flow state
    - "PINCH STATE?"   -> query state

Usage:
  from src.dual_valve import DualValveController
  v = DualValveController(port="COM6", baudrate=115200)
  v.pinch_on()      # Enable flow
  v.solenoid_off()  # Select Buffer A
"""

from __future__ import annotations

from typing import Optional
import logging

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore


class DualValveController:
    """Controller for dual Arduino relays: solenoid (buffer selector) and pinch (flow gate)."""

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        self.port: str = port
        self.baudrate: int = baudrate
        self.ser: Optional["serial.Serial"] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize serial connection to the Arduino."""
        if serial is None:
            logging.error("pyserial is not installed; cannot open serial port")
            self.ser = None
            return
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=2)
            logging.info(f"Dual valve controller connected on {self.port} (solenoid=pin7, pinch=pin9)")
            # Wait for Arduino reset/boot (important for first commands)
            import time
            time.sleep(2.0)
            # Clear any boot messages
            self.ser.reset_input_buffer()
            # Test connection with STATE? command to ensure Arduino is ready
            test_resp = self._send_raw("VALVE STATE?")
            logging.info(f"Connection test response: '{test_resp}'")
        except Exception as e:
            logging.error(f"Dual valve controller failed on {self.port}: {e}")
            self.ser = None

    def close(self) -> None:
        """Close serial connection."""
        if self.ser is not None:
            try:
                self.ser.close()
                logging.info("Dual valve controller closed")
            except Exception as e:
                logging.warning(f"Error closing dual valve: {e}")

    def _send(self, command: str) -> str:
        """Send command and return response."""
        return self._send_raw(command)
    
    def _send_raw(self, command: str) -> str:
        """Send raw command and return response (used internally)."""
        if self.ser is None:
            logging.error("Dual valve not initialized")
            return "Serial not initialized"
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            line = (command.strip() + "\n").encode("ascii", errors="ignore")
            self.ser.write(line)
            self.ser.flush()
            # Delay for Arduino to process command before reading response
            import time
            time.sleep(0.2)  # 200ms to ensure Arduino processes and responds
            # Read all available lines (debug + response)
            responses = []
            while self.ser.in_waiting > 0:
                resp_line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if resp_line:
                    responses.append(resp_line)
                time.sleep(0.01)  # Small delay between lines
            resp = " | ".join(responses) if responses else ""
            logging.info(f"Dual valve command: '{command}', response: '{resp}'")
            return resp
        except Exception as e:
            logging.error(f"Dual valve serial error: {e}")
            return f"Serial error: {e}"

    # Solenoid valve commands (Buffer selector - pin 7)
    def solenoid_on(self) -> str:
        """Select Buffer B (solenoid energized)."""
        return self._send("VALVE ON")

    def solenoid_off(self) -> str:
        """Select Buffer A (solenoid de-energized)."""
        return self._send("VALVE OFF")

    def solenoid_toggle(self) -> str:
        """Toggle buffer selection."""
        return self._send("VALVE TOGGLE")

    def solenoid_state(self) -> str:
        """Query solenoid state."""
        return self._send("VALVE STATE?")

    # Pinch valve commands (Flow gate - pin 9)
    def pinch_on(self) -> str:
        """Enable flow (pinch valve open)."""
        return self._send("PINCH ON")

    def pinch_off(self) -> str:
        """Block flow (pinch valve closed)."""
        return self._send("PINCH OFF")

    def pinch_toggle(self) -> str:
        """Toggle flow state."""
        return self._send("PINCH TOGGLE")

    def pinch_state(self) -> str:
        """Query pinch valve state."""
        return self._send("PINCH STATE?")
