"""
Test the C# Remote Desktop Server using file-based communication
This script demonstrates how the Python client will communicate with the C# server
"""

import json
import time
from pathlib import Path
import sys

def test_server(shared_folder: str):
    """Test the C# server by sending commands via JSON files"""
    
    shared = Path(shared_folder)
    command_file = shared / "command.json"
    response_file = shared / "response.json"
    screenshot_file = shared / "screenshot.jpg"
    
    print("=== Remote Desktop Server Test ===")
    print(f"Shared folder: {shared}")
    print()
    
    # Check if server is running (response.json should exist with "ready" status)
    if not response_file.exists():
        print("❌ Server not running! response.json not found.")
        print(f"   Start the server first: {shared / 'start_server.bat'}")
        return False
    
    try:
        with open(response_file) as f:
            initial_response = json.load(f)
            print(f"✅ Server status: {initial_response.get('status', 'unknown')}")
    except Exception as e:
        print(f"❌ Error reading response.json: {e}")
        return False
    
    print("\n--- Test 1: Screenshot ---")
    if test_screenshot(command_file, response_file, screenshot_file):
        print("✅ Screenshot test passed")
    else:
        print("❌ Screenshot test failed")
        return False
    
    print("\n--- Test 2: Click Command ---")
    if test_click(command_file, response_file, 100, 100):
        print("✅ Click test passed")
    else:
        print("❌ Click test failed")
        return False
    
    print("\n--- Test 3: Type Command ---")
    if test_type(command_file, response_file, "Hello from Python!"):
        print("✅ Type test passed")
    else:
        print("❌ Type test failed")
        return False
    
    print("\n--- Test 4: Key Press ---")
    if test_key(command_file, response_file, "escape"):
        print("✅ Key press test passed")
    else:
        print("❌ Key press test failed")
        return False
    
    print("\n=== All tests passed! ✅ ===")
    return True


def send_command(command_file: Path, command: dict, timeout: float = 5.0) -> dict:
    """Send a command to the server and wait for response"""
    
    # Write command
    with open(command_file, 'w') as f:
        json.dump(command, f, indent=2)
    
    print(f"   Sent: {command}")
    
    # Wait for command file to be processed (file will be read by server)
    # The server updates response.json after processing
    time.sleep(0.5)  # Give server time to process
    
    # Read response
    response_file = command_file.parent / "response.json"
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        try:
            with open(response_file) as f:
                response = json.load(f)
                # Check if this is a response to our command
                if response.get('action') == command.get('action'):
                    print(f"   Response: {response}")
                    return response
        except Exception:
            pass
        time.sleep(0.1)
    
    print("   ⚠️  Timeout waiting for response")
    return {}


def test_screenshot(command_file: Path, response_file: Path, screenshot_file: Path) -> bool:
    """Test screenshot command"""
    
    # Delete old screenshot if exists
    if screenshot_file.exists():
        screenshot_file.unlink()
    
    command = {"action": "screenshot"}
    response = send_command(command_file, command)
    
    if response.get('status') != 'ok':
        return False
    
    # Check if screenshot was created
    time.sleep(1)  # Give time for file to be written
    if not screenshot_file.exists():
        print("   ❌ Screenshot file not created")
        return False
    
    size = screenshot_file.stat().st_size / 1024  # KB
    print(f"   📸 Screenshot saved: {screenshot_file.name} ({size:.1f} KB)")
    
    return True


def test_click(command_file: Path, response_file: Path, x: int, y: int) -> bool:
    """Test mouse click command"""
    
    command = {
        "action": "click",
        "x": x,
        "y": y,
        "button": "left"
    }
    
    response = send_command(command_file, command)
    return response.get('status') == 'ok'


def test_type(command_file: Path, response_file: Path, text: str) -> bool:
    """Test type text command"""
    
    command = {
        "action": "type",
        "text": text
    }
    
    response = send_command(command_file, command)
    return response.get('status') == 'ok'


def test_key(command_file: Path, response_file: Path, key: str) -> bool:
    """Test key press command"""
    
    command = {
        "action": "key",
        "key": key
    }
    
    response = send_command(command_file, command)
    return response.get('status') == 'ok'


if __name__ == "__main__":
    # Default to local dist folder (for testing before deployment)
    default_folder = Path(__file__).parent / "dist" / "RemoteDesktopServer_Win7"
    
    if len(sys.argv) > 1:
        shared_folder = sys.argv[1]
    else:
        shared_folder = str(default_folder)
    
    print("Usage: python test_cs_server.py [shared_folder_path]")
    print(f"Using: {shared_folder}")
    print()
    
    # Check if folder exists
    if not Path(shared_folder).exists():
        print(f"❌ Folder not found: {shared_folder}")
        print("\nMake sure the server is running!")
        sys.exit(1)
    
    # Run tests
    success = test_server(shared_folder)
    
    sys.exit(0 if success else 1)
