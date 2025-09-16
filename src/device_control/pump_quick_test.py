"""Quick functional test for Bartels micropump control unit.

Features:
  * Auto-detect COM port by (in priority order):
        1. .env-defined PUMP_VID / PUMP_PID
        2. FTDI known VID:PID 0403:B4C0
        3. Description substring match: 'micropump', 'bartels'
  * Auto-try baud rates (default list: 9600, 115200, 57600) stopping at first success.
  * Configure frequency, voltage, waveform; turn pump on for a short interval, then off.
  * Clear, colored(ish) textual status (no external deps; simple tags).

Assumptions:
  * Protocol: ASCII commands terminated with \r.
  * No response required; script only verifies that port opens & write succeeds.

Usage (PowerShell):
  python -m device_control.pump_quick_test
  python -m device_control.pump_quick_test --freq 120 --voltage 150 --seconds 8

Override port manually:
  python -m device_control.pump_quick_test --port COM7

Exit codes:
  0 success; 1 no port; 2 open/write error.

"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable, Optional, Sequence

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # Optional dependency
    def load_dotenv(*_a, **_k):  # type: ignore
        return False

import serial
from serial import SerialException
from serial.tools import list_ports  # type: ignore

DEFAULT_BAUD_CANDIDATES: Sequence[int] = (9600, 115200, 57600)
DEFAULT_FREQ = 100
DEFAULT_VOLTAGE = 120
DEFAULT_WAVEFORM = "RECT"
CR = "\r"

# Known FTDI IDs for Bartels unit (observed in repo notes)
KNOWN_VID = 0x0403
KNOWN_PID = 0xB4C0


def log(msg: str):
    print(msg, flush=True)


def detect_port(env_vid: Optional[int], env_pid: Optional[int]) -> Optional[str]:
    ports = list_ports.comports()

    # 1. .env exact match
    if env_vid is not None and env_pid is not None:
        for p in ports:
            if p.vid == env_vid and p.pid == env_pid:
                log(f"[info] Found port via .env VID:PID {env_vid:04X}:{env_pid:04X} -> {p.device}")
                return p.device

    # 2. Known VID/PID fallback
    for p in ports:
        if p.vid == KNOWN_VID and p.pid == KNOWN_PID:
            log(f"[info] Found port via known VID:PID {KNOWN_VID:04X}:{KNOWN_PID:04X} -> {p.device}")
            return p.device

    # 3. Description contains keywords
    KEYWORDS = ("micropump", "bartels")
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in KEYWORDS):
            log(f"[info] Found port via description match '{p.description}' -> {p.device}")
            return p.device

    return None


def try_baud(port: str, baud: int) -> bool:
    try:
        with serial.Serial(port=port, baudrate=baud, timeout=1) as ser:
            # Send a harmless param set; success == no exception
            ser.write(b"F100" + CR.encode())
            ser.flush()
            return True
    except SerialException:
        return False


def select_baud(port: str, candidates: Iterable[int]) -> Optional[int]:
    for b in candidates:
        if try_baud(port, b):
            log(f"[info] Selected baud {b}")
            return b
    return None


def send(ser: serial.Serial, cmd: str):
    ser.write((cmd + CR).encode("ascii"))
    ser.flush()


def run_cycle(ser: serial.Serial, seconds: float, freq: int, voltage: int, waveform: str):
    # Configure
    send(ser, f"F{freq}")
    time.sleep(0.15)
    send(ser, f"A{voltage}")
    time.sleep(0.15)
    send(ser, waveform.upper())
    time.sleep(0.15)

    log(f"[info] Configured (freq={freq}, voltage={voltage}, waveform={waveform.upper()})")

    # On
    send(ser, "bon")
    log(f"[info] Pump ON for {seconds:.1f}s ...")
    t0 = time.time()
    while time.time() - t0 < seconds:
        time.sleep(0.25)
    # Off
    send(ser, "boff")
    log("[info] Pump OFF")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Quick Bartels pump functional test")
    ap.add_argument("--port", help="Explicit COM port (skip auto-detect)")
    ap.add_argument("--freq", type=int, default=DEFAULT_FREQ, help="Frequency (Hz)")
    ap.add_argument("--voltage", type=int, default=DEFAULT_VOLTAGE, help="Voltage units expected by device")
    ap.add_argument("--waveform", default=DEFAULT_WAVEFORM, help="Waveform label (RECT/SINE/etc)")
    ap.add_argument("--seconds", type=float, default=3.0, help="ON duration for test")
    ap.add_argument("--baud", type=int, help="Force a single baud rate")
    ap.add_argument("--baud-candidates", nargs="*", type=int, default=list(DEFAULT_BAUD_CANDIDATES), help="List of baud rates to try if auto-selecting")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    # Load .env if present
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    load_dotenv(os.path.join(repo_root, ".env"))
    env_vid = os.getenv("PUMP_VID")
    env_pid = os.getenv("PUMP_PID")
    env_vid_i = int(env_vid, 0) if env_vid else None
    env_pid_i = int(env_pid, 0) if env_pid else None

    port = args.port or detect_port(env_vid_i, env_pid_i)
    if not port:
        log("[error] Could not auto-detect pump port. Provide --port COMx")
        return 1

    if args.baud:
        baud = args.baud
        log(f"[info] Using forced baud {baud}")
    else:
        baud = select_baud(port, args.baud_candidates)
        if baud is None:
            log(f"[error] Could not open {port} at any candidate baud {args.baud_candidates}")
            return 2

    try:
        with serial.Serial(port=port, baudrate=baud, timeout=2) as ser:
            log(f"[info] Opened {port} @ {baud} baud")
            run_cycle(ser, args.seconds, args.freq, args.voltage, args.waveform)
            log("[success] Test cycle complete.")
            return 0
    except SerialException as e:
        log(f"[error] Serial failure: {e}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
