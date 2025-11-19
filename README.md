# Micropump Controller

Hardware control system for Bartels micropumps, Arduino solenoid valves, and remote microscope automation.

## Quick Start

### Installation
```bash
# Clone and setup environment
uv sync

# Test hardware connection
uv run python -c "from src.resolve_ports import list_all_ports; print(list_all_ports())"
```

### Basic Usage
```bash
# Run a protocol from YAML config
uv run python run_protocol_cli.py config_examples/pump_on_10s.yaml

# Dry run (mock devices)
uv run python run_protocol_cli.py --dry-run config_examples/continuous_switching.yaml
```

## Features

- **Pump Control**: Bartels micropumps (Windows native or WSL)
- **Valve Control**: Arduino-based solenoid valves via serial
- **Protocol Automation**: YAML-based sequences with timing
- **Microscope Automation**: File-based control for Windows 7 microscopes
- **Port Auto-Detection**: Automatic USB device discovery

## Project Structure

```
src/
├── pump_win.py          # Windows native pump controller
├── pump_wsl.py          # WSL-based pump controller  
├── valve.py             # Arduino valve controller
├── microscope.py        # Microscope control via file-based communication
├── stage3d.py           # 3D stage control
└── resolve_ports.py     # Automatic port detection

config_examples/         # Example protocol YAML files
microscope_server/       # C# server for Windows 7 microscopes
via_wsl/                # WSL USB attachment utilities
Legacy/                 # Old implementations (audio/ethernet control)
```

## Microscope Control

**Windows 7 Compatible Solution** - Uses file-based communication via network share.

### Server Setup (Windows 7 Microscope PC)

1. Build the C# server: `C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe microscope_server\MicroscopeServer.csproj /p:Configuration=Release`
2. Or use pre-built `microscope_server\bin\Release\MicroscopeServer.exe`
3. On the microscope PC, run the server with: `MicroscopeServer.exe \\BIPHUB\micropump_controller`
4. Server monitors the shared folder for commands
5. Place button images in `buttons/` subfolder of the shared location

See `microscope_server/` folder for C# source and build instructions.

### Client Usage (Controller PC)

```python
from src.microscope import Microscope

# Initialize with network share
microscope = Microscope(shared_folder=r"\\BIPHUB\micropump_controller")
microscope.initialize()

# Control microscope
microscope.click(500, 300)           # Click at coordinates
microscope.type_text("sample_01")    # Type text
microscope.press_key("enter")        # Press key
microscope.run()                     # Start acquisition
```

### How It Works

**File-Based Communication:**
- Client writes `command.json` to network share
- Server monitors folder, executes commands
- Server updates `response.json` with status
- Screenshots saved as `screenshot.jpg`

**Why File-Based?**
- ✅ Windows 7 compatible (Python 3.12 isn't!)
- ✅ Simple network setup (just share a folder)
- ✅ No firewall/port configuration needed
- ✅ Easy to debug (just look at the JSON files)
- ✅ Only 6.8 MB server package

## Hardware Configuration

### Pump (Bartels Micropump)
- **Auto-detection**: VID:PID 0403:6015 (FTDI)
- **Commands**: Frequency (0-300 Hz), Voltage (0-250V), Waveform
- **Windows**: Direct serial access
- **WSL**: Use `via_wsl/attach_micropump.py` for USB forwarding

### Valve (Arduino)
- **Auto-detection**: Arduino VID:PID
- **Baud Rate**: 9600
- **Commands**: ON, OFF, TOGGLE, PULSE <ms>, STATE?

### Environment Variables (.env)
```bash
PUMP_PORT=COM4              # Override auto-detection
VALVE_SERIAL_PORT=COM5      # Override valve port
```

## Protocol YAML Format

```yaml
# Example: Cleaning cycle with valve and pump
steps:
  - valve_state: ON         # Open valve
    duration: 2
  
  - pump_on: high_flow      # Use predefined profile
    duration: 10
    
  - pump_freq: 120          # Or set parameters directly
    pump_voltage: 200
    pump_waveform: rect
    duration: 30
    
  - valve_state: OFF        # Close valve
    duration: 1
```

See `config_examples/` for more examples.

## Development

### Testing
```bash
# Mock hardware test
uv run python run_protocol_cli.py --dry-run config_examples/pump_on_10s.yaml

# Real hardware
uv run python run_protocol_cli.py config_examples/valve_test.yaml
```

### WSL Development
```bash
# One-time setup: Attach USB to WSL
via_wsl/run_as_admin.bat attach_micropump.py --distro Ubuntu

# Test WSL pump
uv run python -c "from src.pump_wsl import Pump_wsl; p = Pump_wsl(); p.initialize()"
```

## Documentation

- **AGENTS.md** - AI instructions and architecture patterns
- **microscope_server/** - C# microscope server source code
  - `MicroscopeServer.cs` - Main server implementation
  - `MicroscopeServer.csproj` - Build configuration
  - `EMGUCV_SETUP.md` - OpenCV setup instructions
- **config_examples/README.md** - Protocol configuration guide

## Legacy Code

The `Legacy/` folder contains older implementations:
- Python remote desktop attempts (Windows 8+ only)
- Audio-based microscope control
- Ethernet command protocols
- Old summary documentation

These are kept for reference but not actively maintained.

## License

See LICENSE file.
