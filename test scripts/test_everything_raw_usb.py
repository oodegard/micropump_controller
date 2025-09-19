"""Brute-force raw USB attempts for Bartels pump over FTDI without VCP driver.

This script tries multiple strategies:
  - Optional FTDI initialization sequence (vendor control transfers)
  - Baud rates (needed only with FTDI init)
  - Line endings variants (CR, LF, CRLF, double CR)
  - Command case (upper vs given)
  - Inter-command delays
  - Wake sequences (optional prefaces)
  - Multiple commands (F100, A100, MR, BON/BOFF)

It logs every transfer (OUT/IN) with hex dumps and interpreted printable ASCII (after stripping FTDI 2-byte status when appropriate).

Run: python -m "test scripts.test_everything_raw_usb" (or call directly) from repo root.

Outputs: creates folder logs_raw_usb/<timestamp>/ with per-attempt JSONL and a summary table.
"""
from __future__ import annotations
import sys
import json
import time
import itertools as it
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from usbx import usb, Device, USBError  # type: ignore
from usbx import TransferDirection, TransferType  # type: ignore

# Defaults from existing code
DEFAULT_VID = 0x0403
DEFAULT_PID = 0xB4C0

LOG_ROOT = PROJECT_ROOT / "logs_raw_usb"
LOG_ROOT.mkdir(exist_ok=True)

# FTDI vendor requests constants (subset)
FTDI_REQ_RESET = 0
FTDI_REQ_SET_MODEM_CTRL = 1
FTDI_REQ_SET_FLOW_CTRL = 2
FTDI_REQ_SET_BAUDRATE = 3
FTDI_REQ_SET_DATA = 4
FTDI_REQ_SET_LATENCY = 9

FTDI_SIO_RESET_SIO = 0
FTDI_SIO_RESET_PURGE_RX = 1
FTDI_SIO_RESET_PURGE_TX = 2

# Baud rate divisors (simplified for standard rates for FT232R style chips)
# Using precomputed values (value, index) composed into 16-bit value: (value | index << 14)
# Source: FTDI AN_232B-05; here we only include common ones.
FTDI_BAUD_DIVISORS = {
    9600: 0x4138,
    19200: 0x809C,
    38400: 0xC04E,
    57600: 0x0034,
    115200: 0x001A,
}

LINE_ENDINGS = {
    'CR': b'\r',
    'LF': b'\n',
    'CRLF': b'\r\n',
    'CRCR': b'\r\r',
}

COMMAND_SET = ["F100", "A100", "MR", "BON", "BOFF"]

@dataclass
class AttemptConfig:
    ftdi_init: bool
    baud: int
    line_ending: str
    uppercase: bool
    delay_s: float
    wake: bool

@dataclass
class AttemptResult:
    config: AttemptConfig
    success: bool
    notes: str
    responses: List[Tuple[str, str, str]]  # (command, hex_raw, ascii_payload)


def find_interface_and_endpoints(device: Device):
    for intf in device.configuration.interfaces:
        alt = intf.current_alternate
        out_ep = None
        in_ep = None
        for ep in alt.endpoints:
            if ep.transfer_type in (TransferType.BULK, TransferType.INTERRUPT):
                if ep.direction == TransferDirection.OUT and out_ep is None:
                    out_ep = ep.number
                elif ep.direction == TransferDirection.IN and in_ep is None:
                    in_ep = ep.number
        if out_ep is not None:
            return intf.number, out_ep, in_ep
    raise RuntimeError("No suitable interface with OUT endpoint")


def ftdi_control(device: Device, request: int, value: int, index: int = 0, data: bytes | None = None):
    # bmRequestType: 0x40 (Host to device, Vendor, Device)
    device._context.control_transfer(0x40, request, value, index, data if data else b"")  # type: ignore[attr-defined]


def ftdi_initialize(device: Device, baud: int, latency: int = 16):
    # Reset and purge
    ftdi_control(device, FTDI_REQ_RESET, FTDI_SIO_RESET_SIO)
    time.sleep(0.02)
    ftdi_control(device, FTDI_REQ_RESET, FTDI_SIO_RESET_PURGE_RX)
    ftdi_control(device, FTDI_REQ_RESET, FTDI_SIO_RESET_PURGE_TX)
    # Flow control off
    ftdi_control(device, FTDI_REQ_SET_FLOW_CTRL, 0x0000)
    # Baud
    div = FTDI_BAUD_DIVISORS.get(baud)
    if div is not None:
        ftdi_control(device, FTDI_REQ_SET_BAUDRATE, div)
    # Data: 8N1 = 0x0008
    ftdi_control(device, FTDI_REQ_SET_DATA, 0x0008)
    # Latency
    if 1 <= latency <= 255:
        ftdi_control(device, FTDI_REQ_SET_LATENCY, latency)


def strip_status(data: bytes) -> bytes:
    if len(data) >= 2:
        return data[2:]
    return b""


def printable(data: bytes) -> str:
    if not data:
        return ""
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def attempt(config: AttemptConfig) -> AttemptResult:
    responses: List[Tuple[str, str, str]] = []
    try:
        device = usb.find_device(vid=DEFAULT_VID, pid=DEFAULT_PID)
        if device is None:
            return AttemptResult(config, False, "Device not found", [])
        interface_number, out_ep, in_ep = find_interface_and_endpoints(device)
        device.open()
        device.claim_interface(interface_number)
        try:
            if config.ftdi_init:
                ftdi_initialize(device, config.baud, latency=16)
                time.sleep(0.05)
            if config.wake:
                for wake_cmd in [b"\r", b" ", b"U"]:
                    try:
                        device.transfer_out(out_ep, wake_cmd)
                        time.sleep(0.05)
                        if in_ep is not None:
                            try:
                                _ = device.transfer_in(in_ep, timeout=0.2)
                            except USBError:
                                pass
                    except USBError:
                        pass
            for raw_cmd in COMMAND_SET:
                cmd = raw_cmd.upper() if config.uppercase else raw_cmd
                payload = cmd.encode('ascii') + LINE_ENDINGS[config.line_ending]
                try:
                    device.transfer_out(out_ep, payload)
                except USBError as exc:
                    responses.append((cmd, f"OUT_ERROR:{exc}", ""))
                    continue
                time.sleep(config.delay_s)
                read_data = b""
                if in_ep is not None:
                    # Try up to 3 reads to accumulate payload
                    for _ in range(3):
                        try:
                            chunk = device.transfer_in(in_ep, timeout=0.3)
                        except USBError:
                            break
                        if not chunk:
                            break
                        read_data += chunk
                        if len(chunk) < 64:
                            break
                        time.sleep(0.02)
                stripped = strip_status(read_data) if read_data else b""
                responses.append((cmd, read_data.hex(), printable(stripped)))
                time.sleep(config.delay_s)
        finally:
            try:
                device.release_interface(interface_number)
            except USBError:
                pass
            try:
                device.close()
            except USBError:
                pass
        # Evaluate success heuristic: any response longer than just status bytes
        any_payload = any(len(bytes.fromhex(hex_raw)) > 2 for (_, hex_raw, _) in responses if not hex_raw.startswith('OUT_ERROR'))
        note = "payload>2 bytes" if any_payload else "only status or no data"
        return AttemptResult(config, any_payload, note, responses)
    except Exception as exc:  # noqa: BLE001
        return AttemptResult(config, False, f"exception: {exc}", responses)


def main():
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    out_dir = LOG_ROOT / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / 'summary.jsonl'

    baud_options = [9600, 115200]
    configs = []
    for ftdi_init in [False, True]:
        for baud in baud_options:
            for line_end in LINE_ENDINGS.keys():
                for uppercase in [False, True]:
                    for delay_s in [0.05, 0.12, 0.2]:
                        for wake in [False, True]:
                            # Skip baud variations when not doing ftdi init (no effect)
                            if not ftdi_init and baud != baud_options[0]:
                                continue
                            configs.append(AttemptConfig(ftdi_init, baud, line_end, uppercase, delay_s, wake))

    print(f"Total attempts: {len(configs)}")
    successes = []
    with summary_path.open('w', encoding='utf-8') as summary_file:
        for idx, cfg in enumerate(configs, 1):
            print(f"[{idx}/{len(configs)}] ftdi_init={cfg.ftdi_init} baud={cfg.baud} line={cfg.line_ending} upper={cfg.uppercase} delay={cfg.delay_s} wake={cfg.wake}")
            result = attempt(cfg)
            line = asdict(result)
            summary_file.write(json.dumps(line) + "\n")
            if result.success:
                successes.append(result)
                # Write detailed file for successes
                detail_path = out_dir / f"success_{idx:03d}.json"
                with detail_path.open('w', encoding='utf-8') as f:
                    json.dump(line, f, indent=2)

    print(f"Successes: {len(successes)}")
    if successes:
        print("First success config:")
        print(successes[0].config)
    else:
        print("No payloads beyond status bytes were observed. Try installing the VCP driver or expanding heuristic.")

if __name__ == '__main__':
    main()
