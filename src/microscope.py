"""
Microscope Remote Desktop Control - File-based communication with C# server.

This module provides microscope control via file-based communication with the
Windows 7 C# remote desktop server. Commands are sent via JSON files in a shared folder.

Usage in YAML config:
    microscope:
        start: true      # Click the Run button to start acquisition
        
Example YAML:
    steps:
      - microscope: start
        duration: 2      # Wait 2 seconds for it to start
      
      - pump_on: high_flow
        duration: 30
      
      - microscope: wait_done  # Wait until acquisition finishes
        duration: 300   # Max wait time
"""

from typing import Optional, Dict, Any
from pathlib import Path
import json
import time


class Microscope:
    """
    File-based remote desktop microscope controller.
    
    Communicates with C# RemoteDesktopServer.exe via shared folder.
    The server monitors command.json and updates response.json.
    
    Configuration:
        - shared_folder: Network path to shared folder (e.g., r"\\\\MICROSCOPE-PC\\RemoteDesktop")
        - run_button_x, run_button_y: Coordinates of Run button
        - running_button_x, running_button_y: Coordinates of button when acquisition is running
    """
    
    # Default button coordinates (update these for your microscope software)
    DEFAULT_RUN_X = 450
    DEFAULT_RUN_Y = 120
    DEFAULT_RUNNING_X = 450
    DEFAULT_RUNNING_Y = 120
    
    def __init__(
        self,
        shared_folder: str = r"\\BIPHUB\RemoteDesktopServer_Win7\status",
        run_button_x: Optional[int] = None,
        run_button_y: Optional[int] = None,
        running_button_x: Optional[int] = None,
        running_button_y: Optional[int] = None
    ):
        """
        Initialize microscope controller.
        
        Args:
            shared_folder: Path to shared folder for command.json/response.json
            run_button_x: X coordinate of Run button (uses default if None)
            run_button_y: Y coordinate of Run button
            running_button_x: X coordinate when acquisition running
            running_button_y: Y coordinate when acquisition running
        """
        self.shared_folder = Path(shared_folder)
        self.command_file = self.shared_folder / "command.json"
        self.response_file = self.shared_folder / "response.json"
        
        self.run_x = run_button_x or self.DEFAULT_RUN_X
        self.run_y = run_button_y or self.DEFAULT_RUN_Y
        self.running_x = running_button_x or self.DEFAULT_RUNNING_X
        self.running_y = running_button_y or self.DEFAULT_RUNNING_Y
        
        self.is_initialized = False
        self.last_error = ""
        
    def initialize(self) -> bool:
        """
        Check if shared folder is accessible.
        
        Returns:
            bool: True if shared folder exists and is writable
        """
        try:
            if not self.shared_folder.exists():
                self.last_error = f"Shared folder not accessible: {self.shared_folder}"
                return False
            
            # Test write access by creating a test command
            test_result = self._send_command("screenshot")
            if not test_result:
                self.last_error = "Failed to communicate with C# server"
                return False
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            self.last_error = f"Initialization failed: {e}"
            return False
    
    def _send_command(self, action: str, **kwargs) -> bool:
        """
        Send command to C# server via command.json file.
        
        Args:
            action: Command action (click, type, key, screenshot, shutdown)
            **kwargs: Additional command parameters (x, y, text, key, etc.)
        
        Returns:
            bool: True if command sent and response received successfully
        """
        try:
            # Clear old response file
            if self.response_file.exists():
                self.response_file.unlink()
            
            # Write command
            command = {"action": action, **kwargs}
            with open(self.command_file, 'w') as f:
                json.dump(command, f)
            
            # Wait for response (C# server monitors file every 100ms)
            timeout = 5.0
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.response_file.exists():
                    with open(self.response_file, 'r') as f:
                        response = json.load(f)
                    
                    # C# server uses "status": "ok" or "status": "error"
                    if response.get("status") == "ok":
                        return True
                    elif response.get("status") == "error":
                        self.last_error = response.get("error", "Unknown error")
                        return False
                
                time.sleep(0.1)
            
            self.last_error = "Timeout waiting for server response"
            return False
            
        except Exception as e:
            self.last_error = f"Command failed: {e}"
            return False
    
    def run(self, image_path: str | dict = "run") -> bool:
        """
        Find and click the Run button using template matching or coordinates.
        
        The button image should be in the buttons/ folder of the shared directory.
        
        Args:
            image_path: Name of button image file (e.g., "Run1_start", "stop", "capture")
                       OR dict with coordinate click: {"action": "click", "x": 100, "y": 200}
        
        Returns:
            bool: True if button found and clicked successfully
        """
        # Handle coordinate-based clicking (dict format)
        if isinstance(image_path, dict):
            if image_path.get("action") == "click":
                return self._send_command("click", x=image_path["x"], y=image_path["y"])
            else:
                print(f"[ERROR] Unknown action in dict: {image_path}")
                return False
        
        # Handle template matching (string format)
        # Remove .png extension if provided (will be added by server)
        image_name = image_path.replace(".png", "")
        return self._send_command("find_and_click", image=image_name)
    
    def wait_done(self, timeout: float = 300.0) -> bool:
        """
        Wait for microscope acquisition to finish.
        
        This monitors the same button coordinates - when acquisition is running,
        the button might show "Stop" or be disabled. When done, it reverts.
        
        TODO: Implement actual detection logic (screenshot comparison or pixel check)
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            bool: True if acquisition finished within timeout
        """
        # Placeholder: For now just wait a bit
        # Real implementation would check screenshot pixels or button state
        time.sleep(2.0)
        return True
    
    def click(self, x: int, y: int, button: str = "left") -> bool:
        """
        Click at specific coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ("left", "right", or "middle")
        
        Returns:
            bool: True if successful
        """
        return self._send_command("click", x=x, y=y, button=button)
    
    def type_text(self, text: str) -> bool:
        """
        Type text on the microscope PC.
        
        Args:
            text: Text to type
        
        Returns:
            bool: True if successful
        """
        return self._send_command("type", text=text)
    
    def press_key(self, key: str) -> bool:
        """
        Press a keyboard key.
        
        Args:
            key: Key name (enter, tab, escape, space, etc.)
        
        Returns:
            bool: True if successful
        """
        return self._send_command("key", key=key)
    
    def take_screenshot(self) -> bool:
        """
        Request a screenshot from the microscope PC.
        
        The screenshot will be saved to screenshot.jpg in the shared folder.
        
        Returns:
            bool: True if successful
        """
        return self._send_command("screenshot")
    
    def close(self) -> bool:
        """
        Close connection (no-op for file-based communication).
        
        Returns:
            bool: Always True
        """
        self.is_initialized = False
        return True
    
    def get_error_details(self) -> str:
        """
        Get detailed error message from last operation.
        
        Returns:
            str: Error details
        """
        return self.last_error
    
    def get_suggested_fix(self) -> str:
        """
        Get suggested fix for last error.
        
        Returns:
            str: Troubleshooting suggestions
        """
        if "not accessible" in self.last_error:
            return (
                "1. Check network share is available: \\\\BIPHUB\\RemoteDesktopServer_Win7\n"
                "2. Verify C# server is running on Windows 7 PC\n"
                "3. Test share access: dir \\\\BIPHUB\\RemoteDesktopServer_Win7\\C_RemoteDesktop"
            )
        elif "Timeout" in self.last_error:
            return (
                "1. Check C# RemoteDesktopServer.exe is running\n"
                "2. Verify it's monitoring C:\\RemoteDesktop folder\n"
                "3. Check server console for errors"
            )
        else:
            return "Check server logs for detailed error information"


# For backward compatibility with YAML configs
class MockMicroscope:
    """Mock microscope for dry-run testing."""
    
    def __init__(self, **kwargs):
        self.is_initialized = False
        self.last_error = ""
    
    def initialize(self) -> bool:
        self.is_initialized = True
        return True
    
    def run(self, image_path: str = "run.png") -> bool:
        print(f"[MOCK] Would click Run button")
        return True
    
    def wait_done(self, timeout: float = 300.0) -> bool:
        print(f"[MOCK] Would wait for acquisition to finish")
        return True
    
    def click(self, x: int, y: int, button: str = "left") -> bool:
        print(f"[MOCK] Would click at ({x}, {y}) with {button} button")
        return True
    
    def type_text(self, text: str) -> bool:
        print(f"[MOCK] Would type: {text}")
        return True
    
    def press_key(self, key: str) -> bool:
        print(f"[MOCK] Would press key: {key}")
        return True
    
    def take_screenshot(self) -> bool:
        print(f"[MOCK] Would take screenshot")
        return True
    
    def close(self) -> bool:
        return True
    
    def get_error_details(self) -> str:
        return ""
    
    def get_suggested_fix(self) -> str:
        return ""
