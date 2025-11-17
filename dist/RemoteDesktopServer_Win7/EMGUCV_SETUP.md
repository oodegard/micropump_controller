# EmguCV Template Matching Setup

## Overview
The C# server now supports **template matching** to find and click buttons by image, just like the tracebot project.

## How It Works

### Command Format
```json
{
  "action": "find_and_click",
  "image": "run",
  "button": "left"
}
```

The server will:
1. Look for `buttons/run.png` in the shared folder
2. Take a screenshot of the microscope PC
3. Use template matching to find the button
4. Click at the center of the matched region

### Python Usage
```python
from src.microscope import Microscope

microscope = Microscope()
microscope.initialize()

# Will look for buttons/run.png and click it
microscope.run(image_path="run")  # or "run.png"
```

### YAML Usage
```yaml
run:
  - microscope: run    # Looks for buttons/run.png
  - duration: 2
```

## Installation Steps

### Step 1: Install EmguCV NuGet Packages

The C# code requires EmguCV for template matching. Download and install:

**Option A: Using NuGet Package Manager (recommended)**
```bash
cd remote_desktop_server_cs
nuget install EMGU.CV -Version 3.1.0 -OutputDirectory packages
```

**Option B: Download manually**
1. Go to https://www.nuget.org/packages/EMGU.CV/3.1.0
2. Download the package
3. Extract to `remote_desktop_server_cs/packages/EMGU.CV.3.1.0/`

### Step 2: Verify DLL Locations

The project expects DLLs at:
```
remote_desktop_server_cs/packages/EMGU.CV.3.1.0/lib/net40/
├── Emgu.CV.dll
├── Emgu.CV.UI.dll
├── Emgu.Util.dll
└── opencv_core310.dll (and other opencv DLLs)
```

###Step 3: Rebuild the Project

```bash
cd remote_desktop_server_cs
msbuild RemoteDesktopServer.csproj /p:Configuration=Release /t:Build
```

Or use Visual Studio:
- Open `RemoteDesktopServer.csproj`
- Build → Rebuild Solution

### Step 4: Copy DLLs to Distribution

After building, copy the EmguCV DLLs to the distribution folder:
```powershell
Copy-Item remote_desktop_server_cs\packages\EMGU.CV.3.1.0\lib\net40\*.dll -Destination dist\RemoteDesktopServer_Win7\ -Force
```

### Step 5: Create Button Templates

1. Take a screenshot of your microscope software
2. Crop the Run button (save as PNG)
3. Save to `buttons/run.png` in the shared folder

**Tip:** Make the button image small but distinctive - around 50x30 pixels works well.

##Button Template Guidelines

###Good Templates:
- Clear, high-contrast buttons
- Include unique text or icons
- Avoid plain backgrounds
- 30-100 pixels in each dimension

###Bad Templates:
- Generic shapes (plain rectangles)
- Low contrast
- Too large (slow matching)
- Too small (unreliable matching)

### Matching Threshold

The server uses 0.8 confidence threshold (80% match required).

To adjust, edit `RemoteDesktopServer.cs`:
```csharp
private const double MATCH_THRESHOLD = 0.8;  // Increase for stricter matching
```

## Troubleshooting

### "Button image not found"
- Check file exists in `buttons/` folder
- Verify `.png` extension
- Check file permissions

### "Button not found (max confidence: 0.xx)"
- Button appearance changed (window moved, resolution changed)
- Retake template screenshot
- Lower MATCH_THRESHOLD if button is similar but not identical
- Check button is visible (not covered by other windows)

### Build Errors "Emgu could not be found"
- Install EmguCV NuGet packages (see Step 1)
- Verify DLL locations (see Step 2)
- Check `.csproj` references point to correct paths

### Missing opencv_core DLL at runtime
- Copy all opencv DLLs from EmguCV package to distribution folder
- Include in deployment: `opencv_core310.dll`, `opencv_imgproc310.dll`, etc.

## Alternative: Coordinate-Based Clicking

If template matching setup is too complex, you can still use coordinate-based clicking:

```json
{
  "action": "click",
  "x": 450,
  "y": 120,
  "button": "left"
}
```

Template matching is more flexible (handles window movement) but coordinates are simpler to set up.
