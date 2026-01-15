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
        - shared_folder: Network path to shared folder (e.g., r"\\MICROSCOPE-PC\RemoteDesktop")
        - run_button_x, run_button_y: Coordinates of Run button
        - running_button_x, running_button_y: Coordinates of button when acquisition is running
    """
    
    # Default button coordinates (update these for your microscope software)
    DEFAULT_RUN_X = 450
    DEFAULT_RUN_Y = 120
    DEFAULT_RUNNING_X = 450
    DEFAULT_RUNNING_Y = 120


class Microscope:
    """
    Remote desktop-based microscope controller.
    
    This is the default microscope control interface for the micropump controller.
    It provides transparent remote control over ethernet - no audio needed.
    
    Example usage:
        # In commander mode (run from controller PC)
        microscope = Microscope()
        if microscope.initialize():
            microscope.run()  # Trigger remote action
        
        # Server runs on microscope PC:
        # python remote_desktop_server.py
    """
    
    def __init__(self, config: Optional[RemoteDesktopConfig] = None):
        """
        Initialize microscope controller.
        
        Args:
            config: Remote desktop configuration. If None, uses auto-detection.
        """
        self.config = config or RemoteDesktopConfig.auto_detect()
        self.server_ip: Optional[str] = None
        self.is_initialized = False
    
    def _discover_server(self) -> Optional[str]:
        """
        Discover remote desktop server via UDP broadcast.
        
        Returns:
            Server IP address if found, None otherwise.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(self.config.discovery_timeout)
        
        message = json.dumps({'type': 'discover'}).encode()
        
        try:
            # Send broadcast discovery
            sock.sendto(message, ('<broadcast>', DISCOVERY_PORT))
            
            # Wait for response
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode())
            
            if response.get('role') == 'remote_desktop_server':
                print(f"[MICROSCOPE] Found server at {addr[0]}")
                return addr[0]
        except socket.timeout:
            print("[MICROSCOPE] No server found (timeout)")
        except Exception as e:
            print(f"[MICROSCOPE] Discovery error: {e}")
        finally:
            sock.close()
        
        return None
    
    def _send_command(self, command: str, **kwargs) -> dict:
        """
        Send a command to the remote server.
        
        Args:
            command: Command name (e.g., 'click', 'type', 'find_and_click')
            **kwargs: Command-specific parameters
            
        Returns:
            Response dictionary with 'status' field
        """
        if not self.server_ip:
            # Try to discover server
            self.server_ip = self._discover_server()
            if not self.server_ip:
                return {'status': 'error', 'error': 'Server not found'}
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.command_timeout)
            sock.connect((self.server_ip, COMMAND_PORT))
            
            message = {'command': command, **kwargs}
            sock.sendall(json.dumps(message).encode())
            
            response_data = sock.recv(4096)
            response = json.loads(response_data.decode())
            
            sock.close()
            return response
        except Exception as e:
            print(f"[MICROSCOPE] Command error: {e}")
            # Reset server IP on connection failure
            self.server_ip = None
            return {'status': 'error', 'error': str(e)}
    
    def initialize(self) -> bool:
        """
        Initialize connection to remote desktop server.
        
        Returns:
            True if server found and ready, False otherwise.
        """
        print("[MICROSCOPE] Initializing remote desktop connection...")
        
        self.server_ip = self._discover_server()
        
        if self.server_ip:
            self.is_initialized = True
            print(f"[MICROSCOPE] Connected to server at {self.server_ip}")
            return True
        else:
            print("[MICROSCOPE] Failed to find server")
            print("             Make sure remote_desktop_server.py is running on microscope PC")
            return False
    
    def run(self, image_path: str = "run.png") -> bool:
        """
        Trigger microscope run by finding and clicking the run button.
        
        This is the primary command used in protocol sequences.
        It uses image recognition to find and click the run button.
        
        Args:
            image_path: Path to the run button image (default: "run.png")
            
        Returns:
            True if successful, False otherwise.
        """
        print(f"[MICROSCOPE] Running microscope (finding '{image_path}')...")
        
        result = self._send_command('find_and_click', image=image_path, confidence=0.8)
        
        if result.get('status') == 'ok':
            if result.get('found'):
                print("[MICROSCOPE] ✓ Found and clicked run button")
                return True
            else:
                print(f"[MICROSCOPE] ✗ Run button not found (image: {image_path})")
                return False
        else:
            print(f"[MICROSCOPE] ✗ Command failed: {result.get('error', 'Unknown error')}")
            return False
    
    def acquire(self) -> bool:
        """
        Trigger microscope image acquisition.
        
        This is a placeholder for future acquisition workflows.
        Currently just logs the action.
        
        Returns:
            True (always succeeds for now)
        """
        print("[MICROSCOPE] Acquisition triggered (placeholder)")
        return True
    
    def click(self, x: int, y: int, button: str = 'left') -> bool:
        """
        Click at specific coordinates on remote screen.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left' or 'right')
            
        Returns:
            True if successful, False otherwise.
        """
        result = self._send_command('click', x=x, y=y, button=button)
        return result.get('status') == 'ok'
    
    def type_text(self, text: str) -> bool:
        """
        Type text on remote screen.
        
        Args:
            text: Text to type
            
        Returns:
            True if successful, False otherwise.
        """
        result = self._send_command('type', text=text)
        return result.get('status') == 'ok'
    
    def press_key(self, key: str) -> bool:
        """
        Press a key on remote screen.
        
        Args:
            key: Key name (e.g., 'enter', 'tab', 'esc')
            
        Returns:
            True if successful, False otherwise.
        """
        result = self._send_command('key', key=key)
        return result.get('status') == 'ok'
    
    def close(self):
        """Close the connection (cleanup)."""
        self.is_initialized = False
        print("[MICROSCOPE] Connection closed")
