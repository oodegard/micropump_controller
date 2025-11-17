# Quick Start: Remote Desktop Microscope Control

## 30-Second Setup

### Microscope PC:
```powershell
uv run python remote_desktop_server.py
```

### Controller PC:
```powershell
# Interactive GUI control:
uv run python remote_desktop_client.py

# OR automated protocol:
uv run python run_protocol_cli.py config_examples/remote_desktop_example.yaml
```

**That's it!** The PCs will find each other automatically.

---

## First Time Setup

### 1. Connect Hardware (one-time)

- Plug ethernet cable between controller PC and microscope PC
- Wait 30 seconds for auto-configuration

### 2. Configure Firewall (one-time, on BOTH PCs)

```powershell
# Copy-paste this into PowerShell as Administrator on BOTH PCs:

New-NetFirewallRule -DisplayName "Remote Desktop Discovery" -Direction Inbound -Protocol UDP -LocalPort 50123 -Action Allow
New-NetFirewallRule -DisplayName "Remote Desktop Commands" -Direction Inbound -Protocol TCP -LocalPort 50124 -Action Allow
New-NetFirewallRule -DisplayName "Remote Desktop Screenshots" -Direction Inbound -Protocol TCP -LocalPort 50125 -Action Allow
```

### 3. Prepare Button Image (for automation)

- Screenshot the button you want to click on microscope PC
- Crop to just the button area
- Save as `run.png` in project root
- Done!

---

## Usage Modes

### Mode 1: Interactive GUI (For Manual Control)

**When:** You want to see and control the microscope PC screen directly

**Run:**
```powershell
# On microscope PC:
uv run python remote_desktop_server.py

# On controller PC:
uv run python remote_desktop_client.py
```

**You get:**
- Live view of remote screen
- Click anywhere to control remote mouse
- Adjustable refresh rate (FPS slider)
- Right-click support

---

### Mode 2: Protocol Automation (For Experiments)

**When:** You want automated control during pump/valve experiments

**Run:**
```powershell
# On microscope PC:
uv run python remote_desktop_server.py

# On controller PC:
uv run python run_protocol_cli.py config_examples/remote_desktop_example.yaml
```

**YAML example:**
```yaml
required hardware:
  pump: true
  valve: true
  microscope: true  # Enables remote desktop

run:
  - pump_on: my_profile
  - wait: 5
  - microscope: run  # Finds and clicks "run.png"
  - wait: 10
  - pump_off: 0
```

**The protocol will:**
- Auto-discover microscope server
- Control pump/valve
- Find and click buttons on microscope PC
- Wait for acquisitions

---

## Troubleshooting

### "Server not found"
1. Check ethernet cable is plugged in
2. Verify firewall rules on BOTH PCs
3. Wait 30-60 seconds for network auto-config
4. Run `ipconfig` - look for 169.254.x.x address

### "Button not found"
1. Check `run.png` exists in project root
2. Take fresh screenshot of button
3. Lower confidence: edit `src/microscope.py`, change `confidence=0.7`

### Slow screen refresh
1. Lower FPS in GUI client
2. Edit `remote_desktop_server.py`: set `SCREENSHOT_QUALITY = 60`

---

## What's Different from Audio Mode?

| Feature | Audio Mode | Remote Desktop Mode |
|---------|------------|---------------------|
| **Cable** | 3.5mm audio | Ethernet |
| **Setup** | Volume calibration | Plug and play |
| **Speed** | ~1-2 seconds | ~100ms |
| **Reliability** | Signal degradation | Rock solid |
| **Debugging** | Blind (no visual) | See screen in real-time |
| **Interaction** | Commands only | Full mouse control |

**Bottom line:** Remote desktop is better in every way! 🚀

---

## Pro Tips

💡 **Leave server running** - Start `remote_desktop_server.py` on microscope PC and leave it running between experiments

💡 **Multiple protocols** - Run different YAML files without restarting the server

💡 **Test first** - Use interactive client to verify button location before running protocol

💡 **Snapshot images** - Take button screenshots at actual microscope screen resolution

💡 **Check logs** - Both server and client print useful connection/command info

---

## Next Steps

✅ Read full documentation: [`REMOTE_DESKTOP.md`](REMOTE_DESKTOP.md)

✅ See example YAML: [`config_examples/remote_desktop_example.yaml`](config_examples/remote_desktop_example.yaml)

✅ Explore API: [`src/microscope.py`](src/microscope.py)

---

**Ready to control your microscope! 😊**
