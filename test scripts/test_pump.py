# Adjusted imports to reflect the new structure
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
from src.controllers.pump_control import BartelsPump

# Directly specify the pump port for testing
pump_port = "COM3"  # Replace with the actual COM port of the pump

# Initialize the pump controller
pump = BartelsPump(pump_port)

try:

    print("About to start pump. Listen for a sound!")
    time.sleep(2)
    print("Starting pump...")
    pump.start()
    time.sleep(5)

    print("About to stop pump.")
    time.sleep(2)
    print("Stopping pump...")
    pump.stop()

    print("Pump test complete.")
finally:
    pump.close()
    print("Pump closed.")
