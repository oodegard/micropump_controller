# EmguCV Template Matching Setup Guide

## ✓ Installation Complete

EmguCV 3.1.0.1 has been successfully installed and integrated into the Remote Desktop Server.

## What Was Installed

- **EmguCV 3.1.0.1** - Computer vision library for .NET (OpenCV wrapper)
- **Native DLLs**:
  - `cvextern.dll` - EmguCV native library
  - `opencv_ffmpeg310_64.dll` - Video codec support
- **Managed Assemblies**:
  - `Emgu.CV.World.dll` - Main EmguCV library
  - `Emgu.CV.UI.dll` - UI components

## How Template Matching Works

The server can now automatically find and click buttons on the microscope software using image recognition.

### 1. Capture Button Screenshots

On the Windows 7 microscope PC:

1. Open the microscope software
2. Use the Snipping Tool or screenshot utility to capture individual buttons
3. Save each button as a PNG file (e.g., `Run1_start.png`, `Stop_button.png`)
4. Place the PNG files in the `buttons/` folder next to `RemoteDesktopServer.exe`

**Tips for good button screenshots:**
- Capture JUST the button, with minimal extra background
- Use PNG format for best quality
- Name the files descriptively (no spaces recommended)
- Capture buttons in their normal state (not hovered/pressed)

### 2. Configure YAML Protocol

In your YAML config file (e.g., `microscope_run_test.yaml`):

```yaml
required hardware:
  microscope: true

run:
  # Template matching - finds button automatically
  - microscope: Run1_start      # Looks for buttons/Run1_start.png
  - wait: 5
  - microscope: Stop_button     # Looks for buttons/Stop_button.png
```

### 3. Match Confidence Threshold

The server uses a **0.8 confidence threshold** (80% match required).

To adjust this, edit `RemoteDesktopServer.cs` line 40:
```csharp
private const double MATCH_THRESHOLD = 0.8;  // Change to 0.7 for more lenient matching
```

Lower values = more lenient (may click wrong buttons)
Higher values = more strict (may miss buttons)

## Fallback: Coordinate-Based Clicking

If template matching fails, you can still use direct coordinates:

```yaml
run:
  - microscope:
      action: click
      x: 450      # X pixel coordinate
      y: 120      # Y pixel coordinate
```

## Deployment

All necessary files are in `bin\Release\`:
- `RemoteDesktopServer.exe`
- `Emgu.CV.World.dll`
- `Emgu.CV.UI.dll`
- `cvextern.dll`
- `opencv_ffmpeg310_64.dll`
- `Newtonsoft.Json.dll`

Copy the entire `bin\Release\` folder to the Windows 7 PC.

## Troubleshooting

### Button not found errors

1. **Check the screenshot quality**: Make sure the button PNG is clear and matches the on-screen appearance
2. **Lower the threshold**: Try 0.7 or 0.75 instead of 0.8
3. **Check screen resolution**: Template matching is resolution-sensitive
4. **Use coordinate fallback**: If a specific button won't match, use `action: click` with x/y coordinates

### DLL not found errors

Make sure ALL DLLs are in the same folder as `RemoteDesktopServer.exe`:
- cvextern.dll (required!)
- opencv_ffmpeg310_64.dll
- Emgu.CV.World.dll
- Newtonsoft.Json.dll

### Server console output

The server logs helpful information:
```
Searching for button: Run1_start.png
Button found at (450, 120) with confidence 0.93
```

or:
```
Button not found (confidence: 0.65, threshold: 0.80)
```

## Building from Source

If you need to rebuild:

```powershell
# Restore NuGet packages
.\nuget.exe restore packages.config -PackagesDirectory packages

# Build with MSBuild
C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe RemoteDesktopServer.csproj /p:Configuration=Release
```

## Files Modified

- `packages.config` - Updated to EmguCV 3.1.0.1
- `RemoteDesktopServer.csproj` - Added EmguCV references and post-build DLL copying
- `RemoteDesktopServer.cs` - Uncommented EmguCV code (using statements and `FindButton()` method)
