# Troubleshooting Windows 7 Issues

## Error: CLR20r3 System.ArgumentException

If you see this error when running `RemoteDesktopServer.exe` on Windows 7:

```
Problem Event Name: CLR20r3
Problem Signature 09: System.ArgumentException
```

This means the program couldn't access the shared folder path.

### Solution 1: Run with Local Folder Path

Instead of using a network path, use a **local folder**:

1. Create a folder on Windows 7:
   ```
   C:\RemoteDesktop
   ```

2. Run the server with this local path:
   ```batch
   RemoteDesktopServer.exe C:\RemoteDesktop
   ```

3. Then share `C:\RemoteDesktop` over the network:
   - Right-click `C:\RemoteDesktop`
   - Properties → Sharing → Advanced Sharing
   - Check "Share this folder"
   - Share name: `RemoteDesktop`
   - Permissions: Everyone → Full Control

4. Access from other PC:
   ```
   \\MICROSCOPE-PC\RemoteDesktop
   ```

### Solution 2: Run Without Arguments

The updated version defaults to the **current directory**:

```batch
cd C:\RemoteDesktop
RemoteDesktopServer.exe
```

This creates command/response files in the current folder.

### Solution 3: Use Batch File with Correct Path

Edit `start_server.bat`:

```batch
@echo off
REM Change this to your local folder
set FOLDER=C:\RemoteDesktop

REM Create folder if it doesn't exist
if not exist "%FOLDER%" mkdir "%FOLDER%"

REM Run server
cd /d "%FOLDER%"
"%~dp0RemoteDesktopServer.exe" "%FOLDER%"

pause
```

### Verify .NET Framework 4.0

Check if .NET Framework 4.0 is installed:

1. Open `Control Panel`
2. Programs and Features
3. Look for "Microsoft .NET Framework 4 Client Profile" or "Microsoft .NET Framework 4"

If not installed:
- Windows 7 SP1 should include it by default
- If missing, download from Microsoft: https://www.microsoft.com/download/details.aspx?id=17718

### Test the Server

After starting the server, you should see:

```
=== Remote Desktop Server for Windows 7 ===
Compatible with Python remote desktop client

Using shared folder: C:\RemoteDesktop
Press Ctrl+C to exit

Remote Desktop Server Started
Shared Folder: C:\RemoteDesktop
Waiting for commands from client...
```

And a file `response.json` should be created in the folder:

```json
{"status":"ready","timestamp":"2025-11-17T16:44:47.2029384+01:00"}
```

### Common Issues

**Issue:** "Access denied" when creating folder
- **Solution:** Run as Administrator (right-click → Run as Administrator)

**Issue:** Server starts but no response.json
- **Solution:** Check folder permissions - ensure the user can write to the folder

**Issue:** Network path not accessible
- **Solution:** Use local path first, then share the folder

**Issue:** Server crashes immediately
- **Solution:** Check error details in Event Viewer:
  - Run `eventvwr.msc`
  - Windows Logs → Application
  - Look for recent errors from RemoteDesktopServer.exe

### Debug Mode

To see detailed error messages, run from command prompt:

```batch
cd C:\RemoteDesktop
C:\path\to\RemoteDesktopServer.exe
```

Any errors will be printed to the console with full details.

### Expected Behavior

When working correctly:

1. **Server starts** - Shows "Waiting for commands from client..."
2. **response.json created** - Contains `{"status":"ready",...}`
3. **Console stays open** - Showing real-time command execution
4. **No error dialogs** - Server runs quietly until Ctrl+C

### If All Else Fails

1. Copy the entire error message from Event Viewer
2. Note the exact folder path you're using
3. Check if the folder exists and is writable
4. Try running in a simple path like `C:\Test` first

### Contact Information

The updated executable (from Nov 17, 2025) includes:
- Better error messages
- Path validation
- Directory creation
- Default to current directory
- Detailed exception logging

If you still see errors, the console will show exactly what went wrong.
