from abc import ABC, abstractmethod

class DeviceController(ABC):
    """Abstract base class for all device controllers."""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate

    @abstractmethod
    def on(self):
        """Turn the device on."""
        pass

    @abstractmethod
    def off(self):
        """Turn the device off."""
        pass

    @abstractmethod
    def state(self) -> str:
        """Return current device state."""
        pass
