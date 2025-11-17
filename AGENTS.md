# Micropump Controller AI Instructions

## Project Overview
This is a Windows-first hardware control system for Bartels micropumps and Arduino-based solenoid valves, with cross-platform support via WSL. The architecture prioritizes **serial communication reliability** and **flexible deployment patterns**.

## Key Architecture Patterns

### Device Controller Pattern
Controllers use a **try-initialize-fallback** pattern with automatic port detection:
- `Pump_win` (Windows native) and `Pump_wsl` (WSL-based) share identical interfaces  
- `ValveController` (`src/valve.py`) uses direct Arduino serial communication
- All controllers implement: `initialize()`, `close()`, error handling, and parameter validation

**Example controller structure:**
```python
def initialize(self) -> bool:
    # 1. Auto-detect port if not specified
    # 2. Test communication with short timeout
    # 3. Set self.is_initialized flag
    # 4. Store detailed error messages for debugging
```

### Port Resolution Strategy
The system uses a **layered port detection** approach in `src/resolve_ports.py`:
1. Explicit environment variables (`PUMP_PORT`, `VALVE_SERIAL_PORT` from `.env`)
2. VID/PID detection via `get_port_by_id('pump'/'arduino')`
3. Keyword-based description matching
4. Fallback defaults (COM4, COM5)

**Critical:** Always test `_test_communication()` after port assignment, not just serial open.

### WSL Integration Pattern
WSL support enables cross-platform deployment without VM overhead:
- `src/pump_wsl.py` executes Python serial commands in WSL via subprocess
- Admin elevation handled via `via_wsl/run_as_admin.bat` + Python scripts
- USB device attachment automated through `usbipd-win` integration via `via_wsl/attach_micropump.py`
- Same pump interface as Windows version for drop-in replacement

## Development Workflows

### Configuration-Driven Execution
Use YAML configs in `config_examples/` for complex sequences:
```bash
# Test with mock devices
uv run python run_protocol_cli.py --dry-run config_examples/pump_on_10s.yaml

# Real hardware with port auto-detection  
uv run python run_protocol_cli.py config_examples/continuous_switching.yaml

# Force manual port configuration
PUMP_PORT=COM3 uv run python run_protocol_cli.py config_examples/pump_on_10s.yaml
```

### Environment Setup Commands
```bash
# Install environment with UV
uv sync

# Test hardware connection
uv run python -c "from src.resolve_ports import list_all_ports; print(list_all_ports())"

# Verify device detection
uv run python -c "from src.resolve_ports import get_port_by_id; print(get_port_by_id('pump'))"
```

### Audio Monitoring Integration
Use `src/audio/monitor.py` for debugging pump operations:
```bash
# Monitor any command execution
uv run python src/audio/monitor.py "uv run python run_protocol_cli.py config_examples/pump_on_10s.yaml"

# Test device discovery
uv run python src/audio/discovery.py
```

### WSL Setup Workflow
For cross-platform development, use the automated WSL setup:
```bash
# Attach USB device to WSL with admin elevation
via_wsl/run_as_admin.bat attach_micropump.py --distro Ubuntu

# Test WSL pump controller
uv run python -c "from src.pump_wsl import Pump_wsl; p = Pump_wsl(); p.initialize()"
```

### Important WSL Patterns
- **Admin elevation:** WSL USB attachment requires administrator privileges; `via_wsl/run_as_admin.bat` handles UAC prompts automatically
- **FTDI driver setup:** `attach_micropump.py` includes interactive FTDI driver installation with single sudo prompt
- **Device reconnection:** Auto-detach/reattach cycle in `attach_micropump.py` forces driver recognition in WSL
- **Subprocess communication:** WSL controllers execute Python serial commands via `subprocess.run()` with WSL distribution targeting

## Critical Implementation Details

### Hardware Communication Protocol
- **Pump commands:** `F{freq}\r`, `A{voltage}\r`, `MR\r` (rect), `MS\r` (sine), `bon\r`, `boff\r`
- **Valve commands:** `ON\n`, `OFF\n`, `TOGGLE\n`, `PULSE {ms}\n`, `STATE?\n`
- **Timing:** Add 0.15s delays between pump commands; valve responses are immediate
- **Flow control:** Pumps use XON/XOFF; valves use standard serial

### Error Handling Pattern
All controllers implement detailed error reporting:
```python
def get_error_details(self) -> str:
    return self.last_error

def get_suggested_fix(self) -> str:
    # Return actionable troubleshooting steps
```

Use this for user-friendly diagnostics rather than throwing exceptions.

### Cross-Platform Abstraction
- Controllers have identical interfaces but platform-specific implementations
- WSL controllers run Python serial code via subprocess for USB access
- Admin elevation automatically handled through batch file wrappers
- Mock controllers (`MockPump`, `MockValve`) for testing without hardware

### CLI Integration Patterns
- Use `--dry-run` for development and testing
- YAML sequences support both profile-based (`pump_on: profile_name`) and granular commands (`pump_freq: 120`)
- Environment variables override auto-detection for CI/testing scenarios

### Type Hinting Standards
**Be diligent about type hints** - this codebase maintains strict typing standards:
- All function parameters and return types must be annotated
- Use `Optional[T]` for nullable types, `List[T]` for lists, `Dict[K, V]` for dictionaries
- Import from `typing` module: `from typing import Optional, List, Dict, Any`
- Controller methods return `bool` for success/failure operations
- Port detection functions return `str` for ports or raise exceptions

**Example pattern:**
```python
def initialize(self) -> bool:
def get_port_by_id(device: str) -> str:
def _run_wsl_command(self, python_code: str) -> bool:
```

## Common Debugging Patterns

**Port detection issues:** Check `.env` VID/PID values match `list_all_ports()` output
**WSL USB problems:** Use `via_wsl/attach_micropump.py` with admin elevation  
**Communication failures:** Verify `_test_communication()` passes before operations
**Timing issues:** Increase delays between commands, especially for pump configuration changes

## Testing Conventions
- Mock objects mirror real device interfaces exactly
- Test scripts in `tests/` and `via_wsl/` use real hardware when available
- Audio monitoring provides quantitative feedback for pump operation validation
- Use `--force-attach` and `--skip-attach` flags for WSL testing control