# Audio-Based Communication for Airgapped Microscope Control

## Overview

This folder contains an **FSK (Frequency Shift Keying) audio modem** for communicating between:
- **Microfluidics PC** (this computer) running `run_protocol_cli.py`
- **Microscope PC** (airgapped computer) running `microscope_control.exe`

The system uses audio tones (like old-school modems) to send commands without any physical connection.

---

## Files

- **`audio_protocol.py`** - Core FSK modem implementation with error correction
- **`microscope_audio_test.py`** - Standalone test suite for feasibility testing
- **`build_standalone.py`** - Build script to create `.exe` for airgapped transfer
- **`requirements.txt`** - Python dependencies (sounddevice, numpy)

---

## How It Works

### FSK Protocol Features

The protocol is based on Bell 202 modem standard with safety features:

- **Two frequencies for binary data:**
  - 1200 Hz = binary 0 (mark)
  - 1800 Hz = binary 1 (space)

- **Preamble sync tone (2400 Hz for 500ms)**
  - Prevents false triggers from background speech
  - Signals "start of transmission"

- **4-bit checksum**
  - Detects corrupted transmissions
  - Auto-rejects invalid data

- **Noise immunity:**
  - Minimum tone duration (80ms) filters out speech
  - Frequency tolerance (±100 Hz) handles speaker variations
  - Minimum signal power threshold

- **Total transmission time: ~1.3 seconds per command**
  - Too long for accidental speech patterns to trigger

### Available Commands

```python
Command.CAPTURE  # Trigger image capture
Command.DONE     # Capture complete
Command.ERROR    # Capture failed
Command.PING     # Test connection
Command.PONG     # Respond to ping
```

---

## Testing on Two Computers

### Step 1: Install Dependencies (on THIS PC)

```powershell
cd test_audio_comunication
pip install -r requirements.txt
```

### Step 2: Run Feasibility Test (on THIS PC first)

```powershell
python microscope_audio_test.py
```

**Expected output:**
- Test 1: Hear system beep ✓
- Test 2: Hear 1200 Hz tone ✓
- Test 3: Clap hands, see audio detected ✓
- Test 4: Frequency detection working ✓
- Test 5: FSK protocol encode/decode ✓
- Test 6: Noise rejection working ✓

### Step 3: Transfer to Second Test PC

**Option A: Standalone Executable (Recommended)**

```powershell
# Build .exe
pip install pyinstaller
python build_standalone.py

# Copy to USB stick:
# dist/microscope_audio_test.exe
```

**Option B: Python Script (if Python installed on test PC)**

Copy to USB stick:
- `audio_protocol.py`
- `microscope_audio_test.py`
- `requirements.txt`

On test PC:
```powershell
pip install -r requirements.txt
python microscope_audio_test.py
```

### Step 4: Run Test on Second PC

Run the same test - all 6 tests should pass on both PCs.

### Step 5: Two-PC Communication Test

**On PC 1 (sender):**
```python
from audio_protocol import MicroscopeAudioController, Command

controller = MicroscopeAudioController()
controller.send_command(Command.PING)
print("Sent PING - listen on other PC!")
```

**On PC 2 (receiver):**
```python
from audio_protocol import MicroscopeAudioController

controller = MicroscopeAudioController()
cmd = controller.wait_for_command(timeout=30)
print(f"Received: {cmd.name if cmd else 'Nothing'}")
```

Position speaker near microphone between the two PCs. If you receive the PING command, the system is working! 🎧

---

## Troubleshooting

### No audio output?
- Check volume is up (>50%)
- Verify speakers/headphones plugged in
- Test with: `powershell -c "[console]::beep(1000,500)"`

### No audio input?
- Check microphone is plugged in
- Open Windows Sound settings → Recording devices
- Verify microphone is not muted
- Test levels while speaking

### FSK protocol fails?
- **Audio loopback may not work** - use separate speaker/mic
- Position speaker close to microphone (within 1 meter)
- Reduce background noise
- Increase volume on sender PC

### Checksum errors?
- Audio quality too low
- Too much background noise
- Increase speaker volume
- Move speaker closer to microphone

---

## Next Steps (After Successful Testing)

Once both test PCs pass:

1. **Build microscope control software** (`microscope_control.exe`)
2. **Integrate with `run_protocol_cli.py`** on microfluidics PC
3. **Add YAML command:** `microscope_capture: 0`
4. **Deploy to production** microscope PC

---

## Production Usage (Future)

### On Microfluidics PC (this computer)

Add to YAML config:
```yaml
required hardware:
  microscope: true

run:
  - pump_on: full flow
  - microscope_capture: 0  # Trigger + wait for completion
  - duration: 5
  - pump_off: 0
```

### On Microscope PC (airgapped)

Run `microscope_control.exe`:
- Listens for `CAPTURE` command via audio
- Triggers microscope image capture
- Sends `DONE` response when complete

---

## Technical Details

**Why FSK instead of simple beeps?**
- Digital data transmission (not just "beep = trigger")
- Error detection with checksums
- Multiple commands supported
- Immune to false triggers

**Why so slow (10 baud)?**
- Maximum reliability over acoustic channel
- Better noise immunity
- Easier frequency discrimination
- Still fast enough for microscope control (1.3s per command)

**Can someone talking trigger it?**
- No! Requires sustained 2400 Hz preamble for 500ms
- Human speech doesn't create pure sustained tones
- Checksum prevents random noise from being decoded as valid command

---

## Safety Features Summary

✓ Preamble prevents false triggers from speech  
✓ Checksum detects corrupted transmissions  
✓ Frequency tolerance handles speaker variations  
✓ 1.3s transmission too long for accidental patterns  
✓ Minimum signal power filters out distant noise  
✓ Auto-retry logic for failed transmissions






This will record audio and show detected frequencies in real-time.
Run simple_tone_generator.py on the SENDER computer.

Available audio input devices:
  [0] Microsoft Sound Mapper - Input
  [1] Line In (Realtek(R) Audio)
  [2] Headset (Lenovo Wireless VoIP H
  [8] Primary Sound Capture Driver
  [9] Line In (Realtek(R) Audio)
  [10] Headset (Lenovo Wireless VoIP Headset)
  [20] Line In (Realtek(R) Audio)
  [21] Headset (Lenovo Wireless VoIP Headset)
  [23] Line In (Realtek HD Audio Line input)
  [24] Stereo Mix (Realtek HD Audio Stereo input)
  [25] Microphone (Realtek HD Audio Mic input)
  [31] Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0
;(Lenovo Wireless VoIP Headset))
  [33] Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0
;(WH-1000XM4))

Select input device (press Enter for default): 0

======================================================================
LISTENING... (Press Ctrl+C to stop)
======================================================================

[Chunk 1] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0014
  Top frequencies detected:

[Chunk 2] Recording 1.0s...
  RMS: 0.0014  |  Max: 0.0088
  Top frequencies detected:

[Chunk 3] Recording 1.0s...
  RMS: 0.0034  |  Max: 0.0088
  Top frequencies detected:

[Chunk 4] Recording 1.0s...
  RMS: 0.0043  |  Max: 0.0088
  Top frequencies detected:

[Chunk 5] Recording 1.0s...
  RMS: 0.0020  |  Max: 0.0088
  Top frequencies detected:

[Chunk 6] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 7] Recording 1.0s...
  RMS: 0.0044  |  Max: 0.0089
  Top frequencies detected:

[Chunk 8] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 9] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 10] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 11] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 12] Recording 1.0s...
  RMS: 0.0062  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 13] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 14] Recording 1.0s...
  RMS: 0.0062  |  Max: 0.0089
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 15] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 16] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 17] Recording 1.0s...
  RMS: 0.0005  |  Max: 0.0020
  Top frequencies detected:

[Chunk 18] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0027
  Top frequencies detected:

[Chunk 19] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0023
  Top frequencies detected:

[Chunk 20] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0022
  Top frequencies detected:

[Chunk 21] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0008
  Top frequencies detected:

[Chunk 22] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0009
  Top frequencies detected:

[Chunk 23] Recording 1.0s...
  RMS: 0.0005  |  Max: 0.0023
  Top frequencies detected:

[Chunk 24] Recording 1.0s...
  RMS: 0.0049  |  Max: 0.0089
  Top frequencies detected:
    1.   300.0 Hz  (magnitude:        122)

[Chunk 25] Recording 1.0s...
  RMS: 0.0047  |  Max: 0.0088
  Top frequencies detected:
    1.   500.0 Hz  (magnitude:        113)

[Chunk 26] Recording 1.0s...
  RMS: 0.0015  |  Max: 0.0088
  Top frequencies detected:

[Chunk 27] Recording 1.0s...
  RMS: 0.0048  |  Max: 0.0088
  Top frequencies detected:
    1.   700.0 Hz  (magnitude:        116)

[Chunk 28] Recording 1.0s...
  RMS: 0.0049  |  Max: 0.0088
  Top frequencies detected:
    1.  1000.0 Hz  (magnitude:        122)

[Chunk 29] Recording 1.0s...
  RMS: 0.0013  |  Max: 0.0085
  Top frequencies detected:

[Chunk 30] Recording 1.0s...
  RMS: 0.0036  |  Max: 0.0070
  Top frequencies detected:

[Chunk 31] Recording 1.0s...
  RMS: 0.0049  |  Max: 0.0089
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        125)

[Chunk 32] Recording 1.0s...
  RMS: 0.0019  |  Max: 0.0088
  Top frequencies detected:

[Chunk 33] Recording 1.0s...
  RMS: 0.0045  |  Max: 0.0088
  Top frequencies detected:
    1.  1800.0 Hz  (magnitude:        102)

[Chunk 34] Recording 1.0s...
  RMS: 0.0051  |  Max: 0.0089
  Top frequencies detected:
    1.  2000.0 Hz  (magnitude:        134)

[Chunk 35] Recording 1.0s...
  RMS: 0.0021  |  Max: 0.0087
  Top frequencies detected:

[Chunk 36] Recording 1.0s...
  RMS: 0.0042  |  Max: 0.0085
  Top frequencies detected:

[Chunk 37] Recording 1.0s...
  RMS: 0.0053  |  Max: 0.0089
  Top frequencies detected:
    1.  3000.0 Hz  (magnitude:        139)

[Chunk 38] Recording 1.0s...
  RMS: 0.0024  |  Max: 0.0089
  Top frequencies detected:

[Chunk 39] Recording 1.0s...
  RMS: 0.0043  |  Max: 0.0090
  Top frequencies detected:

[Chunk 40] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 41] Recording 1.0s...
  RMS: 0.0014  |  Max: 0.0087
  Top frequencies detected:

[Chunk 42] Recording 1.0s...
  RMS: 0.0016  |  Max: 0.0090
  Top frequencies detected:

[Chunk 43] Recording 1.0s...
  RMS: 0.0049  |  Max: 0.0093
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        124)

[Chunk 44] Recording 1.0s...
  RMS: 0.0047  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        112)

[Chunk 45] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 46] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 47] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 48] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 49] Recording 1.0s...
  RMS: 0.0048  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        118)

[Chunk 50] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 51] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 52] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0089
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 53] Recording 1.0s...
  RMS: 0.0042  |  Max: 0.0088
  Top frequencies detected:

[Chunk 54] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 55] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 56] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0014
  Top frequencies detected:

[Chunk 57] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0009
  Top frequencies detected:

[Chunk 58] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0009
  Top frequencies detected:

[Chunk 59] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0009
  Top frequencies detected:

[Chunk 60] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0009
  Top frequencies detected:

[Chunk 61] Recording 1.0s...
  RMS: 0.0003  |  Max: 0.0009
  Top frequencies detected:

[Chunk 62] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0010
  Top frequencies detected:

[Chunk 63] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0011
  Top frequencies detected:

[Chunk 64] Recording 1.0s...
  RMS: 0.0008  |  Max: 0.0050
  Top frequencies detected:

[Chunk 65] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0034
  Top frequencies detected:

[Chunk 66] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0012
  Top frequencies detected:

[Chunk 67] Recording 1.0s...
  RMS: 0.0004  |  Max: 0.0010
  Top frequencies detected:

[Chunk 68] Recording 1.0s...
  RMS: 0.0005  |  Max: 0.0023
  Top frequencies detected:

[Chunk 69] Recording 1.0s...
  RMS: 0.0053  |  Max: 0.0089
  Top frequencies detected:
    1.   300.0 Hz  (magnitude:        143)

[Chunk 70] Recording 1.0s...
  RMS: 0.0043  |  Max: 0.0088
  Top frequencies detected:

[Chunk 71] Recording 1.0s...
  RMS: 0.0024  |  Max: 0.0088
  Top frequencies detected:

[Chunk 72] Recording 1.0s...
  RMS: 0.0052  |  Max: 0.0088
  Top frequencies detected:
    1.   700.0 Hz  (magnitude:        140)

[Chunk 73] Recording 1.0s...
  RMS: 0.0043  |  Max: 0.0088
  Top frequencies detected:

[Chunk 74] Recording 1.0s...
  RMS: 0.0023  |  Max: 0.0088
  Top frequencies detected:

[Chunk 75] Recording 1.0s...
  RMS: 0.0041  |  Max: 0.0070
  Top frequencies detected:
    1.  1200.0 Hz  (magnitude:        110)

[Chunk 76] Recording 1.0s...
  RMS: 0.0043  |  Max: 0.0088
  Top frequencies detected:

[Chunk 77] Recording 1.0s...
  RMS: 0.0021  |  Max: 0.0088
  Top frequencies detected:

[Chunk 78] Recording 1.0s...
  RMS: 0.0051  |  Max: 0.0088
  Top frequencies detected:
    1.  1800.0 Hz  (magnitude:        131)

[Chunk 79] Recording 1.0s...
  RMS: 0.0045  |  Max: 0.0089
  Top frequencies detected:
    1.  2000.0 Hz  (magnitude:        103)

[Chunk 80] Recording 1.0s...
  RMS: 0.0019  |  Max: 0.0088
  Top frequencies detected:

[Chunk 81] Recording 1.0s...
  RMS: 0.0048  |  Max: 0.0085
  Top frequencies detected:
    1.  2400.0 Hz  (magnitude:        120)

[Chunk 82] Recording 1.0s...
  RMS: 0.0050  |  Max: 0.0090
  Top frequencies detected:
    1.  3000.0 Hz  (magnitude:        123)

[Chunk 83] Recording 1.0s...
  RMS: 0.0015  |  Max: 0.0089
  Top frequencies detected:

[Chunk 84] Recording 1.0s...
  RMS: 0.0047  |  Max: 0.0090
  Top frequencies detected:
    1.  4000.0 Hz  (magnitude:        109)

[Chunk 85] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 86] Recording 1.0s...
  RMS: 0.0017  |  Max: 0.0087
  Top frequencies detected:

[Chunk 87] Recording 1.0s...
  RMS: 0.0018  |  Max: 0.0088
  Top frequencies detected:

[Chunk 88] Recording 1.0s...
  RMS: 0.0047  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        113)

[Chunk 89] Recording 1.0s...
  RMS: 0.0048  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        120)

[Chunk 90] Recording 1.0s...
  RMS: 0.0061  |  Max: 0.0088
  Top frequencies detected:
    1.  1500.0 Hz  (magnitude:        191)

[Chunk 91] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 92] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 93] Recording 1.0s...
  RMS: 0.0000  |  Max: 0.0002
  Top frequencies detected:

[Chunk 94] Recording 1.0s...


======================================================================
STOPPED
======================================================================

Review the frequencies detected above.

Look for:
  - Did you see the expected frequencies (300, 500, 1200, 1800, 2400 Hz)?
  - Were some frequencies clearer than others?
  - Was there a lot of background noise?

If specific frequencies were NOT detected:
  1. Move speaker closer to microphone
  2. Increase volume on sender
  3. Try those frequencies might not work well in your setup
======================================================================