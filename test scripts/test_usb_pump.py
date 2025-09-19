"""Quick probe with 100 ms delays."""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.controllers.pump_control import UsbPumpController, PumpCommunicationError


def main() -> None:
    try:
        with UsbPumpController() as pump:
            print(f"Connected to pump VID=0x{pump.vid:04x}, PID=0x{pump.pid:04x}")

            def show(cmd: str) -> None:
                response = pump.send_command(cmd)
                print(f"{cmd!r} -> {response!r}")
                time.sleep(0.12)

            show("F100")
            show("A100")
            pump.set_waveform("rect")
            show("bon")
            time.sleep(5.0)
            show("boff")

    except PumpCommunicationError as exc:
        print(f"Pump error: {exc}")


if __name__ == "__main__":
    main()
