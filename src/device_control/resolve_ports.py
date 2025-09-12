import serial.tools.list_ports

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
    """
    List all available serial ports.

    Returns:
        list: A list of available serial ports with their descriptions.
    """
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]

if __name__ == "__main__":
    # Example usage
    import serial.tools.list_ports
    print("Available ports:")
    for port in serial.tools.list_ports.comports():
        label = ""
        if getattr(port, 'vid', None) == 9025 and getattr(port, 'pid', None) == 67:
            label = "[Arduino Uno detected]"
        print(f"  Port: {port.device} {label}\n"
              f"    Description: {port.description}\n"
              f"    HWID: {port.hwid}\n"
              f"    VID: {getattr(port, 'vid', None)}\n"
              f"    PID: {getattr(port, 'pid', None)}\n"
              f"    Manufacturer: {getattr(port, 'manufacturer', None)}\n"
              f"    Serial Number: {getattr(port, 'serial_number', None)}\n")
    try:
        pump_port = find_pump_port_by_description("Bartels")
        print("Pump found on port:", pump_port)
    except Exception as e:
        print(e)
