import serial
from device_control.utils.base import DeviceController

class ValveController(DeviceController):
    """Controller for a solenoid valve via Arduino + relay."""

    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__(port, baudrate)
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=2)
        except serial.SerialException:
            self.ser = None

    def close(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass

    def _send(self, command: str) -> str:
        if self.ser is None:
            return "Serial not initialized"
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            line = (command.strip() + "\n").encode("ascii", errors="ignore")
            self.ser.write(line)
            self.ser.flush()
            resp = self.ser.readline().decode("ascii", errors="ignore").strip()
            return resp
        except Exception as e:
            return f"Serial error: {e}"

    def on(self):
        self._send("ON")

    def off(self):
        self._send("OFF")

    def toggle(self):
        return self._send("TOGGLE")

    def state(self):
        return self._send("STATE?")

    def pulse(self, ms: int):
        return self._send(f"PULSE {ms}")
