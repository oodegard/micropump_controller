"""Minimal direct-serial control of Bartels mp-Labtronix Control Unit.

This bypasses any vendor DLL (FTDI D2XX) and uses plain CDC/Virtual COM via pyserial.
Tested assumptions (adjust if your hardware differs):
- Device enumerates as an FTDI VCP (VID:PID 0403:B4C0) and accepts simple ASCII commands
  terminated by carriage return ("\r").
- Commands (from existing code):
    F<freq>    : set frequency in Hz (e.g. F100)
    A<voltage> : set amplitude/voltage (e.g. A120)
    RECT       : set waveform (other options may exist e.g. SINE, TRAPEZ?)
    bon        : pump on
    boff       : pump off
  Each followed by "\r".
- Device does NOT (in current code) send back confirmations (silent protocol). If your unit
  actually replies (e.g. with OK or value echo) you can enable reading.

Usage:
    python -m device_control.pump_direct_example --port COM4 --freq 100 --voltage 120 --waveform RECT --run-seconds 5

Safety:
    Always start with low voltage/frequency recommended by the datasheet.

"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Optional

import serial
from serial import SerialException

DEFAULT_BAUD = 9600  # If 9600 fails try 115200; adjust below.
CR = "\r"

COMMAND_DELAY = 0.15  # seconds between configuration commands to allow processing


def open_port(port: str, baud: int, timeout: float = 2.0) -> serial.Serial:
    return serial.Serial(port=port, baudrate=baud, timeout=timeout)


def send(ser: serial.Serial, cmd: str, *, expect_response: bool = False, read_timeout: float = 0.3) -> Optional[str]:
    line = (cmd + CR).encode("ascii")
    ser.write(line)
    ser.flush()
    if expect_response:
        # Temporarily adjust timeout if needed
        prev = ser.timeout
        ser.timeout = read_timeout
        try:
            resp = ser.readline().decode("ascii", errors="ignore").strip() or None
        finally:
            ser.timeout = prev
        return resp
    return None


def configure_pump(ser: serial.Serial, *, freq: int, voltage: int, waveform: str):
    send(ser, f"F{freq}")
    time.sleep(COMMAND_DELAY)
    send(ser, f"A{voltage}")
    time.sleep(COMMAND_DELAY)
    send(ser, waveform.upper())
    time.sleep(COMMAND_DELAY)


def pump_on(ser: serial.Serial):
    send(ser, "bon")


def pump_off(ser: serial.Serial):
    send(ser, "boff")


def run_cycle(ser: serial.Serial, seconds: float):
    pump_on(ser)
    t0 = time.time()
    try:
        while time.time() - t0 < seconds:
            time.sleep(0.2)
    finally:
        pump_off(ser)


def detect_baud(port: str, candidates=(9600, 115200, 57600)) -> int:
    for b in candidates:
        try:
            with open_port(port, b, timeout=0.6) as ser:
                # Heuristic: send benign query if protocol had one. Lacking docs, just try a config echo.
                send(ser, "F100")
                return b
        except SerialException:
            continue
    raise SerialException(f"Unable to open {port} at common baud rates {candidates}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Direct Bartels pump control (no vendor driver)")
    p.add_argument("--port", required=True, help="Serial COM port, e.g. COM4")
    p.add_argument("--freq", type=int, default=100, help="Frequency (Hz)")
    p.add_argument("--voltage", type=int, default=120, help="Voltage / amplitude units as expected by device")
    p.add_argument("--waveform", default="RECT", help="Waveform label (RECT / SINE / etc)")
    p.add_argument("--run-seconds", type=float, default=3.0, help="Run duration for demo cycle")
    p.add_argument("--auto-baud", action="store_true", help="Attempt to auto-detect baud (tries 9600,115200,57600)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    baud = DEFAULT_BAUD
    if args.auto_baud:
        try:
            baud = detect_baud(args.port)
            print(f"[info] Auto-detected baud rate: {baud}")
        except SerialException as e:
            print(f"[warn] Auto-baud failed: {e}; using default {baud}")

    try:
        with open_port(args.port, baud) as ser:
            print(f"[info] Opened {args.port} @ {baud} baud")
            configure_pump(ser, freq=args.freq, voltage=args.voltage, waveform=args.waveform)
            print(f"[info] Configured: freq={args.freq} voltage={args.voltage} waveform={args.waveform.upper()}")
            print(f"[info] Running for {args.run_seconds} s ...")
            run_cycle(ser, args.run_seconds)
            print("[info] Done.")
    except SerialException as e:
        print(f"[error] Serial failure: {e}")
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
