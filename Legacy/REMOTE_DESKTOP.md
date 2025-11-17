# Remote Desktop Control for Microscope

**The new default microscope control mode** - Control your air-gapped microscope PC over direct ethernet connection with live screen viewing and remote clicking.

## 🎯 What This Does

This system provides **full remote desktop capabilities** between two PCs connected via ethernet cable:

- **Live screen viewing** - See the microscope PC screen in real-time
- **Remote clicking** - Click anywhere on the remote screen (coordinates automatically translated)
- **Protocol integration** - Automated button clicking during experiments
- **Zero configuration** - Plug in ethernet cable and go (auto-discovery via UDP broadcast)
- **Air-gap friendly** - Perfect for isolated microscope PCs with no network access

## 🔌 Hardware Setup

### Direct Ethernet Connection

1. **Connect the PCs:**
   - Use standard ethernet cable (CAT5e/CAT6)
   - Connect directly between controller PC and microscope PC
   - Modern NICs support auto-MDI-X (no crossover cable needed)

2. **Windows will auto-configure:**
   - Both PCs get link-local addresses (169.254.x.x)
   - No manual IP configuration required
   - Takes ~30 seconds after plugging in

3. **Verify connection:**
   ```powershell
   # On either PC, check for 169.254.x.x address
   ipconfig
   
   # Look for "Autoconfiguration IPv4 Address" in ethernet adapter section
   ```

### Firewall Configuration

Windows Firewall must allow ports **50123-50125** on both PCs:

```powershell
# Run on BOTH PCs (controller and microscope):

# Discovery port (UDP)
New-NetFirewallRule -DisplayName "Remote Desktop Discovery" -Direction Inbound -Protocol UDP -LocalPort 50123 -Action Allow

# Command port (TCP)
New-NetFirewallRule -DisplayName "Remote Desktop Commands" -Direction Inbound -Protocol TCP -LocalPort 50124 -Action Allow

# Screenshot port (TCP)
New-NetFirewallRule -DisplayName "Remote Desktop Screenshots" -Direction Inbound -Protocol TCP -LocalPort 50125 -Action Allow
```

## 🚀 Quick Start

### On Microscope PC:

1. **Install dependencies:**
   ```powershell
   uv sync
   ```

2. **Start the server:**
   ```powershell
   uv run python remote_desktop_server.py
   ```

You should see:
```
============================================================
Remote Desktop Server
============================================================
Server IPs: 169.254.x.x
Screen: 1920x1080
Ready for connections...
Press Ctrl+C to stop
```

### On Controller PC:

#### Option 1: Live GUI Control

For manual remote control with live screen viewing:

```powershell
uv run python remote_desktop_client.py
```

This opens a window showing the microscope PC screen. You can:
- Click anywhere to control the remote mouse
- Right-click for context menus
- Adjust FPS (frames per second) for screen refresh rate
- Toggle auto-refresh on/off

#### Option 2: Protocol Automation

For automated experiments integrated with pump/valve control:

```powershell
uv run python run_protocol_cli.py config_examples/remote_desktop_example.yaml
```

The protocol will automatically:
1. Discover the microscope server
2. Execute pump/valve sequences
3. Find and click the "run.png" button when `microscope: run` is encountered
4. Continue with the protocol

## 📝 YAML Configuration

The microscope controller is now **always remote desktop** - no mode selection needed!

```yaml
# Hardware requirements
required hardware:
  pump: true
  valve: true
  microscope: true  # Enables remote desktop control

# Protocol sequence
run:
  - pump_on: my_profile
  - wait: 5
  
  # Trigger microscope acquisition
  - microscope: run  # Finds and clicks "run.png" on remote screen
  
  - wait: 10
  - pump_off: 0
```

### Image Recognition for Button Clicking

The `microscope: run` command uses image recognition to find and click buttons:

1. **Capture the button image:**
   - Take a screenshot of the button you want to click
   - Crop it to just the button (include some surrounding context)
   - Save as `run.png` in the project root directory

2. **Adjust confidence (optional):**
   ```python
   # In src/microscope.py, change confidence threshold:
   def run(self, image_path: str = "run.png", confidence: float = 0.8):
   ```

Lower confidence (e.g., 0.7) = more lenient matching
Higher confidence (e.g., 0.9) = stricter matching

## 🎮 Remote Desktop Client Controls

When running `remote_desktop_client.py`:

| Control | Action |
|---------|--------|
| Left click | Click at position on remote screen |
| Right click | Right-click at position on remote screen |
| FPS spinner | Adjust screen refresh rate (1-30 FPS) |
| Refresh Now button | Manually grab latest screenshot |
| Auto-refresh checkbox | Enable/disable automatic screen updates |

**Coordinate translation is automatic** - the client handles scaling and position mapping from your local window to the remote screen coordinates.

## 🔧 Advanced Usage

### Direct API Access

You can control the microscope directly from Python:

```python
from src.microscope import Microscope

# Initialize and connect
microscope = Microscope()
if microscope.initialize():
    # Find and click a button
    microscope.run(image_path="run.png")
    
    # Click at specific coordinates
    microscope.click(x=500, y=300, button='left')
    
    # Type text
    microscope.type_text("Hello from controller PC!")
    
    # Press keys
    microscope.press_key('enter')
    
    # Cleanup
    microscope.close()
```

### Network Architecture

```
Controller PC                     Microscope PC
─────────────                     ─────────────
                Ethernet Cable
run_protocol_cli.py  ──────────►  remote_desktop_server.py
       │                                 │
       │  UDP:50123 Discovery           │
       │◄───────────────────────────────┤
       │                                 │
       │  TCP:50124 Commands             │
       ├────────────────────────────────►│
       │  (click, type, find_and_click)  │
       │                                 │
       │  TCP:50125 Screenshots          │
       │◄───────────────────────────────┤
       │  (JPEG compressed, base64)      │
```

### Port Usage

| Port | Protocol | Purpose |
|------|----------|---------|
| 50123 | UDP | Auto-discovery (broadcast) |
| 50124 | TCP | Control commands (click, type, etc.) |
| 50125 | TCP | Screenshot streaming |

## 🐛 Troubleshooting

### Server Not Found

**Symptom:** Client says "Server not found - check connection"

**Solutions:**
1. Verify ethernet cable is connected (check link lights on both NICs)
2. Check both PCs have 169.254.x.x addresses: `ipconfig`
3. Disable VPN software (can interfere with link-local addressing)
4. Verify firewall rules are set on **both** PCs
5. Wait 30-60 seconds after plugging in cable for auto-configuration

### Slow Screen Refresh

**Symptom:** Remote desktop client updates slowly

**Solutions:**
1. Lower the FPS setting (reduces network load)
2. Decrease `SCREENSHOT_QUALITY` in `remote_desktop_server.py` (line 18)
3. Decrease `SCREENSHOT_SCALE` to 0.5 for half-resolution (faster transfer)
4. Check for other network activity on the ethernet connection

### Button Not Found

**Symptom:** `microscope: run` reports "Run button not found"

**Solutions:**
1. Verify `run.png` exists in project root directory
2. Capture a fresh screenshot of the button (lighting/scaling may have changed)
3. Lower confidence threshold: `microscope.run(confidence=0.7)`
4. Ensure the button is visible on screen (not minimized or covered)

### Click Coordinates Wrong

**Symptom:** Clicks land in wrong location on remote screen

**Solutions:**
1. This is automatically handled - should not occur
2. If it does, verify `pyautogui.size()` matches actual screen resolution
3. Check for multi-monitor setups (currently assumes primary monitor only)

## 🔄 Migration from Audio Mode

If you were using audio-based microscope control (`microscope_audio.py`):

1. **Remove audio cables** - No longer needed!
2. **Connect ethernet cable** - Between controller and microscope PCs
3. **Update YAML configs** - Remove `microscope_mode` field (ethernet is default)
4. **Start server** - Run `remote_desktop_server.py` on microscope PC
5. **Test protocol** - Everything else works the same!

The new remote desktop mode:
- ✅ More reliable (no audio signal degradation)
- ✅ Faster (network vs audio bandwidth)
- ✅ Interactive (can see and click anywhere)
- ✅ Easier setup (no volume calibration)
- ✅ Better debugging (see what's happening on microscope PC)

## 📦 Dependencies

All dependencies are already in `pyproject.toml`:

```toml
dependencies = [
    "pyautogui>=0.9.54",    # Screen control
    "pillow>=10.0.0",        # Image processing
    "opencv-python>=4.8.0",  # Image recognition
]
```

Install with: `uv sync`

## 🎯 Performance Tips

### For Protocol Automation (run_protocol_cli.py)

- The microscope controller uses minimal bandwidth (only sends commands)
- No continuous screen streaming during protocol execution
- Discovery happens once at initialization
- Commands are lightweight JSON over TCP

### For Interactive Control (remote_desktop_client.py)

- Start with 5 FPS and adjust as needed
- Lower FPS = less network load, more battery life
- Higher FPS = smoother interaction, more responsive
- Use manual refresh for infrequent checks
- Disable auto-refresh when not actively using

### Screenshot Optimization

Edit `remote_desktop_server.py`:

```python
# Line 18-20
SCREENSHOT_QUALITY = 75  # Lower = smaller files (50-100)
SCREENSHOT_SCALE = 1.0   # Half-res: 0.5, quarter: 0.25
MAX_FPS = 10             # Rate limit for protection
```

## 🔐 Security Notes

This is designed for **direct ethernet connection only** (link-local addressing):

- ✅ No internet exposure
- ✅ No routing beyond local cable
- ✅ Perfect for air-gapped setups
- ⚠️ Not encrypted (assumes physical security of cable)
- ⚠️ Do not use over public/shared networks

If you need to run over a network, add SSH tunneling or VPN.

## 🚧 Known Limitations

- **Single monitor only** - Currently assumes primary display
- **No keyboard shortcuts** - Can only send individual keys or text
- **No drag operations** - Only click, not click-and-drag
- **Windows only** - Uses Windows-specific link-local networking
- **No file transfer** - Screen and control only (future enhancement)

## 📄 Related Files

- `remote_desktop_server.py` - Server for microscope PC
- `remote_desktop_client.py` - Interactive GUI client
- `src/microscope.py` - Protocol integration (default mode)
- `src/microscope_audio.py` - Legacy audio mode (still available)
- `src/microscope_ethernet.py` - Command-only mode (no GUI)
- `config_examples/remote_desktop_example.yaml` - Example protocol

---

**Enjoy seamless remote control of your air-gapped microscope! 🎉**
