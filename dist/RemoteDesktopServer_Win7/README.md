# Remote Desktop Server for Windows 7

**Windows 7 SP1 Compatible .NET Application**

## What This Does
This program runs on your **Windows 7 microscope PC** and allows remote control from another computer over a network (ethernet). It uses **file-based communication** instead of network sockets, making it simple and reliable.

## Installation on Windows 7 PC

1. **Copy this entire folder** to the Windows 7 computer (e.g., to `C:\RemoteDesktop\`)

2. **Create a network share** that both computers can access:
   - On Windows 7: Right-click folder → Share with → Specific people
   - Share with: `Everyone` or your username
   - Permissions: `Read/Write`
   - Note the network path (e.g., `\\MICROSCOPE-PC\RemoteDesktop`)

3. **Run the server**: Double-click `start_server.bat`

## Requirements
- Windows 7 SP1 or later (fully compatible!)
- .NET Framework 4.0 (included with Windows 7)
- Network connection between PCs (ethernet cable recommended)
- Shared folder accessible from both computers

## How It Works

### File-Based Communication
The server monitors a **shared folder** for command files created by the client:

**Files:**
- `command.json` - Commands from the client (click, type, screenshot, etc.)
- `response.json` - Status responses from the server
- `screenshot.jpg` - Current screen capture (when requested)

**Supported Commands:**
- `click` - Click mouse at (x, y) coordinates
- `type` - Type text string
- `key` - Press special keys (Enter, Tab, Escape, etc.)
- `screenshot` - Capture current screen
- `shutdown` - Stop the server

### Example Command File (command.json):
```json
{
  "action": "click",
  "x": 500,
  "y": 300,
  "button": "left"
}
```

### Example Response File (response.json):
```json
{
  "status": "ok",
  "action": "click"
}
```

## Files in This Package
- `RemoteDesktopServer.exe` - Main executable (15 KB)
- `Newtonsoft.Json.dll` - JSON parsing library (585 KB)
- `mscorlib.dll` - .NET runtime (5.7 MB)
- `norm*.nlp` - Unicode normalization files
- `start_server.bat` - Convenience launcher
- `README.md` - This file

**Total Size: 6.8 MB**

## Usage from Python Client

The Python client on the controller PC writes command files to the shared folder:

```python
import json
import time
from pathlib import Path

shared_folder = Path(r"\\MICROSCOPE-PC\RemoteDesktop")

# Send click command
command = {"action": "click", "x": 500, "y": 300, "button": "left"}
with open(shared_folder / "command.json", "w") as f:
    json.dump(command, f)

# Wait for response
while not (shared_folder / "response.json").exists():
    time.sleep(0.1)

with open(shared_folder / "response.json") as f:
    response = json.load(f)
    print(response)  # {"status": "ok", "action": "click"}
```

## Troubleshooting

**Server doesn't start:**
- Check if .NET Framework 4.0 is installed (should be included in Win7)
- Run as Administrator if permission issues occur

**Commands not executing:**
- Verify shared folder path is correct
- Check both PCs can read/write to the shared folder
- Ensure firewall allows file sharing

**Screenshot quality:**
- Screenshots are saved as JPEG with 75% quality
- File size typically 50-200 KB depending on screen content

## Advantages Over Python Version

✅ **Windows 7 Compatible** - No DLL issues!
✅ **Small Size** - Only 6.8 MB vs 172 MB Python package
✅ **No Dependencies** - Uses .NET Framework 4.0 included in Windows 7
✅ **Reliable** - File-based communication is simple and robust
✅ **Battle-Tested** - Based on your working tracebot_oo project

## Network Share Setup

**On Microscope PC (Windows 7):**
```
1. Create folder: C:\RemoteDesktop
2. Copy all files from this package to C:\RemoteDesktop
3. Right-click folder → Properties → Sharing tab
4. Click "Advanced Sharing"
5. Check "Share this folder"
6. Name: RemoteDesktop
7. Click "Permissions" → Add "Everyone" → Grant "Full Control"
8. Note the network path shown (e.g., \\MICROSCOPE-PC\RemoteDesktop)
```

**On Controller PC (Windows 11):**
```
1. Open File Explorer
2. Type in address bar: \\MICROSCOPE-PC\RemoteDesktop
3. If prompted, enter username/password for microscope PC
4. Verify you can create/delete files in this folder
```

## Command Reference

### Click Command
```json
{
  "action": "click",
  "x": 500,          // Screen X coordinate
  "y": 300,          // Screen Y coordinate  
  "button": "left"   // "left" or "right"
}
```

### Type Command
```json
{
  "action": "type",
  "text": "Hello World"  // Text to type
}
```

### Key Press Command
```json
{
  "action": "key",
  "key": "enter"     // "enter", "tab", "escape", "space", etc.
}
```

### Screenshot Command
```json
{
  "action": "screenshot"
}
// Creates screenshot.jpg in shared folder
```

### Shutdown Command
```json
{
  "action": "shutdown"
}
// Stops the server gracefully
```

## Server Console Output

The server shows real-time status in the console window:

```
=== Remote Desktop Server for Windows 7 ===
Compatible with Python remote desktop client

Using shared folder: \\BIPHUB\RemoteDesktop
Press Ctrl+C to exit

Remote Desktop Server Started
Shared Folder: \\BIPHUB\RemoteDesktop
Waiting for commands from client...
Command: click
Clicked at (500, 300) - left button
Command: screenshot
Screenshot saved: \\BIPHUB\RemoteDesktop\screenshot.jpg
```

## Python Client Integration

See `remote_desktop_client.py` in the main project for a full GUI client that uses this server.

The client will be updated to use file-based communication instead of sockets.

## Security Notes

- The shared folder should be protected by Windows network permissions
- Consider using a dedicated user account for sharing
- Monitor the console for unexpected commands
- Close the server when not in use

## Technical Details

- **Language:** C# .NET Framework 4.0
- **Architecture:** File-based IPC (Inter-Process Communication)
- **Mouse Control:** Win32 API `mouse_event()`
- **Keyboard Control:** SendKeys.SendWait()
- **Screenshot:** Bitmap.CopyFromScreen()
- **JSON:** Newtonsoft.Json 13.0.3

Built with MSBuild from .NET Framework 4.0.30319
