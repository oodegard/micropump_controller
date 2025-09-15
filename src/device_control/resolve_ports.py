
import os
import serial.tools.list_ports
from dotenv import load_dotenv
# Information about devices
def get_port_by_id(device: str) -> str:
    """
    Get the serial port for a device (pump or arduino) using IDs from .env file.

    Args:
        device (str): Either 'pump' or 'arduino'.

    Returns:
        str: The device's serial port (e.g., 'COM3').

    Raises:
        Exception: If no matching device is found or device type is invalid.
    """
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
    if device.lower() == 'pump':
        vid = int(os.getenv('PUMP_VID'))
        pid = int(os.getenv('PUMP_PID'))
    elif device.lower() == 'arduino':
        vid = int(os.getenv('ARDUINO_VID'))
        pid = int(os.getenv('ARDUINO_PID'))
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
# Information about devices
'''
Port: COM4 
    Description: USB Micropump Control (COM4)
    HWID: USB VID:PID=0403:B4C0 SER=07
    VID: 1027
    PID: 46272
    Manufacturer: FTDI
    Serial Number: 07

Available ports:
  Port: COM5 [Arduino Uno detected]
    Description: USB Serial Device (COM5)
    HWID: USB VID:PID=2341:0043 SER=851383138333513121E1 LOCATION=1-1.3
    VID: 9025
    PID: 67
    Manufacturer: Microsoft
    Serial Number: 851383138333513121E1    
'''





def list_all_ports() -> list:
    """
    List all available serial ports.

    Returns:
        list: A list of available serial ports with their descriptions.
    """
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]

if __name__ == "__main__":
    # List all available ports
    print("Available ports:")
    for port, desc in list_all_ports():
        print(f"  Port: {port}\n    Description: {desc}")

    # Check for pump port
    try:
        pump_port = get_port_by_id('pump')
        print(f"Pump found on port: {pump_port}")
    except Exception as e:
        print(f"Pump not found: {e}")

    # Check for Arduino port
    try:
        arduino_port = get_port_by_id('arduino')
        print(f"Arduino found on port: {arduino_port}")
    except Exception as e:
        print(f"Arduino not found: {e}")
