from pathlib import Path
from typing import Optional

from usbx import usb, Device, TransferDirection, TransferType, USBError

DEFAULT_VID = 0x0403
DEFAULT_PID = 0xB4C0


def load_device_ids() -> tuple[int, int]:
    """Load VID/PID from the project .env file if present."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    vid = DEFAULT_VID
    pid = DEFAULT_PID
    if not env_path.exists():
        return vid, pid
    try:
        with env_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = map(str.strip, line.split("=", 1))
                if key == "PUMP_VID":
                    vid = int(value, 0)
                elif key == "PUMP_PID":
                    pid = int(value, 0)
    except OSError as exc:
        print(f"Warning: unable to read {env_path}: {exc}")
    except ValueError as exc:
        print(f"Warning: invalid VID/PID value in {env_path}: {exc}")
    return vid, pid


def select_interface(device: Device) -> Optional[int]:
    """Pick the first interface that exposes a BULK/INT OUT endpoint."""
    for intf in device.configuration.interfaces:
        alt = intf.current_alternate
        for endpoint in alt.endpoints:
            if endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT) and \
                    endpoint.direction == TransferDirection.OUT:
                return intf.number
    return None


def find_endpoint_number(device: Device, interface_number: int, direction: TransferDirection) -> Optional[int]:
    interface = device.get_interface(interface_number)
    if interface is None:
        return None
    for endpoint in interface.current_alternate.endpoints:
        if endpoint.direction == direction and endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT):
            return endpoint.number
    return None


def main() -> None:
    vid, pid = load_device_ids()
    print(f"Searching for pump VID=0x{vid:04x}, PID=0x{pid:04x}")

    device = usb.find_device(vid=vid, pid=pid)

    if device is None:
        print("Pump not found. Ensure it is connected and the VID/PID are correct.")
        return

    print(f"Pump found: VID=0x{device.vid:04x}, PID=0x{device.pid:04x}, product={device.product}")

    interface_number = select_interface(device)
    if interface_number is None:
        print("Unable to find a suitable interface with a bulk/interrupt OUT endpoint.")
        return

    print(f"Using interface {interface_number}.")

    claimed = False
    try:
        device.open()
        device.claim_interface(interface_number)
        claimed = True

        out_ep = find_endpoint_number(device, interface_number, TransferDirection.OUT)
        in_ep = find_endpoint_number(device, interface_number, TransferDirection.IN)

        if out_ep is None:
            print("No bulk/interrupt OUT endpoint available on the selected interface.")
            return

        print(f"Writing to endpoint {out_ep}.")
        device.transfer_out(out_ep, b"START\r")
        print("Command sent to pump.")

        if in_ep is not None:
            print(f"Reading from endpoint {in_ep}.")
            response = device.transfer_in(in_ep, timeout=1.0)
            if response:
                print("Response from pump:", response)
            else:
                print("Pump responded with no data.")
        else:
            print("No bulk/interrupt IN endpoint available; skipping read.")

    except USBError as exc:
        print(f"USB communication error: {exc}")
    finally:
        if claimed:
            try:
                device.release_interface(interface_number)
            except USBError as exc:
                print(f"Failed to release interface {interface_number}: {exc}")
        if device.is_open:
            device.close()


if __name__ == "__main__":
    main()
