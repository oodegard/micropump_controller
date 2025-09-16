# Adjusted imports to reflect the new structure
import sys, os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.controllers.pump_control import BartelsPump
from src.controllers.valve_control import ValveController
from src.utils.resolve_ports import get_port_by_id

def main():
    pump_port = get_port_by_id('pump')
    arduino_port = get_port_by_id('arduino')

    pump = BartelsPump(pump_port)
    valve = ValveController(port=arduino_port)

    try:
        # --- Continuous Pump Mode ---
        print("\n--- Continuous Pump Mode ---")
        print("Starting pump. Valve will be OFF for 20s, then ON for 40s (total 1 minute). Listen for clicks when valve changes.")
        pump.start()
        valve.off()
        print("Valve OFF (20s)...")
        time.sleep(20)
        valve.on()
        print("Valve ON (40s)...")
        time.sleep(40)
        pump.stop()
        print("Stopped pump after 1 minute.\n")
        time.sleep(3)

        # --- Pulsed Valve Mode ---
        print("--- Pulsed Valve Mode ---")
        print("Starting pump. Toggling valve ON/OFF every 0.5s for 1 minute. Listen for rapid clicks.")
        pump.start()
        start_time = time.time()
        while time.time() - start_time < 60:
            valve.on()
            time.sleep(0.5)
            valve.off()
            time.sleep(0.5)
        pump.stop()
        print("Stopped pump after 1 minute of pulsed valve mode.\n")
    finally:
        pump.close()
        valve.close()
        print("Closed both pump and valve.")

if __name__ == "__main__":
    main()
