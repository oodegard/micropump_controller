# Microscope Communication Modes

This project supports two modes for PC-to-PC communication to control the microscope:

## 🎵 Audio Mode (Default)

Uses audio cable (3.5mm jack) for communication via DTMF-like tones.

**Hardware:** Audio cable connecting microphone jacks on both PCs

**Pros:**
- Simple hardware (just an audio cable)
- No network configuration needed
- Works even if network ports are blocked

**Cons:**
- Requires volume adjustment
- Can be affected by noise
- Slower communication

**Setup:**
1. Connect audio cable between microphone jacks
2. Adjust input/output volumes in Windows Sound settings
3. Run: `python microscope_gui_control.py --mode audio`

## 🔌 Ethernet Mode (Recommended)

Uses direct ethernet cable for fast, reliable communication with zero configuration.

**Hardware:** Ethernet cable (crossover or modern auto-MDI-X cable) directly connecting both PCs

**Pros:**
- ✅ **Plug-and-play** - no network configuration required
- ✅ **Fast** - instant command transmission
- ✅ **Reliable** - no interference or volume issues
- ✅ **Auto-discovery** - PCs find each other automatically

**Cons:**
- Requires ethernet cable
- May need firewall exception (ports 50123-50124)

**Setup:**
1. Connect ethernet cable directly between both PCs
2. Windows will automatically configure link-local addressing
3. Run: `python microscope_gui_control.py --mode ethernet`

**Firewall Setup (if needed):**
```powershell
# Run as Administrator to allow firewall access
netsh advfirewall firewall add rule name="Microscope Discovery" dir=in action=allow protocol=UDP localport=50123
netsh advfirewall firewall add rule name="Microscope Commands" dir=in action=allow protocol=TCP localport=50124
```

## Usage Examples

### YAML Configuration

**Audio mode:**
```yaml
microscope_mode: audio  # or omit for default
required hardware:
  microscope: true
run:
  - microscope: run
```

**Ethernet mode:**
```yaml
microscope_mode: ethernet
required hardware:
  microscope: true
run:
  - microscope: run
```

### Command Line

**Sender PC (protocol controller):**
```powershell
# Audio mode
uv run python run_protocol_cli.py config_examples/microscope_test.yaml

# Ethernet mode
uv run python run_protocol_cli.py config_examples/microscope_ethernet_test.yaml
```

**Receiver PC (microscope GUI controller):**
```powershell
# Audio mode
uv run python microscope_gui_control.py --mode audio

# Ethernet mode (recommended)
uv run python microscope_gui_control.py --mode ethernet
```

## How Ethernet Mode Works

1. **Auto-Discovery:** When the sender PC wants to send a command, it broadcasts a UDP discovery packet
2. **Response:** The receiver PC responds with its IP address
3. **Command Transmission:** Sender establishes TCP connection and sends the command
4. **Acknowledgment:** Receiver sends acknowledgment and executes the button click
5. **Follow-up:** Receiver sends RUN_COMMAND_RECEIVED and RUN_DONE via the same mechanism

**No router, no DHCP, no configuration needed!** Windows automatically assigns link-local addresses (169.254.x.x) when a direct ethernet connection is detected.

## Choosing a Mode

**Use Audio Mode if:**
- You already have audio cables connected
- Ethernet ports are unavailable
- You want the simplest possible hardware setup

**Use Ethernet Mode if:**
- You want maximum reliability and speed
- You have a spare ethernet cable
- You're running many commands in sequence

## Troubleshooting

### Ethernet Mode
- **No peer found:** Check cable connection, ensure both scripts are running
- **Firewall blocked:** Run firewall commands above or temporarily disable firewall for testing
- **Connection timeout:** Check Windows network adapter is enabled

### Audio Mode
- **No signal detected:** Adjust input volume in Windows Sound settings
- **Wrong commands detected:** Reduce background noise, adjust DETECTION_THRESHOLD
- **Commands not heard:** Increase output volume, check cable connections
