"""
Minimal remote desktop server for Windows 7.
This version has minimal dependencies and uses only standard library where possible.
"""

import socket
import threading
import time
import json
import base64
import io
import sys

# Check for required modules
try:
    from PIL import ImageGrab
    import pyautogui
except ImportError:
    print("ERROR: Missing dependencies!")
    print("\nPlease install:")
    print("  pip install pillow pyautogui")
    sys.exit(1)

# Network configuration
DISCOVERY_PORT = 50123
COMMAND_PORT = 50124
SCREENSHOT_PORT = 50125

# Screenshot settings  
SCREENSHOT_QUALITY = 60  # Lower quality for faster transfer on old systems
SCREENSHOT_SCALE = 0.75  # Reduce resolution for better performance
MAX_FPS = 5              # Lower FPS for Windows 7

print(f"""
{'='*60}
Remote Desktop Server for Windows 7
{'='*60}
Minimal version with reduced dependencies
Starting services...
""")

# Get screen size
screen_width, screen_height = pyautogui.size()
print(f"Screen size: {screen_width}x{screen_height}")

# Safety
pyautogui.FAILSAFE = False
is_running = True

def discovery_responder():
    """Respond to discovery broadcasts."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', DISCOVERY_PORT))
    sock.settimeout(1.0)
    
    print(f"[OK] Discovery service on port {DISCOVERY_PORT}")
    
    while is_running:
        try:
            data, addr = sock.recvfrom(1024)
            message = json.loads(data.decode())
            
            if message.get('type') == 'discover':
                response = json.dumps({
                    'type': 'discover_response',
                    'role': 'remote_desktop_server',
                    'screen_width': screen_width,
                    'screen_height': screen_height
                }).encode()
                sock.sendto(response, addr)
                print(f"[DISCOVERY] {addr[0]}")
        except socket.timeout:
            continue
        except Exception as e:
            if is_running:
                print(f"[ERROR] Discovery: {e}")
    
    sock.close()

def capture_screenshot():
    """Capture screenshot."""
    try:
        screenshot = ImageGrab.grab()
        
        if SCREENSHOT_SCALE != 1.0:
            new_width = int(screen_width * SCREENSHOT_SCALE)
            new_height = int(screen_height * SCREENSHOT_SCALE)
            screenshot = screenshot.resize((new_width, new_height))
        
        buffer = io.BytesIO()
        screenshot.save(buffer, format='JPEG', quality=SCREENSHOT_QUALITY, optimize=True)
        return buffer.getvalue()
    except Exception as e:
        print(f"[ERROR] Screenshot: {e}")
        return b''

def screenshot_server():
    """TCP server to stream screenshots."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', SCREENSHOT_PORT))
    sock.listen(5)
    sock.settimeout(1.0)
    
    print(f"[OK] Screenshot service on port {SCREENSHOT_PORT}")
    
    last_screenshot_time = 0
    
    while is_running:
        try:
            client_sock, addr = sock.accept()
            client_sock.settimeout(5.0)
            
            data = client_sock.recv(1024)
            request = json.loads(data.decode())
            
            if request.get('command') == 'get_screenshot':
                # Rate limiting
                min_interval = 1.0 / MAX_FPS
                elapsed = time.time() - last_screenshot_time
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                
                screenshot_data = capture_screenshot()
                last_screenshot_time = time.time()
                
                response = {
                    'status': 'ok',
                    'width': screen_width,
                    'height': screen_height,
                    'data': base64.b64encode(screenshot_data).decode()
                }
                
                response_json = json.dumps(response).encode()
                client_sock.sendall(len(response_json).to_bytes(4, 'big'))
                client_sock.sendall(response_json)
            
            client_sock.close()
            
        except socket.timeout:
            continue
        except Exception as e:
            if is_running:
                print(f"[ERROR] Screenshot server: {e}")
    
    sock.close()

def command_server():
    """TCP server to receive control commands."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', COMMAND_PORT))
    sock.listen(5)
    sock.settimeout(1.0)
    
    print(f"[OK] Command service on port {COMMAND_PORT}")
    
    while is_running:
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
                pyautogui.click(x, y, button=button)
                print(f"[CLICK] ({x}, {y}) {button}")
            
            elif command == 'move':
                x = int(message.get('x', 0))
                y = int(message.get('y', 0))
                pyautogui.moveTo(x, y)
                print(f"[MOVE] ({x}, {y})")
            
            elif command == 'type':
                text = message.get('text', '')
                pyautogui.write(text)
                print(f"[TYPE] {text}")
            
            elif command == 'key':
                key = message.get('key', '')
                pyautogui.press(key)
                print(f"[KEY] {key}")
            
            elif command == 'find_and_click':
                image_path = message.get('image', '')
                confidence = message.get('confidence', 0.8)
                
                try:
                    location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                    if location:
                        center = pyautogui.center(location)
                        pyautogui.click(center)
                        print(f"[FOUND] {image_path} at {center}")
                        response['found'] = True
                    else:
                        print(f"[NOT FOUND] {image_path}")
                        response['found'] = False
                except Exception as e:
                    print(f"[ERROR] Find: {e}")
                    response['status'] = 'error'
                    response['error'] = str(e)
            
            else:
                response['status'] = 'error'
                response['error'] = 'Unknown command'
            
            client_sock.sendall(json.dumps(response).encode())
            client_sock.close()
            
        except socket.timeout:
            continue
        except Exception as e:
            if is_running:
                print(f"[ERROR] Command server: {e}")
    
    sock.close()

# Start all services
print("\nStarting threads...")
threading.Thread(target=discovery_responder, daemon=True).start()
threading.Thread(target=command_server, daemon=True).start()
threading.Thread(target=screenshot_server, daemon=True).start()

print(f"""
{'='*60}
READY - Waiting for connections
{'='*60}
Press Ctrl+C to stop

""")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nStopping...")
    is_running = False
    time.sleep(2)
    print("Stopped.")
