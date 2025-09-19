"""USB pump control using the usbx library."""

from __future__ import annotations

import time
import warnings
from pathlib import Path
from typing import Optional

from usbx import Device, TransferDirection, TransferType, USBError, usb

DEFAULT_VID = 0x0403
DEFAULT_PID = 0xB4C0
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
_CMD_DELAY_S = 0.12  # controller needs ~100 ms between commands

# Waveform commands documented for the Bartels mp-x controller
_WAVEFORM_COMMANDS = {
    "MR": "MR",  # rectangular
    "RECT": "MR",
    "RECTANGLE": "MR",
    "SQUARE": "MR",
    "MS": "MS",  # sine
    "SINE": "MS",
    "SIN": "MS",
    "MC": "MC",  # SRS / custom waveform
    "SRS": "MC",
}


class PumpCommunicationError(RuntimeError):
    """Raised when communicating with the pump fails."""


def _load_device_ids() -> tuple[int, int]:
    """Return VID/PID from the project .env file or defaults."""
    vid = DEFAULT_VID
    pid = DEFAULT_PID
    if not ENV_PATH.exists():
        return vid, pid
    try:
        with ENV_PATH.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = map(str.strip, line.split("=", 1))
                if key == "PUMP_VID":
                    vid = int(value, 0)
                elif key == "PUMP_PID":
                    pid = int(value, 0)
    except (OSError, ValueError) as exc:
        raise PumpCommunicationError(f"Unable to parse pump VID/PID from {ENV_PATH}: {exc}") from exc
    return vid, pid


def _select_interface(device: Device) -> int:
    """Pick the first interface exposing a bulk/interrupt OUT endpoint."""
    for intf in device.configuration.interfaces:
        alt = intf.current_alternate
        for endpoint in alt.endpoints:
            if endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT) and \
                    endpoint.direction == TransferDirection.OUT:
                return intf.number
    raise PumpCommunicationError("Pump has no bulk/interrupt OUT endpoint")


def _find_endpoint(device: Device, interface_number: int, direction: TransferDirection) -> Optional[int]:
    interface = device.get_interface(interface_number)
    if interface is None:
        return None
    for endpoint in interface.current_alternate.endpoints:
        if endpoint.direction == direction and endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT):
            return endpoint.number
    return None


def _format_value(value: int, *, name: str, minimum: int, maximum: int) -> str:
    if not minimum <= value <= maximum:
        raise PumpCommunicationError(f"{name} must be between {minimum} and {maximum} (got {value})")
    return f"{value:03d}"


class UsbPumpController:
    """High-level controller for the Bartels USB micropump."""

    def __init__(self, port: Optional[str] = None, *, vid: Optional[int] = None,
                 pid: Optional[int] = None, auto_connect: bool = True):
        if port is not None:
            warnings.warn(
                "Serial port argument is ignored; the pump now uses direct USB access.",
                UserWarning,
                stacklevel=2,
            )
        self.vid, self.pid = _load_device_ids() if vid is None or pid is None else (vid, pid)
        if vid is not None:
            self.vid = vid
        if pid is not None:
            self.pid = pid
        self._device: Optional[Device] = None
        self._interface_number: Optional[int] = None
        self._out_endpoint: Optional[int] = None
        self._in_endpoint: Optional[int] = None
        self._claimed: bool = False
        if auto_connect:
            self.connect()

    # Context-manager helpers -------------------------------------------------
    def __enter__(self) -> "UsbPumpController":
        if not self.connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # Connection management ---------------------------------------------------
    @property
    def connected(self) -> bool:
        return self._device is not None and self._claimed

    def connect(self) -> None:
        if self.connected:
            return
        device = usb.find_device(vid=self.vid, pid=self.pid)
        if device is None:
            raise PumpCommunicationError(
                f"Pump with VID=0x{self.vid:04x} PID=0x{self.pid:04x} not found"
            )
        interface_number = _select_interface(device)
        out_endpoint = _find_endpoint(device, interface_number, TransferDirection.OUT)
        if out_endpoint is None:
            raise PumpCommunicationError("Unable to determine OUT endpoint for pump")
        in_endpoint = _find_endpoint(device, interface_number, TransferDirection.IN)

        try:
            device.open()
            device.claim_interface(interface_number)
        except USBError as exc:
            try:
                device.close()
            except USBError:
                pass
            raise PumpCommunicationError("Failed to open/claim the pump interface") from exc

        self._device = device
        self._interface_number = interface_number
        self._out_endpoint = out_endpoint
        self._in_endpoint = in_endpoint
        self._claimed = True

    def disconnect(self) -> None:
        if self._device is None:
            return
        try:
            if self._claimed and self._interface_number is not None:
                self._device.release_interface(self._interface_number)
        except USBError:
            pass
        finally:
            self._claimed = False
        try:
            self._device.close()
        except USBError:
            pass
        finally:
            self._device = None
            self._interface_number = None
            self._out_endpoint = None
            self._in_endpoint = None

    def close(self) -> None:
        """Compatibility wrapper for legacy code."""
        self.disconnect()

    # Command helpers ---------------------------------------------------------
    def _ensure_ready(self) -> None:
        if not self.connected or self._device is None or self._out_endpoint is None:
            raise PumpCommunicationError("Pump is not connected")

    def send_command(self, command: str | bytes, *, expect_response: bool = True, timeout: float = 1.0) -> bytes:
        """Send a raw command to the pump and return the response bytes."""
        self._ensure_ready()
        payload = command.encode("ascii") if isinstance(command, str) else command
        if not payload.endswith(b"\r"):
            payload += b"\r"
        try:
            self._device.transfer_out(self._out_endpoint, payload)
        except USBError as exc:
            raise PumpCommunicationError(f"Failed to send command {command!r}") from exc
        time.sleep(_CMD_DELAY_S)

        if not expect_response or self._in_endpoint is None:
            return b""
        try:
            response = self._device.transfer_in(self._in_endpoint, timeout=timeout)
        except USBError as exc:
            raise PumpCommunicationError(f"No response for command {command!r}") from exc
        time.sleep(_CMD_DELAY_S)
        return response

    @staticmethod
    def _check_ack(response: bytes, action: str) -> None:
        stripped = response.strip()
        if stripped.upper().startswith(b"ERR"):
            raise PumpCommunicationError(f"Pump reported error while attempting to {action}: {response!r}")

    # High-level operations ---------------------------------------------------
    def set_frequency(self, frequency_hz: int) -> None:
        value = _format_value(int(frequency_hz), name="Frequency", minimum=1, maximum=300)
        response = self.send_command(f"F{value}")
        self._check_ack(response, "set frequency")

    def set_amplitude(self, amplitude: int) -> None:
        value = _format_value(int(amplitude), name="Amplitude", minimum=1, maximum=250)
        response = self.send_command(f"A{value}")
        self._check_ack(response, "set amplitude")

    def set_waveform(self, waveform: str) -> None:
        key = waveform.strip().upper()
        command = _WAVEFORM_COMMANDS.get(key)
        if command is None:
            raise PumpCommunicationError(
                f"Unknown waveform '{waveform}'. Expected one of {sorted(set(_WAVEFORM_COMMANDS) - {'MR','MS','MC'})}"
            )
        response = self.send_command(command)
        self._check_ack(response, "set waveform")

    def start(self) -> None:
        response = self.send_command("bon")
        self._check_ack(response, "start the pump")

    def stop(self) -> None:
        response = self.send_command("boff")
        self._check_ack(response, "stop the pump")

    def pulse(self, duration_s: float, *, frequency_hz: Optional[int] = None,
              amplitude: Optional[int] = None, waveform: Optional[str] = None) -> None:
        if frequency_hz is not None:
            self.set_frequency(frequency_hz)
        if amplitude is not None:
            self.set_amplitude(amplitude)
        if waveform is not None:
            self.set_waveform(waveform)
        self.start()
        try:
            time.sleep(duration_s)
        finally:
            self.stop()


BartelsPump = UsbPumpController

__all__ = ["UsbPumpController", "PumpCommunicationError", "BartelsPump"]
