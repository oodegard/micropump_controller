# Example Commands

This folder contains example JSON command files that demonstrate how to control the remote desktop server.

## Usage

To execute a command, copy one of these files to the shared folder as `command.json`:

```powershell
# From controller PC
Copy-Item "commands\click_example.json" "\\MICROSCOPE-PC\RemoteDesktop\command.json"
```

Or use Python:

```python
import json
import shutil
from pathlib import Path

# Copy example to active command file
shared = Path(r"\\MICROSCOPE-PC\RemoteDesktop")
shutil.copy("commands/click_example.json", shared / "command.json")
```

## Available Commands

### Mouse Click Commands
- `click_example.json` - Click at specific coordinates
- `click_center.json` - Click at screen center
- `right_click.json` - Right-click for context menu

### Keyboard Commands  
- `type_text.json` - Type a text string
- `press_enter.json` - Press Enter key
- `press_tab.json` - Press Tab key
- `press_escape.json` - Press Escape key

### Screenshot Commands
- `screenshot.json` - Capture current screen

### Server Control
- `shutdown.json` - Stop the server gracefully

## Creating Custom Commands

All commands follow the same JSON structure. See the examples for the exact format.

### Command Structure

```json
{
  "action": "command_name",
  "parameter1": "value1",
  "parameter2": "value2"
}
```

After the server processes a command, it updates `response.json` with the result.
