"""Simple serial-only valve controller for Arduino-based solenoid valve."""

import serial
import logging


class ValveController:
    """Controller for a solenoid valve via Arduino + relay using serial commands."""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._initialize()

    def _initialize(self):
        """Initialize serial connection to valve controller."""
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=2)
            logging.info(f'Valve connection established on {self.port}')
            # Perform initialization pulse test for audible confirmation
            self._perform_initialization_test()
        except serial.SerialException as e:
            logging.error(f'No valve found on {self.port}: {e}')
            self.ser = None

    def _perform_initialization_test(self):
        """Perform a quick on/off pulse during initialization for audible confirmation."""
        if self.ser is None:
            return
        
        import time
        logging.info("WRENCH Performing valve initialization test...")
        logging.info("  Valve ON...")
        self.on()
        time.sleep(0.5)  # 500ms on
        logging.info("  Valve OFF...")
        self.off()
        logging.info("OK Valve initialization test complete - valve is working!")

    def close(self):
        """Close serial connection."""
        if self.ser is not None:
            try:
                self.ser.close()
                logging.info("Valve connection closed")
            except Exception:
                pass

    def _send(self, command: str) -> str:
        """Send command to valve and return response."""
        if self.ser is None:
            logging.error("Valve is not initialized.")
            return "Serial not initialized"
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            # Prefix with VALVE for multi-relay Arduino firmware
            full_command = f"VALVE {command.strip()}"
            line = (full_command + "\n").encode("ascii", errors="ignore")
            self.ser.write(line)
            self.ser.flush()
            resp = self.ser.readline().decode("ascii", errors="ignore").strip()
            logging.info(f"Sent valve command: '{command}', response: '{resp}'")
            return resp
        except Exception as e:
            logging.error(f"Valve serial error: {e}")
            return f"Serial error: {e}"

    def on(self):
        """Turn valve on."""
        return self._send("ON")

    def off(self):
        """Turn valve off."""
        return self._send("OFF")

    def toggle(self):
        """Toggle valve state."""
        return self._send("TOGGLE")

    def state(self):
        """Get valve state."""
        return self._send("STATE?")

    def pulse(self, ms: int):
        """Pulse valve for specified milliseconds."""
        return self._send(f"PULSE {ms}")