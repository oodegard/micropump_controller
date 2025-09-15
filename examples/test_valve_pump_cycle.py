import sys, os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from device_control.pump import BartelsPumpController
from device_control.valve import ValveController
from device_control.resolve_ports import get_port_by_id

def main():
    pump = BartelsPumpController({
        'pump_port': get_port_by_id('pump'),
        'bartels_freq': 100,  # Example frequency in Hz
        'bartels_voltage': 100  # Example voltage in V
    })
    valve = ValveController(port=get_port_by_id('arduino'))

    try:
        # --- Continuous Pump Mode ---
        print("\n--- Continuous Pump Mode ---")
        print("Starting pump. Valve will be OFF for 20s, then ON for 40s (total 1 minute). Listen for clicks when valve changes.")
        pump.bartels_start()
        valve.off()
        print("Valve OFF (20s)...")
        time.sleep(20)
        valve.on()
        print("Valve ON (40s)...")
        time.sleep(40)
        pump.bartels_stop()
        print("Stopped pump after 1 minute.\n")
        time.sleep(3)

        # --- Pulsed Valve Mode ---
        print("--- Pulsed Valve Mode ---")
        print("Starting pump. Toggling valve ON/OFF every 0.5s for 1 minute. Listen for rapid clicks.")
        pump.bartels_start()
        start_time = time.time()
        while time.time() - start_time < 60:
            valve.on()
            time.sleep(0.5)
            valve.off()
            time.sleep(0.5)
        pump.bartels_stop()
        print("Stopped pump after 1 minute of pulsed valve mode.\n")
    finally:
        pump.close()
        valve.close()
        print("Closed both pump and valve.")

if __name__ == "__main__":
    main()
