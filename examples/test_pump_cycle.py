import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import time
from device_control.pump import BartelsPumpController
from device_control.resolve_ports import get_port_by_id

# Example configuration for the Bartels pump
config = {
    'pump_port': get_port_by_id('pump'),
    'bartels_freq': 100,  # Example frequency in Hz
    'bartels_voltage': 100  # Example voltage in V
}

# Initialize the pump controller
pump = BartelsPumpController(config)

try:

    print("About to start pump. Listen for a sound!")
    time.sleep(2)
    print("Starting pump...")
    pump.bartels_start()
    time.sleep(3)

    print("About to stop pump.")
    time.sleep(2)
    print("Stopping pump...")
    pump.bartels_stop()

    print("Pump test complete.")
finally:
    pump.close()
    print("Pump closed.")
