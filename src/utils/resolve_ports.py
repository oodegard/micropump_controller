# Adjusted imports to reflect the new structure
import os
import serial.tools.list_ports
from dotenv import load_dotenv

# Information about devices
def get_port_by_id(device: str) -> str:
    """
    Get the serial port for a device (pump or Arduino) using IDs from .env file.

    Args:
        device (str): Either 'pump' or 'arduino'.

    Returns:
        str: The device's serial port (e.g., 'COM3').

    Raises:
        Exception: If no matching device is found or device type is invalid.
    """
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
    if device.lower() == 'pump':
        vid = int(os.getenv('PUMP_VID', '0'))
        pid = int(os.getenv('PUMP_PID', '0'))
    elif device.lower() == 'arduino':
        vid = int(os.getenv('ARDUINO_VID', '0'))
        pid = int(os.getenv('ARDUINO_PID', '0'))
    else:
        raise Exception(f"Unknown device type: {device}. Use 'pump' or 'arduino'.")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return port.device
    raise Exception(f"No {device} device found with VID={vid} and PID={pid}.")

def find_pump_port_by_description(keyword: str) -> str:
    """
    Find the serial port for a device based on a keyword in its description.

    Args:
        keyword (str): A unique keyword to identify the device (e.g., 'Bartels').

    Returns:
        str: The device's serial port (e.g., 'COM3').

    Raises:
        Exception: If no matching device is found.
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if keyword.lower() in port.description.lower():
            return port.device
    raise Exception(f"No device found with keyword '{keyword}' in description.")

def find_pump_port_by_vid_pid(vid: int, pid: int) -> str:
    """
    Find the serial port for a device based on its Vendor ID (VID) and Product ID (PID).

    Args:
        vid (int): The Vendor ID of the device.
        pid (int): The Product ID of the device.

    Returns:
        str: The device's serial port (e.g., 'COM3').

    Raises:
        Exception: If no matching device is found.
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return port.device
    raise Exception(f"No device found with VID={vid} and PID={pid}.")

def list_all_ports() -> list:
    """List all available serial ports with description, VID and PID.

    Returns:
        list: A list of tuples ``(device, description, vid, pid)`` where
              ``vid`` and ``pid`` are hexadecimal strings (e.g. ``0403``) or ``None``.
    """
    ports = serial.tools.list_ports.comports()
    results = []
    for port in ports:
        vid = f"{port.vid:04X}" if getattr(port, 'vid', None) is not None else None
        pid = f"{port.pid:04X}" if getattr(port, 'pid', None) is not None else None
        results.append((port.device, port.description, vid, pid))
    return results

