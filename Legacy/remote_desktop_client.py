"""
Remote Desktop Client - Runs on the controller PC.

Provides a live view of the remote screen and allows clicking on it.
All interaction happens through a simple tkinter window showing the remote screen.

Usage:
    python remote_desktop_client.py
"""

import socket
import threading
import time
import json
import base64
import io
from typing import Optional
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


# Network configuration
DISCOVERY_PORT = 50123
COMMAND_PORT = 50124
SCREENSHOT_PORT = 50125

# Client settings
AUTO_REFRESH_FPS = 5  # Automatic screenshot refresh rate


class RemoteDesktopClient:
    """Client that displays and controls a remote desktop."""
    
    def __init__(self):
        """Initialize the remote desktop client."""
        self.server_ip = None
        self.remote_width = 0
        self.remote_height = 0
        self.is_running = False
        self._refresh_thread = None
        
        # Create GUI
        self.root = tk.Tk()
        self.root.title("Remote Desktop - Connecting...")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        
        # Status bar
        self.status_var = tk.StringVar(value="Discovering server...")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Control panel
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="FPS:").pack(side=tk.LEFT, padx=5)
        self.fps_var = tk.IntVar(value=AUTO_REFRESH_FPS)
        fps_spin = ttk.Spinbox(control_frame, from_=1, to=30, textvariable=self.fps_var, width=5)
        fps_spin.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = ttk.Button(control_frame, text="Refresh Now", command=self._manual_refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_var = tk.BooleanVar(value=True)
        auto_check = ttk.Checkbutton(control_frame, text="Auto-refresh", variable=self.auto_var)
        auto_check.pack(side=tk.LEFT, padx=5)
        
        # Canvas for displaying remote screen
        self.canvas = tk.Canvas(self.root, bg='black', cursor='cross')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Button-3>', self._on_right_click)
        
        self.current_image = None
        self.photo_image = None
    
    def _discover_server(self) -> Optional[str]:
        """Discover remote desktop server on network."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2.0)
        
        message = json.dumps({'type': 'discover'}).encode()
        
        for _ in range(3):
            try:
                sock.sendto(message, ('<broadcast>', DISCOVERY_PORT))
                
                data, addr = sock.recvfrom(4096)
                response = json.loads(data.decode())
                
                if response.get('role') == 'remote_desktop_server':
                    self.remote_width = response.get('screen_width', 1920)
                    self.remote_height = response.get('screen_height', 1080)
                    sock.close()
                    return addr[0]
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CLIENT] Discovery error: {e}")
        
        sock.close()
        return None
    
    def _send_command(self, command: str, **kwargs) -> dict:
        """Send a command to the remote server."""
        if not self.server_ip:
            return {'status': 'error', 'error': 'Not connected'}
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.server_ip, COMMAND_PORT))
            
            message = {'command': command, **kwargs}
            sock.sendall(json.dumps(message).encode())
            
            response_data = sock.recv(4096)
            response = json.loads(response_data.decode())
            
            sock.close()
            return response
        except Exception as e:
            print(f"[CLIENT] Command error: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_screenshot(self) -> Optional[Image.Image]:
        """Get a screenshot from the remote server."""
        if not self.server_ip:
            return None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((self.server_ip, SCREENSHOT_PORT))
            
            # Request screenshot
            request = json.dumps({'command': 'get_screenshot'}).encode()
            sock.sendall(request)
            
            # Read response length
            length_bytes = sock.recv(4)
            if len(length_bytes) != 4:
                sock.close()
                return None
            
            response_length = int.from_bytes(length_bytes, 'big')
            
            # Read response data
            response_data = b''
            while len(response_data) < response_length:
                chunk = sock.recv(min(8192, response_length - len(response_data)))
                if not chunk:
                    break
                response_data += chunk
            
            sock.close()
            
            # Parse response
            response = json.loads(response_data.decode())
            
            if response.get('status') == 'ok':
                image_data = base64.b64decode(response['data'])
                image = Image.open(io.BytesIO(image_data))
                return image
            
        except Exception as e:
            print(f"[CLIENT] Screenshot error: {e}")
        
        return None
    
    def _update_screenshot(self, image: Image.Image):
        """Update the displayed screenshot."""
        if not image:
            return
        
        # Calculate scaling to fit window
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 800
            canvas_height = 600
        
        # Calculate aspect-preserving scale
        scale_x = canvas_width / image.width
        scale_y = canvas_height / image.height
        scale = min(scale_x, scale_y, 1.0)  # Don't upscale
        
        new_width = int(image.width * scale)
        new_height = int(image.height * scale)
        
        # Resize image
        resized = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Store for coordinate translation
        self.current_image = image
        self.display_scale = scale
        
        # Update canvas
        self.photo_image = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, image=self.photo_image)
    
    def _canvas_to_remote_coords(self, canvas_x: int, canvas_y: int) -> tuple:
        """Convert canvas coordinates to remote screen coordinates."""
        if not self.current_image:
            return (canvas_x, canvas_y)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Center of canvas
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Offset from center
        offset_x = canvas_x - center_x
        offset_y = canvas_y - center_y
        
        # Convert to remote coordinates
        remote_x = int((self.current_image.width / 2) + (offset_x / self.display_scale))
        remote_y = int((self.current_image.height / 2) + (offset_y / self.display_scale))
        
        # Clamp to screen bounds
        remote_x = max(0, min(remote_x, self.remote_width - 1))
        remote_y = max(0, min(remote_y, self.remote_height - 1))
        
        return (remote_x, remote_y)
    
    def _on_click(self, event):
        """Handle left click on canvas."""
        remote_x, remote_y = self._canvas_to_remote_coords(event.x, event.y)
        print(f"[CLIENT] Left click at ({remote_x}, {remote_y})")
        
        result = self._send_command('click', x=remote_x, y=remote_y, button='left')
        
        if result.get('status') == 'ok':
            self.status_var.set(f"Clicked at ({remote_x}, {remote_y})")
            # Refresh after click
            self.root.after(200, self._manual_refresh)
    
    def _on_right_click(self, event):
        """Handle right click on canvas."""
        remote_x, remote_y = self._canvas_to_remote_coords(event.x, event.y)
        print(f"[CLIENT] Right click at ({remote_x}, {remote_y})")
        
        result = self._send_command('click', x=remote_x, y=remote_y, button='right')
        
        if result.get('status') == 'ok':
            self.status_var.set(f"Right-clicked at ({remote_x}, {remote_y})")
            # Refresh after click
            self.root.after(200, self._manual_refresh)
    
    def _manual_refresh(self):
        """Manually refresh the screenshot."""
        self.status_var.set("Refreshing...")
        self.root.update()
        
        image = self._get_screenshot()
        if image:
            self._update_screenshot(image)
            self.status_var.set(f"Connected to {self.server_ip} ({self.remote_width}x{self.remote_height})")
        else:
            self.status_var.set("Failed to get screenshot")
    
    def _auto_refresh_loop(self):
        """Automatic screenshot refresh loop."""
        while self.is_running:
            if self.auto_var.get():
                try:
                    image = self._get_screenshot()
                    if image:
                        self.root.after(0, self._update_screenshot, image)
                        self.root.after(0, self.status_var.set, 
                                       f"Connected to {self.server_ip} ({self.remote_width}x{self.remote_height})")
                except Exception as e:
                    print(f"[CLIENT] Refresh error: {e}")
            
            # Sleep based on FPS setting
            time.sleep(1.0 / max(1, self.fps_var.get()))
    
    def connect(self) -> bool:
        """Connect to remote desktop server."""
        self.status_var.set("Discovering server...")
        self.root.update()
        
        self.server_ip = self._discover_server()
        
        if not self.server_ip:
            self.status_var.set("Server not found - check connection")
            return False
        
        self.root.title(f"Remote Desktop - {self.server_ip}")
        self.status_var.set(f"Connected to {self.server_ip}")
        
        # Get initial screenshot
        self._manual_refresh()
        
        # Start auto-refresh thread
        self.is_running = True
        self._refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self._refresh_thread.start()
        
        return True
    
    def close(self):
        """Close the client."""
        self.is_running = False
        if self._refresh_thread:
            self._refresh_thread.join(timeout=2.0)
        self.root.destroy()
    
    def run(self):
        """Run the client application."""
        if self.connect():
            self.root.mainloop()
        else:
            # Show error dialog
            error_window = tk.Toplevel()
            error_window.title("Connection Error")
            ttk.Label(error_window, text="Could not find remote desktop server.\n\n"
                                         "Make sure:\n"
                                         "1. remote_desktop_server.py is running on the microscope PC\n"
                                         "2. Both PCs are connected via ethernet cable\n"
                                         "3. Windows Firewall allows ports 50123-50125",
                     padding=20).pack()
            ttk.Button(error_window, text="Retry", command=lambda: [error_window.destroy(), self.run()]).pack(pady=10)
            ttk.Button(error_window, text="Exit", command=error_window.destroy).pack(pady=10)
            error_window.mainloop()


if __name__ == "__main__":
    client = RemoteDesktopClient()
    client.run()
