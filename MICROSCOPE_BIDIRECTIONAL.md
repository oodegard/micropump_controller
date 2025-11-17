# Bidirectional Microscope Communication

This system enables full bidirectional communication between the controller PC and the airgapped microscope PC using FSK audio modems.

## How It Works

### Communication Flow

```
Controller PC                    Microscope PC
-------------                    -------------
1. Send CAPTURE    ────────────>  Receives CAPTURE
                                  2. Clicks "Acquire" button
                                  3. Waits 1 second
                                  4. Monitors button color
                                  5. Waits for grey→normal
6. Receives DONE   <────────────  Sends DONE
7. Continues workflow
```

### Technical Details

**Protocol:** FSK (Frequency Shift Keying) audio modem
- **Mark frequency (0 bit):** 1200 Hz
- **Space frequency (1 bit):** 1800 Hz  
- **Preamble:** 1500 Hz sync tone
- **Bit rate:** 10 baud (100ms per bit)
- **Error detection:** 4-bit CRC checksum
- **Commands:** CAPTURE (trigger acquisition), DONE (acquisition complete)

**Button Monitoring:**
- Captures RGB color of "Acquire" button in normal state
- After clicking, waits 1 second
- Polls button color every 2 seconds
- Detects when button returns to normal color (within 30 RGB units tolerance)
- Maximum wait time: 600 seconds (10 minutes)

## Setup

### Controller PC (Sender)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure audio devices:**
   ```bash
   uv run python src/microscope.py
   ```
   This will prompt you to select input/output devices and save the configuration.

3. **Test communication:**
   ```bash
   uv run python test_bidirectional_microscope.py
   ```

### Microscope PC (Receiver)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run listener:**
   ```bash
   uv run python microscope_listener.py
   ```

3. **First-time setup:**
   - Select input device (for receiving CAPTURE commands)
   - Select output device (for sending DONE responses)
   - Position mouse over "Acquire" button when prompted (5 second countdown)
   - Make sure button is in NORMAL state, press Enter to calibrate color

4. **Listener will:**
   - Wait for CAPTURE command
   - Click the Acquire button
   - Monitor button state
   - Send DONE when acquisition completes
   - Repeat indefinitely

## Usage in Workflows

### YAML Configuration

```yaml
hardware:
  pump: true
  microscope: true  # Enable microscope

sequence:
  - name: "Take image"
    microscope_acquire: true  # Blocks until microscope responds with DONE
    
  - name: "Do something after image"
    pump_freq: 120
    wait: 5
```

### Command Line

```bash
# Run workflow with microscope integration
uv run python run_protocol_cli.py config_examples/microscope_workflow.yaml

# Test without hardware (dry run)
uv run python run_protocol_cli.py --dry-run config_examples/microscope_workflow.yaml
```

## Troubleshooting

### No CAPTURE signal received on microscope

**Symptoms:** Listener running but never detects CAPTURE command

**Solutions:**
1. Check audio cable is connected (controller output → microscope input)
2. Verify audio devices are correct:
   ```bash
   # On microscope PC
   uv run python test_audio_comunication/check_audio_devices.py
   ```
3. Increase volume on controller PC output
4. Test with simple tone generator:
   ```bash
   # On controller PC
   uv run python test_audio_comunication/simple_tone_generator.py
   ```

### No DONE signal received on controller

**Symptoms:** Microscope clicks button but controller times out waiting

**Solutions:**
1. Check audio cable is connected (microscope output → controller input)
2. Verify microscope is sending DONE (check console output)
3. Increase volume on microscope PC output
4. Check input device on controller PC is correct

### Button monitoring fails

**Symptoms:** Listener clicks button but doesn't detect completion

**Solutions:**
1. Re-calibrate button color (restart listener)
2. Increase color tolerance in code (currently 30 RGB units)
3. Make sure button position is correct
4. Check if microscope acquisition actually changes button color
5. Add debugging to `is_button_normal()` function:
   ```python
   print(f"Current RGB: ({r}, {g}, {b}), Target: {normal_color}")
   ```

### Acquisition takes too long

**Symptoms:** Timeout after 10 minutes

**Solutions:**
1. Increase timeout in `microscope.acquire()`:
   ```python
   microscope.acquire(timeout=1800.0)  # 30 minutes
   ```
2. Or in `microscope_listener.py`:
   ```python
   wait_for_acquisition_complete(x, y, color, max_wait=1800.0)
   ```

## Testing

### Test Scripts

1. **Full bidirectional test:**
   ```bash
   # On controller PC
   uv run python test_bidirectional_microscope.py
   ```
   Sends CAPTURE and waits for DONE response.

2. **Audio devices:**
   ```bash
   uv run python test_audio_comunication/check_audio_devices.py
   ```
   Lists all available audio devices.

3. **Simple tone test:**
   ```bash
   # Sender
   uv run python test_audio_comunication/simple_tone_generator.py
   
   # Receiver  
   uv run python test_audio_comunication/simple_audio_listener.py
   ```

### Manual Testing

1. **Start listener on microscope PC:**
   ```bash
   uv run python microscope_listener.py
   ```

2. **Send test command from controller PC:**
   ```bash
   uv run python -c "from src.microscope import Microscope; m = Microscope(); m.acquire()"
   ```

3. **Observe:**
   - Controller: Shows "Sending CAPTURE", then "Listening for DONE..."
   - Microscope: Shows "CAPTURE received!", clicks button, monitors, sends "DONE"
   - Controller: Shows "DONE received!" and returns

## Architecture

### Files

- `src/microscope.py` - Microscope controller class (sender)
- `microscope_listener.py` - Listener script (receiver)
- `test_audio_comunication/audio_protocol.py` - FSK modem implementation
- `test_audio_comunication/audio_config.py` - Audio device configuration
- `test_bidirectional_microscope.py` - Test script
- `config_examples/microscope_workflow.yaml` - Example workflow

### Dependencies

- `sounddevice` - Audio I/O
- `numpy` - Signal processing
- `pyautogui` - GUI automation (clicking button)
- `PIL` (Pillow) - Screenshot capture for button monitoring
- `scipy` - High-pass filtering (optional, for noise reduction)

## Advanced Configuration

### Adjust FSK Parameters

Edit `test_audio_comunication/audio_protocol.py`:

```python
@dataclass
class FSKConfig:
    sample_rate: int = 44100
    mark_freq: int = 1200      # Binary 0
    space_freq: int = 1800     # Binary 1
    bit_duration: float = 0.1  # Slower = more robust, faster = quicker
    preamble_freq: int = 1500  
    min_signal_power: float = 0.005  # Lower = more sensitive
    frequency_tolerance: float = 150  # Higher = more tolerant
```

### Adjust Button Detection

Edit `microscope_listener.py`:

```python
# Color tolerance (RGB difference)
tolerance = 30  # Increase if button color varies

# Poll interval
time.sleep(2.0)  # Check button every 2 seconds

# Initial delay
time.sleep(1.0)  # Wait before first check
```

## Future Enhancements

- [ ] Add error signaling (ERROR command if acquisition fails)
- [ ] Support multiple acquisition modes
- [ ] Save calibrated button position/color to file
- [ ] Add visual feedback GUI for listener
- [ ] Support for stage movement commands
- [ ] Batch acquisition with progress updates
