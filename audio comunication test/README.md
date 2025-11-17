# Audio Communication System

This system enables two PCs to communicate via audio cables (microphone-to-line/speaker connection).

## Hardware Setup

Connect a 3.5mm audio cable:
- **PC 1:** Microphone jack → Cable
- **PC 2:** Cable → Microphone jack
- The cable is wired L+R on both sides for bidirectional communication

## Software Components

### Core Module
- **`audio_comm.py`** - Main communication library with `AudioCommander` (send) and `AudioListener` (receive) classes

### Usage Scripts
- **`listen.py`** - Receiver mode - listens for commands and auto-responds
- **`send.py`** - Sender mode - interactive interface to send commands
- **`test_connection.py`** - Test suite to verify audio input/output

## Commands

Three simple commands are supported:

1. **RUN** - Initiates a command on the receiving PC
2. **RUN_COMMAND_RECEIVED** - Acknowledges receipt of RUN command
3. **RUN_DONE** - Signals completion of the command

Each command is encoded as a unique dual-tone frequency pair for reliable detection.

## Installation

Install required dependencies:

```powershell
pip install numpy sounddevice scipy
```

Or add to your project's requirements:
```bash
uv pip install numpy sounddevice scipy
```

## Quick Start

### Test Your Setup

1. **On both PCs**, test audio devices:
   ```powershell
   python test_connection.py
   ```
   - Run option 1 to test output (should hear beep)
   - Run option 2 to test input (speak/make noise)

### Basic Communication

2. **On PC 1** (receiver), start listening:
   ```powershell
   python listen.py
   ```

3. **On PC 2** (sender), send commands:
   ```powershell
   python send.py
   ```
   - Enter `1` to send RUN
   - Enter `2` to send RUN_COMMAND_RECEIVED
   - Enter `3` to send RUN_DONE

### Expected Behavior

When you send **RUN** from PC 2:
- PC 1 receives it and prints ">>> RECEIVED: RUN"
- PC 1 automatically sends back "RUN_COMMAND_RECEIVED"
- PC 2 should receive the acknowledgment

## Programmatic Usage

```python
from audio_comm import AudioCommander, AudioListener

# Sending commands
commander = AudioCommander()
commander.send_command('RUN')

# Receiving commands
def my_callback(command):
    print(f"Got command: {command}")
    # Your logic here

listener = AudioListener(callback=my_callback)
listener.start_listening()

# When done
listener.stop_listening()
```

## Troubleshooting

### No sound playing
- Check Windows sound settings for default output device
- Verify cable is connected to speaker/line-out (not microphone)
- Run `test_connection.py` option 1

### Not receiving commands
- Check Windows sound settings for default input device
- Verify cable is connected to microphone jack
- Check volume levels aren't too low
- Run `test_connection.py` option 2 to verify input levels

### Commands detected but unreliable
- Adjust input volume (should be mid-range, not maxed)
- Ensure cable has good connections
- Try increasing `DETECTION_THRESHOLD` in `audio_comm.py`
- Move away from noise sources

### Audio device selection
Use `list_audio_devices()` to see available devices and modify the config:

```python
from audio_comm import AudioConfig, AudioCommander

config = AudioConfig(input_device=1, output_device=3)
commander = AudioCommander(config=config)
```

## Technical Details

- **Encoding:** Dual-tone multi-frequency (DTMF-like) using unique frequency pairs
- **Sample Rate:** 44.1 kHz
- **Tone Duration:** 150ms per tone (sent 3x for reliability)
- **Detection:** FFT-based frequency analysis with configurable thresholds
- **Threading:** Listener runs in background thread for non-blocking operation

## Advanced Configuration

Edit `audio_comm.py` to adjust:
- `TONE_DURATION` - Length of each tone
- `AMPLITUDE` - Volume level (0.0 to 1.0)
- `DETECTION_THRESHOLD` - Sensitivity for command detection
- `FREQUENCY_TOLERANCE` - Hz tolerance for matching
- `COMMAND_TONES` - Add custom commands with new frequency pairs
