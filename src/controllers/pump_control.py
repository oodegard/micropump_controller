from usbx import usb
for device in usb.get_devices():
    print(device)


# """
# PumpControl (Direct USB Implementation)
# ---------------------------------------

# This module provides a class for controlling the Bartels pump directly via USB.

# """

# # Adjusted imports to reflect the new structure
# import time
# import serial
# import logging

# class BartelsPump:
#     def __init__(self, port: str, baudrate: int = 9600):
#         """Initialize the pump with the given serial port and baud rate."""
#         self.port = port
#         self.baudrate = baudrate
#         try:
#             self.pump = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=2)
#             logging.info(f"Pump connected on {self.port} at {self.baudrate} baud.")
#         except serial.SerialException as e:
#             logging.error(f"Failed to connect to pump on {self.port}: {e}")
#             self.pump = None

#     def close(self):
#         """Close the serial connection to the pump."""
#         if self.pump:
#             self.pump.close()
#             logging.info("Pump connection closed.")

#     def set_frequency(self, freq: int):
#         """Set the pump frequency in Hz."""
#         if self.pump:
#             self.pump.write(f"F{freq}\r".encode("ascii"))
#             logging.info(f"Set frequency to {freq} Hz.")

#     def set_voltage(self, voltage: int):
#         """Set the pump voltage."""
#         if self.pump:
#             self.pump.write(f"A{voltage}\r".encode("ascii"))
#             logging.info(f"Set voltage to {voltage}.")

#     def set_waveform(self, waveform: str):
#         """Set the pump waveform (e.g., RECT, SINE)."""
#         if self.pump:
#             self.pump.write(f"{waveform}\r".encode("ascii"))
#             logging.info(f"Set waveform to {waveform}.")

#     def start(self):
#         """Start the pump."""
#         if self.pump:
#             self.pump.write(b"bon\r")
#             logging.info("Pump started.")

#     def stop(self):
#         """Stop the pump."""
#         if self.pump:
#             self.pump.write(b"boff\r")
#             logging.info("Pump stopped.")

#     def run_cycle(self, duration: float):
#         """Run the pump for a specified duration in seconds."""
#         self.start()
#         time.sleep(duration)
#         self.stop()
