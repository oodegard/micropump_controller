# Microscope Remote Desktop Server - Quick Start

## Setup (One Time)

### 1. Build the C# Server
From the repo root, run:
```powershell
C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe remote_desktop_server_cs\RemoteDesktopServer.csproj /p:Configuration=Release
```

This builds the server to: `remote_desktop_server_cs\bin\Release\RemoteDesktopServer.exe`

### 2. Share the Repo Folder
Share this entire repo as a network share:
1. Right-click `C:\git\micropump_controller` → Properties → Sharing → Advanced Sharing
2. **Share name**: `micropump_controller`
3. **Permissions**: Read/Write for users who need access
4. **Network path**: `\\BIPHUB\micropump_controller`

The server will create these subfolders automatically:
```
\\BIPHUB\micropump_controller\
├── status\           # command.json, response.json, screenshot.jpg (auto-created)
├── buttons\          # Button template images (copy from dist\RemoteDesktopServer_Win7\buttons\)
└── ... (rest of repo files)
```

Copy button templates to the share:
```powershell
Copy-Item "dist\RemoteDesktopServer_Win7\buttons\*" -Destination "\\BIPHUB\micropump_controller\buttons\" -Recurse
```

## Running the Server

### Option 1: From Repo Root (Recommended)
Double-click `start_microscope_server.bat` in the repo root, or run:
```powershell
.\start_microscope_server.bat
```

This runs the server directly from the build output folder - **no file copying needed!**

### Option 2: Custom Shared Folder
```powershell
.\start_microscope_server.bat "C:\CustomPath"
```

## Running Python Client

From repo root:
```powershell
uv run python run_protocol_cli.py config_examples\microscope_run_test.yaml
```

## After Code Changes

### C# Server Changes
Just rebuild and restart:
```powershell
# Rebuild
C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe remote_desktop_server_cs\RemoteDesktopServer.csproj /p:Configuration=Release

# Stop server (Ctrl+C), then restart
.\start_microscope_server.bat
```

### Python Client Changes
No build needed - just run the script again.

## Network Share Setup

### Windows Share Configuration
1. Right-click `C:\git\micropump_controller` → Properties → Sharing
2. Click "Advanced Sharing"
3. Check "Share this folder"
4. Share name: `micropump_controller`
5. Click "Permissions" → Add users → Grant Read/Write access
6. Click OK to save

### Verify Access
From the Windows 7 microscope PC or another computer:
```cmd
dir \\BIPHUB\micropump_controller
```

You should see the repo files. The server will auto-create `status\` and you should copy button images to `buttons\`.

## Advantages of This Setup

✅ No manual file copying after rebuilds
✅ Server runs latest code automatically
✅ Single source of truth (build output folder)
✅ Easy to share entire repo with team
✅ Version control covers everything
