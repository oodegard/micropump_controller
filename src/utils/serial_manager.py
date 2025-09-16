# src/device_control/serial_manager.py
"""
Serial utilities for device_control.

- send_command: open port, send a single command, read a single line response.
- discover_ports: enumerate available serial ports (for convenience).

Requires: pyserial
"""

from __future__ import annotations

import time
from typing import List, Optional

from serial import Serial, SerialException  # type: ignore
from serial.tools import list_ports  # type: ignore


def discover_ports() -> List[str]:
    """
    Return a list of available serial port device names.
    Example: ['COM3', 'COM6'] on Windows or ['/dev/ttyACM0'] on Linux.
    """
    return [p.device for p in list_ports.comports()]


def send_command(
    port: str,
    command: str,
    baudrate: int = 115200,
    *,
    read_timeout: float = 2.5,
    reset_delay: float = 1.8,
    newline: str = "\n",
    retries: int = 1,
    encoding: str = "ascii",
) -> str:
    """
    Open the serial port, send `command` (+ newline), and return the first response line.

    Parameters
    ----------
    port : str
        Serial port name, e.g. 'COM6' or '/dev/ttyACM0'.
    command : str
        Command to send (without trailing newline).
    baudrate : int, default 115200
        Baud rate used by the device firmware.
    read_timeout : float, default 2.5
        Seconds to wait for a response line before timing out.
    reset_delay : float, default 1.8
        Delay after opening the port to allow Arduino auto-reset to complete.
    newline : str, default '\\n'
        Line terminator appended to the command.
    retries : int, default 1
        Number of additional attempts if no response is received.
    encoding : str, default 'ascii'
        Encoding for command/response.

    Returns
    -------
    str
        First line of response (stripped). Empty string if nothing was read.

    Raises
    ------
    SerialException
        If the port cannot be opened or another serial error occurs.
    """
    attempt = 0
    last_exc: Optional[Exception] = None

    while attempt <= retries:
        try:
            with Serial(port=port, baudrate=baudrate, timeout=read_timeout) as ser:
                # Give Arduino time to reboot after opening the port (common on UNO)
                time.sleep(max(0.0, reset_delay))

                # Clear any startup banner
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # Send command
                line = (command.strip() + newline).encode(encoding, errors="ignore")
                ser.write(line)
                ser.flush()

                # Read one line as response
                resp = ser.readline().decode(encoding, errors="ignore").strip()
                return resp
        except SerialException as e:
            last_exc = e
            # Immediate failure opening/using port → break unless we want to retry
            if attempt == retries:
                raise
        except Exception as e:  # Non-serial unexpected error
            last_exc = e
            if attempt == retries:
                # Wrap as SerialException for a consistent caller contract
                raise SerialException(f"Unexpected error during serial I/O: {e}") from e

        # If we get here, no response or an error occurred; backoff and retry
        attempt += 1
        time.sleep(0.3)

    # Should not reach here; safeguard return or raise last exception if present
    if last_exc:
        raise SerialException(f"Serial operation failed after retries: {last_exc}")
    return ""
