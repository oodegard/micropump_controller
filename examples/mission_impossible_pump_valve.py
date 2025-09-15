import sys, os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from device_control.pump import BartelsPumpController
from device_control.valve import ValveController
from device_control.resolve_ports import get_port_by_id

def play_note(pump, freq, duration, valve):
    pump.bartels_set_freq(freq)
    time.sleep(duration * 0.7)
    valve.on()  # Drum hit
    time.sleep(duration * 0.1)
    valve.off()
    time.sleep(duration * 0.2)

def main():
    pump = BartelsPumpController({
        'pump_port': get_port_by_id('pump'),
        'bartels_freq': 100,
        'bartels_voltage': 100
    })
    valve = ValveController(port=get_port_by_id('arduino'))

    # Mission Impossible main riff (approximate, in Hz and seconds)
    # Use 100 Hz as the main note, with some variation for melody
    notes = [
        (100, 0.4), (100, 0.4), (120, 0.4), (100, 0.4), (140, 0.4), (100, 0.4),
        (160, 0.7), (140, 0.4), (120, 0.4), (100, 0.4), (140, 0.4), (100, 0.4),
        (120, 0.7)
    ]

    print("Get ready for Mission Impossible (pump melody, valve drums)...")
    time.sleep(2)
    try:
        pump.bartels_set_voltage(100)
        pump.bartels_start()
        time.sleep(0.3)  # Let pump spin up
        for freq, dur in notes:
            print(f"Note: {freq} Hz for {dur} s (listen for pump pitch and valve click)")
            play_note(pump, freq, dur, valve)
        print("Done! Your mission, should you choose to accept it...")
    finally:
        pump.bartels_stop()
        pump.close()
        valve.close()
        print("Closed both pump and valve.")

if __name__ == "__main__":
    main()
