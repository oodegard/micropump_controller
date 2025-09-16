import time
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.controllers.valve_control import ValveController
from src.utils.resolve_ports import get_port_by_id

def main():

    valve = ValveController(port=get_port_by_id('arduino'))

    print("Testing valve ON...")
    valve.on()
    time.sleep(1)
    print("Testing valve OFF...")
    valve.off()
    time.sleep(1)
    print("Testing valve TOGGLE...")
    valve.toggle()
    time.sleep(1)
    print("Testing valve STATE...")
    state = valve.state()
    print(f"Valve state: {state}")
    print("Testing valve PULSE 500 ms...")
    valve.pulse(500)
    time.sleep(1)
    print("Testing valve ON/OFF cycle 3 times...")
    for i in range(3):
        print(f"Cycle {i+1}: Valve ON")
        valve.on()
        time.sleep(0.5)
        print(f"Cycle {i+1}: Valve OFF")
        valve.off()
        time.sleep(0.5)
    print("Valve test complete.")
    valve.close()
    print("Valve closed.")

if __name__ == "__main__":
    main()
