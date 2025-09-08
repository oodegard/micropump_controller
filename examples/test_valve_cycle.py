# File: examples/valve_cycle.py
# Turns valve ON for 2s, OFF for 1s, repeated 10 times.

import time

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


from device_control.valve import ValveController

def main():
    valve = ValveController(port="COM6")  # change if needed

    for i in range(10):
        print(f"Cycle {i+1}: Valve ON")
        valve.on()
        time.sleep(2)

        print(f"Cycle {i+1}: Valve OFF")
        valve.off()
        time.sleep(1)

    print("Done.")

if __name__ == "__main__":
    main()
