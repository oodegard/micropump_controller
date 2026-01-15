
"""
# THIS HAS NOT BEEN UPDATED SINCE REFACTORING TO WINDOES VS WSL - IS OUTDATED
# AND MAY REQUIRE ADJUSTMENTS TO WORK PROPERLY.


Command-line interface for running pump/valve sequences from a YAML file.

Usage examples (from project root):
    python run_protocol_cli.py config_examples/continuous_switching.yaml
    uv run python run_protocol_cli.py config_examples/continuous_switching.yaml

Flags:
    --dry-run     Simulate; no serial ports opened (mock devices)
    --no-detect   Disable VID/PID auto-detection and rely only on .env/default ports

Port resolution order (when not --dry-run):
    1. Explicit environment: PUMP_PORT / VALVE_SERIAL_PORT (or legacy PUMP_COM)
    2. VID/PID detection via get_port_by_id('pump' / 'arduino') using .env IDs
    3. Fallback defaults: COM4 (pump), COM5 (valve)

The YAML format currently supported (see example file) plus extended single-step
commands:

    pump settings:
        profile name:
            waveform: RECT
            voltage: 100     # Vpp
            freq: 50         # Hz

    required hardware:
        pump: true
        valve: true

    run:
        # Original style (profile application + start). Now simplified to a mere start
        # because initial configuration is applied during controller init.
        - pump_on: profile name
        - wait: 5
        - pump_off: 0

        # New granular pump commands (can be mixed):
        - pump_waveform: RECT      # sets waveform only
        - pump_voltage: 90         # sets voltage (Vpp) only
        - pump_freq: 120           # sets frequency only
        - pump_start: 0            # start (alias to bartels_start)
        - pump_stop: 0             # stop (alias to bartels_stop)
        - pump_cycle: 3            # start, wait N seconds, stop

        # Valve commands:
        - valve_on: 0
        - valve_off: 0
        - valve_toggle: 0
        - valve_state: 0           # queries and prints state
        - valve_pulse: 0.15        # pulse N seconds (emulated: ON, wait, OFF)

        # Mixed timed block (unchanged semantics):
        - wait: 20
            commands:
                - action: valve_on
                    wait: 2
                - action: valve_off
                    wait: 2

        # Simple wait:
        - wait: 10
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
import signal
import serial
import serial.tools.list_ports
from typing import Any, Dict, List

import yaml

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore

# Local imports - simplified structure with single files per device
from src.pump_win import Pump_win
from src.pump_wsl import Pump_wsl
from src.dual_valve import DualValveController
from src.messagebox import MessageBox


class MockPump:
    """Mock pump for --dry-run mode (logs actions only)."""
    def __init__(self, name: str = "MockPump"):
        self.name = name
        self.running = False

    def set_waveform(self, wf):
        print(f"[DRY-RUN][PUMP] set waveform={wf}")

    def set_voltage(self, v):
        print(f"[DRY-RUN][PUMP] set voltage(Vpp)={v}")

    def set_frequency(self, f):
        print(f"[DRY-RUN][PUMP] set freq={f}")

    def start(self):
        self.running = True
        print("[DRY-RUN][PUMP] START")

    def stop(self):
        if self.running:
            print("[DRY-RUN][PUMP] STOP")
        self.running = False

    def close(self):
        print("[DRY-RUN][PUMP] CLOSE")

    # Legacy method names for compatibility
    def bartels_set_waveform(self, wf):
        self.set_waveform(wf)

    def bartels_set_voltage(self, v):
        self.set_voltage(v)

    def bartels_set_freq(self, f):
        self.set_frequency(f)

    def bartels_start(self):
        self.start()

    def bartels_stop(self):
        self.stop()


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


# Global flag used to indicate a user-requested stop (Ctrl+C)
STOP_REQUESTED = False


def _handle_sigint(signum, frame) -> None:
    """Signal handler for SIGINT (Ctrl+C). Set STOP_REQUESTED so loops can exit cleanly."""
    global STOP_REQUESTED
    if not STOP_REQUESTED:
        print("\n[INTERRUPT] SIGINT received - requesting shutdown...")
    STOP_REQUESTED = True


def _setup_signal_handlers() -> None:
    """Register signal handler(s) for graceful shutdown on Ctrl+C."""
    try:
        signal.signal(signal.SIGINT, _handle_sigint)
    except Exception:
        # Some environments may not support signals in the same way; ignore if registration fails
        pass


def interruptible_sleep(total: float, tick: float = 0.1) -> None:
    """Sleep in small increments and abort early if STOP_REQUESTED is set.

    Raises KeyboardInterrupt if a stop was requested so callers can handle it like a true
    interrupt.
    """
    global STOP_REQUESTED
    end = time.time() + float(total or 0)
    while time.time() < end:
        if STOP_REQUESTED:
            # Convert to KeyboardInterrupt so existing handlers work as expected
            raise KeyboardInterrupt()
        remaining = end - time.time()
        time.sleep(min(tick, max(0.0, remaining)))
    # final check
    if STOP_REQUESTED:
        raise KeyboardInterrupt()


def resolve_ports_from_env(prefer_detection: bool = True) -> dict:
    """Determine ports using layered strategy:
    1. Explicit env overrides (PUMP_PORT / VALVE_SERIAL_PORT / VALVE_PORT)
    2. VID/PID detection via ARDUINO_VID/ARDUINO_PID from .env
    3. Description-based detection (Arduino keywords)
    4. Fallback defaults (COM4 / COM5)
    """
    load_env_once()
    pump_port_env = os.getenv("PUMP_PORT") or os.getenv("PUMP_COM")
    valve_port_env = os.getenv("VALVE_SERIAL_PORT") or os.getenv("VALVE_PORT")

    detected_pump = None
    detected_valve = None

    # Try VID/PID-based detection for valve (Arduino)
    if not valve_port_env:
        try:
            arduino_vid = int(os.getenv("ARDUINO_VID", "0"))
            arduino_pid = int(os.getenv("ARDUINO_PID", "0"))
            if arduino_vid > 0 and arduino_pid > 0:
                detected_valve = _find_port_by_vid_pid(arduino_vid, arduino_pid)
        except (ValueError, Exception):
            pass

        # Fallback to description-based detection if VID/PID didn't work
        if not detected_valve:
            arduino_keywords = ["arduino", "ch340", "wchusbserial", "silicon labs", "cp210x"]
            for keyword in arduino_keywords:
                try:
                    detected_valve = _find_port_by_description(keyword)
                    if detected_valve:
                        break
                except Exception:
                    continue

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


def _find_port_by_vid_pid(vid: int, pid: int) -> str:
    """Find serial port by VID/PID; raises Exception if not found."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return port.device
    raise Exception(f"No device found with VID={vid:04X} and PID={pid:04X}")


def _find_port_by_description(keyword: str) -> str:
    """Find serial port by keyword in description; raises Exception if not found."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if keyword.lower() in port.description.lower():
            return port.device
    raise Exception(f"No device found with keyword '{keyword}' in description")


def apply_pump_profile(pump, name: str, profiles: Dict[str, Any], *, start: bool = True):  # pump can be real or mock
    """Apply pump profile with correct ordering (stop -> waveform -> voltage -> frequency -> start)."""
    profile = profiles.get(name)
    if not profile:
        sys.exit(
            f"Pump profile '{name}' not found in 'pump settings'. Available: {list(profiles.keys())}"
        )
    # Always stop first to avoid abrupt changes while running
    try:
        pump.stop()
    except Exception:
        pass  # ignore if already stopped
    # Order important for hardware safety
    waveform = profile.get("waveform")
    voltage = profile.get("voltage")
    freq = profile.get("freq")
    if waveform is not None:
        pump.set_waveform(waveform)
        interruptible_sleep(0.05)
    if voltage is not None:
        pump.set_voltage(voltage)
        interruptible_sleep(0.05)
    if freq is not None:
        pump.set_frequency(freq)
        interruptible_sleep(0.05)
    if start:
        pump.start()


def run_sequence(
    config: Dict[str, Any],
    pump,
    valve,
    pump_profiles: Dict[str, Any],
    *,
    microscope=None,
    dry_run: bool = False,
):
    global STOP_REQUESTED
    for idx, step in enumerate(config.get("run", [])):
        # Check for interrupt at the start of each step
        if STOP_REQUESTED:
            print(f"\n[INTERRUPT] Stop requested before step {idx+1} - aborting sequence")
            raise KeyboardInterrupt()
        
        if not isinstance(step, dict):
            print(f"[WARN] Step ignored (not a dict): {step}")
            continue
        print(f"[STEP {idx+1}] Executing: {step}")
        # Pump ON (apply profile)
        if "pump_on" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            profile_name = step["pump_on"]
            
            # Apply profile settings
            if profile_name not in pump_profiles:
                print(f"[WARN] Profile '{profile_name}' not found in pump settings")
                continue
            
            profile = pump_profiles[profile_name]
            print(f"[ACTION] Applying profile '{profile_name}': {profile}")
            
            # Apply waveform
            if "waveform" in profile:
                waveform = profile["waveform"]
                try:
                    pump.set_waveform(waveform)
                    print(f"  ✓ Waveform: {waveform}")
                except Exception as e:
                    print(f"  [WARN] Failed to set waveform: {e}")
            
            # Apply voltage
            if "voltage" in profile:
                voltage = profile["voltage"]
                try:
                    pump.set_voltage(voltage)
                    print(f"  ✓ Voltage: {voltage} Vpp")
                except Exception as e:
                    print(f"  [WARN] Failed to set voltage: {e}")
            
            # Apply frequency
            if "freq" in profile:
                freq = profile["freq"]
                try:
                    pump.set_frequency(freq)
                    print(f"  ✓ Frequency: {freq} Hz")
                except Exception as e:
                    print(f"  [WARN] Failed to set frequency: {e}")
            
            # Start the pump
            print(f"[ACTION] Pump START")
            try:
                pump.start()
            except Exception as e:
                print(f"[WARN] Failed to start pump: {e}")
            continue
        # Granular pump commands
        if "pump_start" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            print("[ACTION] Pump START")
            try:
                pump.start()
            except Exception as e:
                print(f"[WARN] Failed to start pump: {e}")
            continue
        if "pump_stop" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            print("[ACTION] Pump STOP")
            try:
                pump.stop()
            except Exception as e:
                print(f"[WARN] Failed to stop pump: {e}")
            continue
        if "pump_voltage" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            val = step["pump_voltage"]
            print(f"[ACTION] Set pump voltage -> {val}")
            try:
                pump.set_voltage(val)
            except Exception as e:
                print(f"[WARN] Failed to set voltage: {e}")
            continue
        if "pump_freq" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            val = step["pump_freq"]
            print(f"[ACTION] Set pump frequency -> {val}")
            try:
                pump.set_frequency(val)
            except Exception as e:
                print(f"[WARN] Failed to set frequency: {e}")
            continue
        if "pump_waveform" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            val = step["pump_waveform"]
            print(f"[ACTION] Set pump waveform -> {val}")
            try:
                pump.set_waveform(val)
            except Exception as e:
                print(f"[WARN] Failed to set waveform: {e}")
            continue
        if "pump_cycle" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            duration = float(step["pump_cycle"]) or 0.0
            print(f"[ACTION] Pump cycle for {duration}s")
            try:
                pump.start()
                interruptible_sleep(duration)
                pump.stop()
            except Exception as e:
                print(f"[WARN] Pump cycle error: {e}")
            continue
        # Pump OFF
        if "pump_off" in step:
            if not pump:
                sys.exit("Pump requested but not initialized.")
            print("[ACTION] Pump OFF")
            try:
                pump.stop()
            except Exception as e:
                print(f"[WARN] Could not stop pump cleanly: {e}")
            continue
        # Solenoid valve commands (Buffer selector - pin 7)
        if "valve_on" in step or "solenoid_on" in step:
            if not valve:
                sys.exit("Valve requested but not initialized.")
            print("[ACTION] Solenoid Valve ON (Buffer B)")
            try:
                resp = valve.solenoid_on()
                if resp:
                    print(f"  [VALVE RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to set solenoid valve ON: {e}")
            continue
        if "valve_off" in step or "solenoid_off" in step:
            if not valve:
                sys.exit("Valve requested but not initialized.")
            print("[ACTION] Solenoid Valve OFF (Buffer A)")
            try:
                resp = valve.solenoid_off()
                if resp:
                    print(f"  [VALVE RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to set solenoid valve OFF: {e}")
            continue
        if "valve_toggle" in step or "solenoid_toggle" in step:
            if not valve:
                sys.exit("Valve requested but not initialized.")
            print("[ACTION] Solenoid Valve TOGGLE")
            try:
                resp = valve.solenoid_toggle()
                if resp:
                    print(f"  [SOLENOID RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to toggle solenoid valve: {e}")
            continue
        if "valve_state" in step or "solenoid_state" in step:
            if not valve:
                sys.exit("Valve requested but not initialized.")
            print("[ACTION] Solenoid Valve STATE?")
            try:
                resp = valve.solenoid_state()
                if resp:
                    print(f"  [SOLENOID STATE] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to read solenoid valve state: {e}")
            continue
        
        # Pinch valve commands (Flow gate - pin 9)
        if "pinch_valve_on" in step or "pinch_on" in step:
            if not valve:
                sys.exit("Pinch valve requested but not initialized.")
            print("[ACTION] Pinch Valve ON (Enable flow)")
            try:
                resp = valve.pinch_on()
                if resp:
                    print(f"  [PINCH RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to set pinch valve ON: {e}")
            continue
        if "pinch_valve_off" in step or "pinch_off" in step:
            if not valve:
                sys.exit("Pinch valve requested but not initialized.")
            print("[ACTION] Pinch Valve OFF (Block flow)")
            try:
                resp = valve.pinch_off()
                if resp:
                    print(f"  [PINCH RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to set pinch valve OFF: {e}")
            continue
        if "pinch_valve_toggle" in step or "pinch_toggle" in step:
            if not valve:
                sys.exit("Pinch valve requested but not initialized.")
            print("[ACTION] Pinch Valve TOGGLE")
            try:
                resp = valve.pinch_toggle()
                if resp:
                    print(f"  [PINCH RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to toggle pinch valve: {e}")
            continue
        if "pinch_valve_state" in step or "pinch_state" in step:
            if not valve:
                sys.exit("Pinch valve requested but not initialized.")
            print("[ACTION] Pinch Valve STATE?")
            try:
                resp = valve.pinch_state()
                if resp:
                    print(f"  [PINCH STATE] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to read pinch valve state: {e}")
            continue
        if "pinch_valve_pulse" in step or "pinch_pulse" in step:
            if not valve:
                sys.exit("Pinch valve requested but not initialized.")
            seconds = float(step.get("pinch_valve_pulse", step.get("pinch_pulse", 0)))
            print(f"[ACTION] Pinch Valve PULSE {seconds}s (emulated)")
            try:
                valve.pinch_on()
                time.sleep(seconds)
                resp = valve.pinch_off()
                if resp:
                    print(f"  [PINCH RESP] {resp}")
            except Exception as e:
                print(f"[WARN] Failed to pulse pinch valve: {e}")
            continue
        # Timed command block
        if ("wait" in step or "duration" in step) and "commands" in step:
            total = float(step.get("wait", step.get("duration", 0)))
            commands: List[dict] = step.get("commands", [])
            print(f"[BLOCK] {total}s repeating {len(commands)} commands")
            block_start = time.time()
            block_count = 0
            while (time.time() - block_start) < total:
                for cmd in commands:
                    remaining = total - (time.time() - block_start)
                    if remaining <= 0:
                        break
                    action = cmd.get("action")
                    segment = float(cmd.get("wait", cmd.get("duration", 0)))
                    block_count += 1
                    print(f"    [BLOCK STEP {block_count}] {action} for {segment}s (remaining: {remaining:.1f}s)")
                    if action == "valve_on":
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        valve.on()
                        print(f"      [VALVE] ON command sent.")
                        interruptible_sleep(segment)
                    elif action == "valve_off":
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        valve.off()
                        print(f"      [VALVE] OFF command sent.")
                        interruptible_sleep(segment)
                    else:
                        print(f"      [WARN] Unknown action '{action}' in block")
            print(f"[BLOCK] Completed after {time.time() - block_start:.1f}s.")
            continue
        # Simple wait
        if list(step.keys()) == ["wait"] or list(step.keys()) == ["duration"]:
            wait_s = float(step.get("wait", step.get("duration", 0))) or 0.0
            print(f"[WAIT] {wait_s}s")
            interruptible_sleep(wait_s)
            continue
        
        # New: Standalone wait command
        if "wait" in step:
            wait_s = float(step["wait"]) or 0.0
            print(f"[WAIT] {wait_s}s")
            interruptible_sleep(wait_s)
            continue
        
        # New: Message box (blocks until user clicks OK)
        if "okbutton" in step:
            message = step["okbutton"]
            title = step.get("okbutton_title", "OK")
            print(f"[ACTION] Show message box: {message}")
            MessageBox.show_ok(message, title)
            print(f"[ACTION] User pressed OK, continuing...")
            continue
        
        # New: Loop command with repeat count
        if "loop" in step:
            loop_data = step["loop"]
            repeat = loop_data.get("repeat", 1)
            steps = loop_data.get("steps", [])
            wells = loop_data.get("wells")
            
            if wells:
                # Wells generator mode (not yet implemented)
                print(f"[LOOP] Wells generator mode not yet implemented: {wells}")
                continue
            
            print(f"[LOOP] Repeating {len(steps)} steps {repeat} times")
            for iteration in range(repeat):
                # Check for interrupt at the start of each loop iteration
                if STOP_REQUESTED:
                    print(f"\n[INTERRUPT] Stop requested during loop iteration {iteration+1}/{repeat} - aborting loop")
                    raise KeyboardInterrupt()
                
                print(f"  [LOOP ITERATION {iteration + 1}/{repeat}]")
                for substep in steps:
                    # Check for interrupt between each substep
                    if STOP_REQUESTED:
                        print(f"\n[INTERRUPT] Stop requested during loop substep - aborting loop")
                        raise KeyboardInterrupt()
                    
                    if not isinstance(substep, dict):
                        continue
                    
                    # Handle valve_on with duration syntax: valve_on: 2
                    if "valve_on" in substep:
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        duration = float(substep["valve_on"]) if isinstance(substep["valve_on"], (int, float)) else 0
                        if duration > 0:
                            print(f"    [VALVE] ON for {duration}s")
                            valve.on()
                            interruptible_sleep(duration)
                        else:
                            print(f"    [VALVE] ON")
                            valve.on()
                        continue
                    
                    # Handle valve_off with duration syntax: valve_off: 0
                    if "valve_off" in substep:
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        duration = float(substep["valve_off"]) if isinstance(substep["valve_off"], (int, float)) else 0
                        print(f"    [VALVE] OFF")
                        valve.off()
                        if duration > 0:
                            interruptible_sleep(duration)
                        continue
                    
                    # Handle valve_toggle
                    if "valve_toggle" in substep:
                        if not valve:
                            sys.exit("Valve requested but not initialized.")
                        print(f"    [VALVE] TOGGLE")
                        try:
                            resp = valve.toggle()
                            if resp:
                                print(f"      [VALVE RESP] {resp}")
                        except Exception as e:
                            print(f"      [WARN] Failed to toggle valve: {e}")
                        continue
                    
                    # Handle wait in loop
                    if "wait" in substep:
                        wait_s = float(substep["wait"])
                        print(f"    [WAIT] {wait_s}s")
                        time.sleep(wait_s)
                        continue
                    
                    # Handle pump commands in loop
                    if "pump_on" in substep:
                        if not pump:
                            sys.exit("Pump requested but not initialized.")
                        profile_name = substep["pump_on"]
                        print(f"    [PUMP] START (profile '{profile_name}')")
                        try:
                            apply_pump_profile(pump, profile_name, pump_profiles, start=True)
                        except Exception as e:
                            print(f"      [WARN] Failed to start pump: {e}")
                        continue
                    
                    if "pump_off" in substep:
                        if not pump:
                            sys.exit("Pump requested but not initialized.")
                        print(f"    [PUMP] STOP")
                        try:
                            pump.stop()
                        except Exception as e:
                            print(f"      [WARN] Failed to stop pump: {e}")
                        continue
                    
                    # Handle move command (placeholder for future stage3d integration)
                    if "move" in substep:
                        position = substep["move"]
                        print(f"    [MOVE] to position '{position}' (stage3d not yet implemented)")
                        continue
                    
                    # Handle image command (placeholder for future microscope integration)
                    if "image" in substep:
                        image_id = substep["image"]
                        print(f"    [IMAGE] capture {image_id} (microscope not yet implemented)")
                        continue
                    
                    # Handle microscope acquire command
                    if "microscope_acquire" in substep:
                        if not microscope:
                            print("    [WARN] Microscope requested but not initialized")
                            continue
                        print(f"    [MICROSCOPE] Triggering image acquisition...")
                        success = microscope.acquire()
                        if success:
                            print(f"    [MICROSCOPE] ✓ Acquisition completed successfully")
                        else:
                            print(f"    [MICROSCOPE] ✗ Acquisition failed or timed out")
                        continue
                    
                    # Handle microscope command (generic button click)
                    if "microscope" in substep:
                        if not microscope:
                            print("    [ERROR] Microscope requested but not initialized")
                            print("[ABORT] Cannot continue without microscope - stopping protocol")
                            raise RuntimeError("Microscope not initialized")
                        action = substep["microscope"]
                        confidence = substep.get("confidence")
                        timeout = substep.get("timeout")
                        wait_complete = substep.get("wait_complete", True)
                        print(f"    [DEBUG] substep={substep}, action={action}, confidence={confidence}")
                        print(f"    [MICROSCOPE] Finding and clicking button: {action}")
                        success = microscope.run(image_path=action, confidence=confidence, timeout=timeout, wait_complete=wait_complete)
                        if success:
                            print(f"    [MICROSCOPE] [OK] Button '{action}' clicked")
                        else:
                            error_msg = microscope.get_error_details()
                            print(f"    [MICROSCOPE] [FAIL] Button '{action}' not found or click failed: {error_msg}")
                            
                            # If wait_complete is False, we're running async - just warn and continue
                            if not wait_complete:
                                print("    [WARN] Microscope operation failed, but continuing protocol since wait_complete=false")
                            else:
                                # Critical failure - can't proceed without microscope
                                print("[ABORT] Cannot continue without image acquisition - stopping protocol")
                                raise RuntimeError(f"Microscope button click failed: {error_msg}")
                        continue
            
            print(f"[LOOP] Completed")
            continue
        
        # New: Move command (placeholder for future stage3d integration)
        if "move" in step:
            position = step["move"]
            print(f"[MOVE] to position '{position}' (stage3d not yet implemented)")
            continue
        
        # New: Image command (placeholder for future microscope integration)
        if "image" in step:
            image_id = step["image"]
            print(f"[IMAGE] capture {image_id} (microscope not yet implemented)")
            continue
        
        # Microscope run command
        if "microscope" in step:
            if not microscope:
                print("[WARN] Microscope requested but not initialized")
                continue
            
            action = step["microscope"]
            if action in ("run", "start"):
                print(f"[MICROSCOPE] Clicking Run button...")
                success = microscope.run()
                if success:
                    print(f"[MICROSCOPE] ✓ Run command sent")
                else:
                    print(f"[MICROSCOPE] ✗ Command failed: {microscope.get_error_details()}")
            elif action == "wait_done":
                print(f"[MICROSCOPE] Waiting for acquisition to complete...")
                timeout = step.get("wait", step.get("duration", 300.0))
                success = microscope.wait_done(timeout=timeout)
                if success:
                    print(f"[MICROSCOPE] ✓ Acquisition finished")
                else:
                    print(f"[MICROSCOPE] ✗ Timeout or error")
            elif action == "screenshot":
                print(f"[MICROSCOPE] Capturing screenshot...")
                success = microscope.take_screenshot()
                if success:
                    print(f"[MICROSCOPE] ✓ Screenshot saved to shared folder")
                else:
                    print(f"[MICROSCOPE] ✗ Screenshot failed")
            else:
                # Treat any other value as a button name to click
                confidence = step.get("confidence")
                timeout = step.get("timeout")
                wait_complete = step.get("wait_complete", True)
                print(f"[MICROSCOPE] Finding and clicking button: {action}")
                success = microscope.run(image_path=action, confidence=confidence, timeout=timeout, wait_complete=wait_complete)
                if success:
                    print(f"[MICROSCOPE] [OK] Button '{action}' clicked")
                else:
                    error_msg = microscope.get_error_details()
                    print(f"[MICROSCOPE] [FAIL] Button '{action}' not found or click failed: {error_msg}")
                    
                    # Show error dialog and let user manually press the button
                    error_dialog_msg = f"ERROR: Could not press '{action}' button.\n\nPlease press it manually and click OK to continue."
                    print(f"[ERROR] Showing manual intervention dialog...")
                    MessageBox.show_ok(error_dialog_msg, "Microscope Error")
                    print(f"[MICROSCOPE] User confirmed manual button press, continuing...")
            continue
        
        # Legacy: Microscope acquire command (alias for microscope: run)
        if "microscope_acquire" in step:
            if not microscope:
                print("[WARN] Microscope requested but not initialized")
                continue
            print(f"[MICROSCOPE] Triggering image acquisition...")
            success = microscope.acquire()
            if success:
                print(f"[MICROSCOPE] ✓ Acquisition completed successfully")
            else:
                print(f"[MICROSCOPE] ✗ Acquisition failed or timed out")
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

    # Ensure signal handlers are active so Ctrl+C can be handled gracefully
    global STOP_REQUESTED
    STOP_REQUESTED = False
    _setup_signal_handlers()

    config = load_yaml_config(args.yaml_file)
    required_hw = config.get("required hardware", {})
    if not required_hw:
        print("No 'required hardware' section found in YAML file. Aborting.")
        return 1

    pump_enabled = bool(required_hw.get("pump", False))
    valve_enabled = bool(required_hw.get("valve", False))
    pinch_valve_enabled = bool(required_hw.get("pinch_valve", False))
    microscope_enabled = bool(required_hw.get("microscope", False))
    
    # valve_enabled includes both standard and pinch valve
    valve_enabled = valve_enabled or pinch_valve_enabled
    dry_run = args.dry_run

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
            pump = Pump_win()
            if not pump.initialize():
                print(f"Pump_win initialization failed: {pump.get_error_details()}")
                print(f"Suggested fix: {pump.get_suggested_fix()}")
                print("Trying WSL pump controller...")
                pump = Pump_wsl()
                if not pump.initialize():
                    print(f"Pump_wsl initialization failed: {pump.get_error_details()}")
                    print(f"Suggested fix: {pump.get_suggested_fix()}")
                    return 1

    # Dual valve controller (solenoid + pinch on same Arduino)
    valve = None
    
    if valve_enabled:
        if dry_run:
            valve = MockValve()
        else:
            # Auto-detect valve port using VID/PID or description, with fallback to env/default
            ports_info = resolve_ports_from_env()
            valve_port = ports_info["valve_port"]
            valve_baud = ports_info["valve_baud"]
            detection_method = "auto-detected (VID/PID)" if ports_info["valve_detected"] else ("env override" if ports_info["valve_from_env"] else "fallback default")
            
            print(f"[INFO] Attempting dual valve controller connection on {valve_port} ({detection_method})")
            valve = DualValveController(port=valve_port, baudrate=valve_baud)
            if getattr(valve, 'ser', None) is None:
                print(f"Dual valve initialization failed: Serial connection not established on {valve_port}")
                print(f"Suggested fix: Check Arduino connection or verify ARDUINO_VID/ARDUINO_PID in .env")
                return 1
            print(f"[INFO] Dual valve controller initialized successfully on {valve_port}")

    microscope = None
    if microscope_enabled:
        # File-based remote desktop via C# server on Windows 7
        if dry_run:
            from src.microscope import MockMicroscope
            print(f"[INFO] Using MOCK microscope (dry-run mode)")
            microscope = MockMicroscope()
        else:
            from src.microscope import Microscope
            print(f"[INFO] Initializing microscope remote desktop controller...")
            
            microscope = Microscope()
            if not microscope.initialize():
                print(f"[WARN] Microscope initialization failed:")
                print(f"       {microscope.get_error_details()}")
                print(f"       Suggested fix: {microscope.get_suggested_fix()}")
                # Don't exit - allow protocol to run and retry connection later
            else:
                print(f"[INFO] Microscope controller connected successfully")

    try:
        run_sequence(config, pump, valve, pump_profiles, microscope=microscope, dry_run=dry_run)
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("[INTERRUPT] Ctrl+C detected - initiating emergency shutdown")
        print("="*60)
        
        # Stop pump immediately
        if pump:
            try:
                print("[SHUTDOWN] Stopping pump...")
                pump.stop()
                print("[SHUTDOWN] ✓ Pump stopped")
            except Exception as e:
                print(f"[SHUTDOWN] ✗ Pump stop failed: {e}")
        
        # Turn off valves (both solenoid and pinch)
        if valve:
            try:
                print("[SHUTDOWN] Turning off solenoid valve...")
                valve.solenoid_off()
                print("[SHUTDOWN] ✓ Solenoid valve off")
            except Exception as e:
                print(f"[SHUTDOWN] ✗ Solenoid valve off failed: {e}")
            try:
                print("[SHUTDOWN] Turning off pinch valve...")
                valve.pinch_off()
                print("[SHUTDOWN] ✓ Pinch valve off")
            except Exception as e:
                print(f"[SHUTDOWN] ✗ Pinch valve off failed: {e}")
        
        # Close microscope connection
        if microscope:
            try:
                print("[SHUTDOWN] Closing microscope connection...")
                microscope.close()
                print("[SHUTDOWN] ✓ Microscope closed")
            except Exception as e:
                print(f"[SHUTDOWN] ✗ Microscope close failed: {e}")
        
        print("="*60)
        print("[SHUTDOWN] Emergency shutdown complete - protocol aborted")
        print("="*60)
        return 130  # Standard exit code for Ctrl+C
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
        if microscope:
            try:
                microscope.close()
            except Exception:
                pass
    print("Sequence complete.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
