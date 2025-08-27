from .base import DeviceController
from .serial_manager import send_command

class ValveController(DeviceController):
    """Controller for a solenoid valve via Arduino + relay."""

    def on(self):
        send_command(self.port, "ON", self.baudrate)

    def off(self):
        send_command(self.port, "OFF", self.baudrate)

    def toggle(self):
        return send_command(self.port, "TOGGLE", self.baudrate)

    def state(self):
        return send_command(self.port, "STATE?", self.baudrate)

    def pulse(self, ms: int):
        return send_command(self.port, f"PULSE {ms}", self.baudrate)
