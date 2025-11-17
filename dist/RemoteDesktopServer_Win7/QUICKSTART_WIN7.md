# Quick Setup Guide for Windows 7

## Step-by-Step Installation

### Step 1: Copy Files to Windows 7 PC

Copy this entire folder to your Windows 7 computer. You can:

**Option A: Use USB drive**
1. Copy `RemoteDesktopServer_Win7` folder to USB drive
2. Plug USB into Windows 7 PC
3. Copy folder to `C:\Program Files\RemoteDesktopServer_Win7`

**Option B: Use network share** (if available)
1. From Windows 11 PC: Share is already at `\\BIPHUB\RemoteDesktopServer_Win7`
2. From Windows 7 PC: Open `\\BIPHUB\RemoteDesktopServer_Win7`
3. Copy all files to `C:\Program Files\RemoteDesktopServer_Win7`

### Step 2: First Run

1. **Right-click** on `start_server.bat`
2. Choose **"Run as Administrator"** (important!)
3. The server will:
   - Create `C:\RemoteDesktop` folder
   - Start monitoring for commands
   - Show: "Waiting for commands from client..."

### Step 3: Share the Folder

Now make `C:\RemoteDesktop` accessible from your other PC:

1. Open `C:\RemoteDesktop` in Explorer
2. Right-click the folder → **Properties**
3. Go to **Sharing** tab
4. Click **"Advanced Sharing..."**
5. Check **"Share this folder"**
6. Share name: `RemoteDesktop`
7. Click **"Permissions"**
8. Add **"Everyone"**
9. Grant **"Full Control"**
10. Click **OK**, **OK**, **OK**

### Step 4: Note the Network Path

Windows will show the network path, something like:

```
\\MICROSCOPE-PC\RemoteDesktop
```

Write this down - you'll need it for the client!

### Step 5: Test from Other PC

From your Windows 11 PC:

1. Open File Explorer
2. Type in address bar: `\\MICROSCOPE-PC\RemoteDesktop`
3. You should see a file: `response.json`
4. Try creating a test file - if you can, networking is working!

## What You Should See

### On Windows 7 (Server):

```
=== Remote Desktop Server for Windows 7 ===

Creating folder: C:\RemoteDesktop
Starting server...
Shared folder: C:\RemoteDesktop

Server will monitor this folder for command.json files
Press Ctrl+C to exit

=== Remote Desktop Server for Windows 7 ===
Compatible with Python remote desktop client

Using shared folder: C:\RemoteDesktop
Press Ctrl+C to exit

Remote Desktop Server Started
Shared Folder: C:\RemoteDesktop
Waiting for commands from client...
```

### In C:\RemoteDesktop:

You should see this file appear:

**response.json:**
```json
{"status":"ready","timestamp":"2025-11-17T16:44:47.2029384+01:00"}
```

## Testing the Connection

### From Windows 11 PC:

Create a test command file:

1. Open Notepad
2. Type:
```json
{"action":"screenshot"}
```
3. Save as: `\\MICROSCOPE-PC\RemoteDesktop\command.json`

### Watch Windows 7 Console:

You should see:
```
Command: screenshot
Screenshot saved: C:\RemoteDesktop\screenshot.jpg
```

### Check the Network Share:

You should now see:
```
\\MICROSCOPE-PC\RemoteDesktop\
├── command.json
├── response.json
└── screenshot.jpg
```

## Troubleshooting

**Server won't start:**
- Run as Administrator
- Check if .NET Framework 4 is installed (should be on Win7 SP1)

**Can't create C:\RemoteDesktop:**
- Choose a different folder: `start_server.bat C:\Test`
- Or run as Administrator

**Can't access \\MICROSCOPE-PC from other PC:**
- Check firewall settings
- Enable "File and Printer Sharing" in Windows 7
- Make sure both PCs are on same network
- Try using IP address instead: `\\192.168.x.x\RemoteDesktop`

**Error: CLR20r3 System.ArgumentException:**
- See `TROUBLESHOOTING_WIN7.md` for detailed solutions

## Network Settings (if needed)

If you can't access the share from the other PC:

1. **Open Windows Firewall:**
   - Control Panel → Windows Firewall
   - Click "Allow a program through Windows Firewall"
   - Check "File and Printer Sharing" for both Home/Work and Public

2. **Check Network Location:**
   - Control Panel → Network and Sharing Center
   - Make sure network is "Home network" or "Work network" (not Public)

3. **Enable Network Discovery:**
   - Network and Sharing Center
   - Change advanced sharing settings
   - Turn on "Network discovery"
   - Turn on "File and printer sharing"

## Using with Python Client

Once the server is running and the share is accessible:

```python
from pathlib import Path
import json
import time

# Use the network path
shared = Path(r"\\MICROSCOPE-PC\RemoteDesktop")

# Send a click command
command = {
    "action": "click",
    "x": 500,
    "y": 300,
    "button": "left"
}

with open(shared / "command.json", "w") as f:
    json.dump(command, f)

# Wait for response
time.sleep(0.5)

with open(shared / "response.json") as f:
    response = json.load(f)
    print(response)  # Should show: {"status": "ok", "action": "click"}
```

## Summary Checklist

- [ ] Files copied to Windows 7 PC
- [ ] `start_server.bat` run as Administrator
- [ ] Server shows "Waiting for commands from client..."
- [ ] `C:\RemoteDesktop` folder created
- [ ] `response.json` file exists
- [ ] Folder shared as `\\MICROSCOPE-PC\RemoteDesktop`
- [ ] Can access share from Windows 11 PC
- [ ] Can create/delete files in the share from Windows 11
- [ ] Test command works (screenshot command)

## Files You Should Have

```
C:\Program Files\RemoteDesktopServer_Win7\
├── RemoteDesktopServer.exe    ← The program
├── Newtonsoft.Json.dll        ← JSON library
├── mscorlib.dll               ← .NET runtime
├── norm*.nlp                  ← Unicode files
├── start_server.bat           ← Easy launcher
├── README.md                  ← Full documentation
├── TROUBLESHOOTING_WIN7.md    ← Problem solving
└── QUICKSTART_WIN7.md         ← This file

C:\RemoteDesktop\              ← Working folder (created by server)
├── command.json               ← Commands from client
├── response.json              ← Status from server
└── screenshot.jpg             ← Screenshots (when requested)
```

## Need Help?

See `TROUBLESHOOTING_WIN7.md` for detailed error solutions.

The server includes detailed error messages - any problems will be shown in the console window.
