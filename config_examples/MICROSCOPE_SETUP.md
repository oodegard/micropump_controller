# Microscope Integration Setup Guide

## Overview
The microscope controller uses **file-based communication** with a C# remote desktop server running on Windows 7. Commands are sent via JSON files in a shared network folder.

## Quick Start

### 1. Start the C# Server on Windows 7
```bash
# On the microscope PC (Windows 7):
cd C:\RemoteDesktop
RemoteDesktopServer.exe
```

You should see:
```
RemoteDesktop Server Starting...
Monitoring folder: C:\RemoteDesktop
Waiting for commands from client...
```

### 2. Find Button Coordinates

**Method 1: Using Windows Screenshot Tool**
1. Open your microscope software
2. Press `Win + Shift + S` to take a screenshot
3. Move your mouse to the Run button and note the coordinates in the bottom-left corner
4. Write down the X and Y values

**Method 2: Using Paint**
1. Take a screenshot (`PrintScreen` key)
2. Paste into Paint
3. Hover over the Run button center
4. Note the coordinates shown in the bottom-left corner

**Method 3: Remote Screenshot**
1. Copy `dist/RemoteDesktopServer_Win7/commands/screenshot.json` to `C:\RemoteDesktop\command.json`
2. Open `C:\RemoteDesktop\screenshot.jpg` in Paint
3. Find the button coordinates as above

### 3. Update Default Coordinates

Edit `src/microscope.py`:
```python
# Default button coordinates (update these for your microscope software)
DEFAULT_RUN_X = 450      # Change to your measured X
DEFAULT_RUN_Y = 120      # Change to your measured Y
```

Or specify in YAML/code:
```python
from src.microscope import Microscope

microscope = Microscope(
    shared_folder=r"\\BIPHUB\RemoteDesktopServer_Win7\C_RemoteDesktop",
    run_button_x=450,
    run_button_y=120
)
```

### 4. Test the Connection

```bash
# Dry-run test (no hardware needed)
uv run python run_protocol_cli.py --dry-run config_examples/microscope_simple.yaml

# Real hardware test (requires C# server running)
uv run python run_protocol_cli.py config_examples/microscope_simple.yaml
```

## YAML Command Reference

### Available Commands

**Start acquisition:**
```yaml
- microscope: start
- duration: 2
```

**Wait for completion:**
```yaml
- microscope: wait_done
- duration: 300  # Max timeout in seconds
```

**Take screenshot:**
```yaml
- microscope: screenshot
- duration: 1
```

## Network Share Configuration

The system uses a shared folder for communication. Default path:
```
\\BIPHUB\RemoteDesktopServer_Win7\C_RemoteDesktop
```

This maps to `C:\RemoteDesktop` on the Windows 7 PC.

### Files Used:
- `command.json` - Commands from controller PC → microscope PC
- `response.json` - Status responses from microscope PC → controller PC
- `screenshot.jpg` - Screen captures (when requested)

## Troubleshooting

### "Shared folder not accessible"
```bash
# Check share is available (on controller PC):
dir \\BIPHUB\RemoteDesktopServer_Win7\C_RemoteDesktop

# If fails, verify:
# 1. Network connection between PCs
# 2. C# server is running on Windows 7 PC
# 3. Share exists: net share (on microscope PC)
```

### "Timeout waiting for server response"
- Check `RemoteDesktopServer.exe` is running on Windows 7
- Verify it shows "Monitoring folder: C:\RemoteDesktop"
- Check server console for error messages
- Try manual test: copy a command JSON file to `C:\RemoteDesktop\command.json`

### Button Click Not Working
- Take a screenshot and verify coordinates
- Test manually: Use `commands/click_example.json` and update coordinates
- Check if UI layout changed (screen resolution, window position)
- Try clicking 10-20 pixels to the right/left if button is wide

### Button Detection (Future Enhancement)
Currently uses **coordinate-based clicking** (simple, fast, reliable).

For **image-based detection** (more flexible):
1. Add EmguCV library to C# project
2. Implement template matching (similar to tracebot_oo)
3. Save button screenshots in `buttons/` folder
4. Update microscope.py to send image paths instead of coordinates

## Example Workflow

```yaml
# Complete microscope + pump workflow
required hardware:
  pump: true
  valve: false
  microscope: true

pump settings:
  high_flow:
    waveform: RECT
    voltage: 200
    freq: 150

run:
  # Start microscope
  - microscope: start
  - duration: 2
  
  # Flow during capture
  - pump_on: high_flow
  - duration: 30
  - pump_off: 0
  
  # Wait for microscope to finish
  - microscope: wait_done
  - duration: 300
  
  # Capture final state
  - microscope: screenshot
  - duration: 1
```

## Architecture

```
Controller PC (Win11)              Microscope PC (Win7)
├── run_protocol_cli.py        →   ├── RemoteDesktopServer.exe
├── src/microscope.py              │   (monitors command.json)
└── config YAML                    └── C:\RemoteDesktop\
                                       ├── command.json
                                       ├── response.json
                                       └── screenshot.jpg
```

Communication flow:
1. Python writes `command.json` to shared folder
2. C# server detects file change (100ms polling)
3. C# executes command (click, type, screenshot, etc.)
4. C# writes `response.json` with status
5. Python reads response and continues

## Next Steps

1. Find your Run button coordinates
2. Update `DEFAULT_RUN_X` and `DEFAULT_RUN_Y` in `src/microscope.py`
3. Test with `--dry-run` first
4. Run real test with C# server active
5. Integrate into your experimental workflows
