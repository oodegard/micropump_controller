import time
from device_control.pump import BartelsPumpController

# Example configuration for the Bartels pump
config = {
    'pump_port': 'COM3',  # Replace with the actual COM port
    'bartels_freq': 100,  # Example frequency in Hz
    'bartels_voltage': 5  # Example voltage in V
}

# Initialize the pump controller
pump = BartelsPumpController(config)

try:
    # Start a pump cycle for 10 seconds
    print("Starting pump cycle...")
    pump.pump_cycle(run_time=10)
    print("Pump cycle complete.")
finally:
    # Ensure the pump is properly closed
    pump.close()
