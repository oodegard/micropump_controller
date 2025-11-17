# Handshake Integration Guide

The handshake logic from `quick_setup.py` has been integrated into the production classes for seamless use.

## Overview

- **Sender logic** → `src/microscope.py` (Microscope class)
- **Receiver logic** → `microscope_listener.py`
- **Handshake frequencies**: 900 Hz (calling) / 1100 Hz (answer)

## Usage

### On the SENDER PC (Microfluidics Controller)

```python
from src.microscope import Microscope

# Initialize with automatic handshake (default)
microscope = Microscope()

if microscope.is_connected:
    # Send capture command and wait for done
    microscope.acquire()
```

Or test with the provided script:
```bash
uv run python test_microscope_handshake.py
```

**Receiver PC (Microscope - Airgapped):**

Run the listener with button image:
```bash
uv run python microscope_listener.py --button-image run.png
```

Or use default (run.png in project root):
```bash
uv run python microscope_listener.py
```

## What Happens

### Initialization Sequence

1. **Microscope class** (`__init__`):
   - Auto-detects audio devices (or uses provided device IDs)
   - Calls `establish_handshake()` if `auto_handshake=True` (default)
   
2. **Handshake Process** (Sender side):
   - Sends 900 Hz calling tone repeatedly
   - Listens for 1100 Hz answer tone after each call
   - Requires 3 consecutive answer detections
   - Stops calling tone when confirmed (signals receiver)
   - Sets `is_connected = True`

3. **Handshake Process** (Receiver side):
   - Listens for 900 Hz calling tone
   - Requires 3 consecutive calling tone detections
   - Starts sending 1100 Hz answer tone continuously
   - Waits for sender to stop calling (3 consecutive non-detections)
   - Proceeds to command listening loop

### Command Cycle

After handshake established:

1. Sender calls `microscope.acquire()`
2. Sends CAPTURE command via FSK audio
3. Receiver hears CAPTURE → clicks Acquire button
4. Receiver monitors button state until acquisition complete
5. Receiver sends DONE command
6. Sender receives DONE → returns True

## Manual Control

If you want to skip auto-handshake:

```python
# Initialize without handshake
microscope = Microscope(auto_handshake=False)

# Manually establish later
if microscope.establish_handshake():
    print("Connected!")
    microscope.acquire()
```

## Button Image Setup

### Creating Button Image

1. Take a screenshot of your Acquire button when it's visible/enabled
2. Crop to just the button (include some border for better matching)
3. Save as `run.png` in the project root
4. Or save anywhere and specify with `--button-image` flag

### Command Line (Recommended)
```bash
python microscope_listener.py --button-image path/to/button.png
```

### Default Image
If you don't provide `--button-image`, the script uses `run.png` from the project root.

### Image Recognition Tips

- **Resolution**: Button image should match your screen resolution
- **Lighting**: Screenshot should match typical lighting conditions
- **State**: Capture button in its normal/enabled state (not greyed out)
- **Confidence**: Default is 0.8 (80% match) - adjust if needed in code

## Troubleshooting

### Handshake Fails
- Check volume levels on both PCs (should be moderate, not max)
- Verify microphone not muted
- Try running `quick_setup.py` standalone to test audio path
- Check firewall/antivirus not blocking audio devices

### "Not connected" Error
```python
microscope = Microscope()
if not microscope.is_connected:
    print(f"Error: {microscope.last_error}")
    # Try manual handshake
    microscope.establish_handshake()
```

### Receiver Not Hearing Commands
- Verify handshake completed successfully on both sides
- Check FSK modem frequencies match (1200/1800 Hz for data)
- Monitor audio levels (should see "Sound detected" messages)
- Run with debug: Check `modem.decode_command(audio, debug=True)`

## Integration Example

```python
from src.microscope import Microscope
from src.pump_win import Pump_win
from src.valve import ValveController

# Setup devices
microscope = Microscope()  # Auto-handshake
pump = Pump_win()
pump.initialize()
valve = ValveController()

# Wait for handshake
if not microscope.is_connected:
    print("Waiting for microscope connection...")
    exit(1)

# Run experiment
print("Starting experiment...")
pump.set_frequency(120)
pump.set_voltage(200)
pump.start()

# Trigger acquisition
print("Capturing image...")
if microscope.acquire():
    print("Image captured!")
else:
    print("Acquisition timeout")

pump.stop()
valve.open()
```

## Files Modified

- `src/microscope.py`: Added sender handshake logic
- `microscope_listener.py`: Added receiver handshake logic + argparse for button position
- `test_microscope_handshake.py`: New test script for sender PC

## Original Quick Setup

The original `quick_setup.py` is still available for standalone testing:
```bash
cd test_audio_comunication
uv run python quick_setup.py
```

This is useful for:
- Debugging audio issues
- Testing new frequencies
- Verifying hardware before integration
