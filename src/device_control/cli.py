
"""Command-line interface for running pump/valve sequences from a YAML file.

Usage examples (from project root):
    python -m device_control.cli config_examples/continuous_switching.yaml
    python src/device_control/cli.py config_examples/continuous_switching.yaml

Flags:
    --dry-run     Simulate; no serial ports opened (mock devices)
    --no-detect   Disable VID/PID auto-detection and rely only on .env/default ports

Port resolution order (when not --dry-run):
    1. Explicit environment: PUMP_PORT / VALVE_SERIAL_PORT (or legacy PUMP_COM)
    2. VID/PID detection via get_port_by_id('pump' / 'arduino') using .env IDs
    3. Fallback defaults: COM4 (pump), COM5 (valve)

The YAML format currently supported (see example file):
  pump settings:
    profile name:
      waveform: RECT
      voltage: 100
      freq: 50
  required hardware:
    pump: true
    valve: true
  run:
    - pump_on: profile name   (order applied: stop -> waveform -> voltage (Vpp) -> freq -> start)
    - duration: 120
      commands:
        - action: valve_on
          duration: 5
        - action: valve_off
          duration: 5
    - pump_off: 0
"""

from __future__ import annotations

# Ensure project root (two levels up from this file) is on sys.path when executed as a script
import os as _os, sys as _sys
_SRC_DIR = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
if _SRC_DIR not in _sys.path:
    _sys.path.insert(0, _SRC_DIR)

import argparse
import os
import sys
import time
from typing import Any, Dict, List

import yaml

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore

# Local imports (package-relative). Classes actually defined in pump/valve modules.
from device_control.pump import BartelsPumpController
from device_control.valve import ValveController
from device_control.resolve_ports import get_port_by_id


class MockPump:
    """Mock pump for --dry-run mode (logs actions only)."""
    def __init__(self, name: str = "MockPump"):
        self.name = name
        self.running = False

    def bartels_set_waveform(self, wf):
        print(f"[DRY-RUN][PUMP] set waveform={wf}")

    def bartels_set_voltage(self, v):
        print(f"[DRY-RUN][PUMP] set voltage(Vpp)={v}")

    def bartels_set_freq(self, f):
        print(f"[DRY-RUN][PUMP] set freq={f}")

    def bartels_start(self):
        self.running = True
        print("[DRY-RUN][PUMP] START")

    def bartels_stop(self):
        if self.running:
            print("[DRY-RUN][PUMP] STOP")
        self.running = False

    def close(self):
        print("[DRY-RUN][PUMP] CLOSE")


class MockValve:
    """Mock valve for --dry-run mode (logs actions only)."""
    def __init__(self, name: str = "MockValve"):
        self.name = name
        self.state_val = False

    def on(self):
        self.state_val = True
        print("[DRY-RUN][VALVE] ON")

    def off(self):
        self.state_val = False
        print("[DRY-RUN][VALVE] OFF")

    def close(self):
        print("[DRY-RUN][VALVE] CLOSE")


def load_yaml_config(path: str) -> Dict[str, Any]:
    """Load YAML configuration from file path."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        sys.exit(f"Config file not found: {path}")
    except yaml.YAMLError as e:
        sys.exit(f"YAML parse error in {path}: {e}")
    except Exception as e:  # pragma: no cover
        sys.exit(f"Unexpected error reading {path}: {e}")


def load_env_once():
    """Load project .env file if present (idempotent)."""
    if not load_dotenv:
        return
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    env_path = os.path.join(root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)  # ignore return


def resolve_ports_from_env(prefer_detection: bool = True) -> dict:
    """Determine ports using layered strategy:
    1. Explicit env overrides (PUMP_PORT / VALVE_SERIAL_PORT)
    2. VID/PID detection via get_port_by_id('pump'/'arduino') when available
    3. Fallback defaults (COM4 / COM5)
    """
    load_env_once()
    pump_port_env = os.getenv("PUMP_PORT") or os.getenv("PUMP_COM")
    valve_port_env = os.getenv("VALVE_SERIAL_PORT")

    detected_pump = None
    detected_valve = None
    if prefer_detection:
        # Attempt detection; suppress exceptions and fall back
        try:
            detected_pump = get_port_by_id("pump")
        except Exception:
            detected_pump = None
        try:
            detected_valve = get_port_by_id("arduino")
        except Exception:
            detected_valve = None

    pump_port = pump_port_env or detected_pump or "COM4"
    valve_port = valve_port_env or detected_valve or "COM5"

    return {
        "pump_port": pump_port,
        "valve_port": valve_port,
        "valve_baud": int(os.getenv("VALVE_BAUDRATE", "115200")),
        "pump_detected": bool(detected_pump),
        "valve_detected": bool(detected_valve),
        "pump_from_env": bool(pump_port_env is not None),
        "valve_from_env": bool(valve_port_env is not None),
    }


def apply_pump_profile(pump, name: str, profiles: Dict[str, Any], *, start: bool = True):  # pump can be real or mock
    """Apply pump profile with correct ordering (stop -> waveform -> voltage -> frequency -> start)."""
    profile = profiles.get(name)
    if not profile:
        sys.exit(
            f"Pump profile '{name}' not found in 'pump settings'. Available: {list(profiles.keys())}"
        )
    # Always stop first to avoid abrupt changes while running
    try:
        pump.bartels_stop()
    except Exception:
        pass  # ignore if already stopped
    # Order important for hardware safety
    waveform = profile.get("waveform")
    voltage = profile.get("voltage")
    freq = profile.get("freq")
    if waveform is not None:
        pump.bartels_set_waveform(waveform)
        time.sleep(0.05)
    if voltage is not None:
        pump.bartels_set_voltage(voltage)
        time.sleep(0.05)
    if freq is not None:
        pump.bartels_set_freq(freq)
        time.sleep(0.05)
    if start:
        pump.bartels_start()


def run_sequence(
    config: Dict[str, Any],
    pump,
    valve,
    pump_profiles: Dict[str, Any],
    *,
    dry_run: bool = False,
):
    for step in config.get("run", []):
        if not isinstance(step, dict):
            print(f"[WARN] Step ignored (not a dict): {step}")
            continue
        # Pump ON (apply profile)
        if "pump_on" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            profile_name = step["pump_on"]
            # Modified behavior: mimic test_pump_cycle.py where we simply start the pump
            # without re-applying waveform/voltage/frequency each time. We keep the
            # profile name for logging only (initial settings were applied at controller init).
            print(f"[ACTION] Pump START (profile '{profile_name}' – using initial configured settings)")
            try:
                pump.bartels_start()
            except Exception as e:
                print(f"[WARN] Failed to start pump: {e}")
            continue
        # Pump OFF
        if "pump_off" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            print("[ACTION] Pump OFF")
            try:
                pump.bartels_stop()
            except Exception as e:
                print(f"[WARN] Could not stop pump cleanly: {e}")
            continue
        # Timed command block
        if "duration" in step and "commands" in step:
            total = float(step.get("duration", 0))
            commands: List[dict] = step.get("commands", [])
            print(f"[BLOCK] {total}s repeating {len(commands)} commands")
            block_start = time.time()
            while (time.time() - block_start) < total:
                for cmd in commands:
                    remaining = total - (time.time() - block_start)
                    if remaining <= 0:
                        break
                    action = cmd.get("action")
                    segment = float(cmd.get("duration", 0))
                    if action == "valve_on":
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        print(f"  [VALVE] ON for {segment}s")
                        valve.on()
                        time.sleep(segment)
                    elif action == "valve_off":
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        print(f"  [VALVE] OFF for {segment}s")
                        valve.off()
                        time.sleep(segment)
                    else:
                        print(f"  [WARN] Unknown action '{action}' in block")
            continue
        # Simple wait
        if list(step.keys()) == ["duration"]:
            wait_s = float(step["duration"]) or 0.0
            print(f"[WAIT] {wait_s}s")
            time.sleep(wait_s)
            continue
        print(f"[WARN] Unrecognized step keys: {list(step.keys())}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run micropump/valve sequence from a YAML config file.")
    p.add_argument("yaml_file", help="Path to YAML configuration file")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging (currently basic prints)")
    p.add_argument("--dry-run", action="store_true", help="Simulate actions without opening serial ports")
    p.add_argument(
        "--no-detect", action="store_true", help="Disable VID/PID auto-detection; rely only on env/default"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = load_yaml_config(args.yaml_file)
    required_hw = config.get("required hardware", {})
    if not required_hw:
        print("No 'required hardware' section found in YAML file. Aborting.")
        return 1

    pump_enabled = bool(required_hw.get("pump", False))
    valve_enabled = bool(required_hw.get("valve", False))
    dry_run = args.dry_run

    env_ports = resolve_ports_from_env(prefer_detection=not args.no_detect) if not dry_run else {}

    pump_profiles = config.get("pump settings", {}) if pump_enabled else {}
    if pump_enabled and not pump_profiles:
        print("Pump enabled but no 'pump settings' found in YAML file.")
        return 1

    # Initialize devices (real or mock)
    pump = None
    if pump_enabled:
        if dry_run:
            pump = MockPump()
        else:
            first_profile = next(iter(pump_profiles.values()))
            pump_cfg = {
                "pump_port": env_ports["pump_port"],
                "bartels_freq": first_profile.get("freq", 50),
                "bartels_voltage": first_profile.get("voltage", 100),
            }
            print(
                f"[INFO] Pump port resolved: {pump_cfg['pump_port']} "
                f"(env={env_ports.get('pump_from_env')}, detected={env_ports.get('pump_detected')})"
            )
            try:
                pump = BartelsPumpController(pump_cfg)
            except Exception as e:  # pragma: no cover
                print(f"Failed to initialize pump: {e}")
                return 1
            # Fail-fast if underlying serial handle missing
            if getattr(pump, 'pump', None) is None:
                print(
                    "ERROR: Pump serial connection not established. "
                    "Check wiring, drivers, or override with PUMP_PORT in .env."
                )
                return 1
            # Allow device settle
            time.sleep(0.3)

    valve = None
    if valve_enabled:
        if dry_run:
            valve = MockValve()
        else:
            try:
                print(
                    f"[INFO] Valve port resolved: {env_ports['valve_port']} "
                    f"(env={env_ports.get('valve_from_env')}, detected={env_ports.get('valve_detected')})"
                )
                valve = ValveController(env_ports["valve_port"], env_ports["valve_baud"])
            except Exception as e:  # pragma: no cover
                print(f"Failed to initialize valve: {e}")
                return 1

    try:
        run_sequence(config, pump, valve, pump_profiles, dry_run=dry_run)
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Caught Ctrl+C – shutting down devices...")
        try:
            if pump:
                pump.bartels_stop()
        except Exception:
            pass
        try:
            if valve:
                valve.off()
        except Exception:
            pass
    finally:
        if pump:
            try:
                pump.close()
            except Exception:
                pass
        if valve:
            try:
                valve.close()
            except Exception:
                pass
    print("Sequence complete.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
