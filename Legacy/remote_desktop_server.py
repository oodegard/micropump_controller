"""
Remote Desktop Server - Runs on the microscope PC.

Provides screen capture and remote control via direct ethernet connection:
- Captures and streams screenshots
- Receives and executes mouse clicks
- Receives and executes keyboard input
- No external software needed - pure Python over ethernet

Usage:
    python remote_desktop_server.py
"""

import socket
import threading
import time
import json
import base64
import io
from typing import Optional, Callable
import pyautogui
from PIL import ImageGrab
import numpy as np

# Network configuration
DISCOVERY_PORT = 50123
COMMAND_PORT = 50124
SCREENSHOT_PORT = 50125

# Screenshot settings
SCREENSHOT_QUALITY = 75  # JPEG quality (1-100)
SCREENSHOT_SCALE = 1.0   # Scale factor (0.5 = half size for faster transfer)
MAX_FPS = 10             # Maximum frames per second


class RemoteDesktopServer:
    """Server that provides remote desktop access over ethernet."""
    
    def __init__(self):
        """Initialize the remote desktop server."""
        self.is_running = False
        self._discovery_thread = None
        self._command_thread = None
        self._screenshot_thread = None
        self._clients = set()
        self._last_screenshot_time = 0
        
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        print(f"[SERVER] Screen size: {self.screen_width}x{self.screen_height}")
        
        # Safety: prevent PyAutoGUI from failing on edge coordinates
        pyautogui.FAILSAFE = False
    
    def _get_local_ips(self) -> list:
        """Get list of local IP addresses."""
        ips = []
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                ip = info[4][0]
                if not ip.startswith('127.') and not ip.startswith('::1'):
                    if ip not in ips:
                        ips.append(ip)
        except Exception:
            pass
        
        if not ips:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ips.append(s.getsockname()[0])
                s.close()
            except Exception:
                ips.append("localhost")
        
        return ips
    
    def _discovery_responder(self):
        """Respond to discovery broadcasts."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', DISCOVERY_PORT))
        sock.settimeout(1.0)
        
        print(f"[SERVER] Discovery service started on port {DISCOVERY_PORT}")
        
        while self.is_running:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message.get('type') == 'discover':
                    response = json.dumps({
                        'type': 'discover_response',
                        'role': 'remote_desktop_server',
                        'screen_width': self.screen_width,
                        'screen_height': self.screen_height
                    }).encode()
                    sock.sendto(response, addr)
                    print(f"[SERVER] Responded to discovery from {addr[0]}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"[SERVER] Discovery error: {e}")
        
        sock.close()
    
    def _capture_screenshot(self) -> bytes:
        """Capture screenshot and return as JPEG bytes."""
        try:
            # Capture screen
            screenshot = ImageGrab.grab()
            
            # Resize if scaling is enabled
            if SCREENSHOT_SCALE != 1.0:
                new_width = int(self.screen_width * SCREENSHOT_SCALE)
                new_height = int(self.screen_height * SCREENSHOT_SCALE)
                screenshot = screenshot.resize((new_width, new_height))
            
            # Convert to JPEG bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG', quality=SCREENSHOT_QUALITY, optimize=True)
            return buffer.getvalue()
        except Exception as e:
            print(f"[SERVER] Screenshot error: {e}")
            return b''
    
    def _screenshot_server(self):
        """TCP server to stream screenshots."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', SCREENSHOT_PORT))
        sock.listen(5)
        sock.settimeout(1.0)
        
        print(f"[SERVER] Screenshot service started on port {SCREENSHOT_PORT}")
        
        while self.is_running:
            try:
                client_sock, addr = sock.accept()
                client_sock.settimeout(5.0)
                
                # Read request
                data = client_sock.recv(1024)
                request = json.loads(data.decode())
                
                if request.get('command') == 'get_screenshot':
                    # Rate limiting
                    min_interval = 1.0 / MAX_FPS
                    elapsed = time.time() - self._last_screenshot_time
                    if elapsed < min_interval:
                        time.sleep(min_interval - elapsed)
                    
                    # Capture and send screenshot
                    screenshot_data = self._capture_screenshot()
                    self._last_screenshot_time = time.time()
                    
                    response = {
                        'status': 'ok',
                        'width': self.screen_width,
                        'height': self.screen_height,
                        'data': base64.b64encode(screenshot_data).decode()
                    }
                    
                    response_json = json.dumps(response).encode()
                    client_sock.sendall(len(response_json).to_bytes(4, 'big'))
                    client_sock.sendall(response_json)
                
                client_sock.close()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"[SERVER] Screenshot server error: {e}")
        
        sock.close()
    
    def _command_server(self):
        """TCP server to receive control commands."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', COMMAND_PORT))
        sock.listen(5)
        sock.settimeout(1.0)
        
        print(f"[SERVER] Command service started on port {COMMAND_PORT}")
        
        while self.is_running:
            try:
                client_sock, addr = sock.accept()
                client_sock.settimeout(5.0)
                
                data = client_sock.recv(4096)
                message = json.loads(data.decode())
                
                command = message.get('command')
                response = {'status': 'ok'}
                
                if command == 'click':
                    x = int(message.get('x', 0))
                    y = int(message.get('y', 0))
                    button = message.get('button', 'left')
                    
                    # Execute click
                    pyautogui.click(x, y, button=button)
                    print(f"[SERVER] Click at ({x}, {y}) with {button} button")
                
                elif command == 'move':
                    x = int(message.get('x', 0))
                    y = int(message.get('y', 0))
                    
                    pyautogui.moveTo(x, y)
                    print(f"[SERVER] Move to ({x}, {y})")
                
                elif command == 'type':
                    text = message.get('text', '')
                    
                    pyautogui.write(text)
                    print(f"[SERVER] Type: {text}")
                
                elif command == 'key':
                    key = message.get('key', '')
                    
                    pyautogui.press(key)
                    print(f"[SERVER] Press key: {key}")
                
                elif command == 'find_and_click':
                    image_path = message.get('image', '')
                    confidence = message.get('confidence', 0.8)
                    
                    try:
                        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                        if location:
                            center = pyautogui.center(location)
                            pyautogui.click(center)
                            print(f"[SERVER] Found and clicked image at {center}")
                            response['found'] = True
                        else:
                            print(f"[SERVER] Image not found: {image_path}")
                            response['found'] = False
                    except Exception as e:
                        print(f"[SERVER] Find and click error: {e}")
                        response['status'] = 'error'
                        response['error'] = str(e)
                
                else:
                    response['status'] = 'error'
                    response['error'] = 'Unknown command'
                
                # Send response
                client_sock.sendall(json.dumps(response).encode())
                client_sock.close()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"[SERVER] Command server error: {e}")
        
        sock.close()
    
    def start(self):
        """Start the remote desktop server."""
        if self.is_running:
            print("[SERVER] Already running")
            return
        
        self.is_running = True
        
        print("\n" + "="*60)
        print("Remote Desktop Server")
        print("="*60)
        print(f"Server IPs: {', '.join(self._get_local_ips())}")
        print(f"Screen: {self.screen_width}x{self.screen_height}")
        print(f"Ready for connections...")
        print("Press Ctrl+C to stop\n")
        
        # Start discovery responder
        self._discovery_thread = threading.Thread(target=self._discovery_responder, daemon=True)
        self._discovery_thread.start()
        
        # Start command server
        self._command_thread = threading.Thread(target=self._command_server, daemon=True)
        self._command_thread.start()
        
        # Start screenshot server
        self._screenshot_thread = threading.Thread(target=self._screenshot_server, daemon=True)
        self._screenshot_thread.start()
        
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[SERVER] Stopping...")
            self.stop()
    
    def stop(self):
        """Stop the remote desktop server."""
        self.is_running = False
        
        if self._discovery_thread:
            self._discovery_thread.join(timeout=2.0)
        if self._command_thread:
            self._command_thread.join(timeout=2.0)
        if self._screenshot_thread:
            self._screenshot_thread.join(timeout=2.0)
        
        print("[SERVER] Stopped")


if __name__ == "__main__":
    server = RemoteDesktopServer()
    server.start()
