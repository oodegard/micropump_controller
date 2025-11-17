"""
Simple file transfer client - sends files over ethernet.
Run this on the computer that has the files to send.
"""

import socket
import json
import base64
from pathlib import Path

DISCOVERY_PORT = 50123
TRANSFER_PORT = 50126

def discover_server():
    """Find file transfer server on network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(3.0)
    
    message = json.dumps({'type': 'discover_file_transfer'}).encode()
    
    try:
        sock.sendto(message, ('<broadcast>', DISCOVERY_PORT))
        data, addr = sock.recvfrom(4096)
        response = json.loads(data.decode())
        
        if response.get('type') == 'file_transfer_server':
            sock.close()
            return addr[0]
    except socket.timeout:
        pass
    finally:
        sock.close()
    
    return None

def send_file(server_ip, file_path):
    """Send a file to the server."""
    path = Path(file_path)
    if not path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return False
    
    # Read file
    content = path.read_bytes()
    
    # Create transfer message
    transfer = {
        'filename': path.name,
        'content': base64.b64encode(content).decode()
    }
    
    # Send to server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30.0)
        sock.connect((server_ip, TRANSFER_PORT))
        
        sock.sendall(json.dumps(transfer).encode())
        sock.shutdown(socket.SHUT_WR)
        
        # Get confirmation
        response = sock.recv(4096)
        result = json.loads(response.decode())
        
        sock.close()
        
        if result.get('status') == 'ok':
            print(f"[SENT] {path.name} ({len(content)} bytes)")
            return True
        else:
            print(f"[ERROR] Transfer failed: {result}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Transfer error: {e}")
        return False

def send_files(file_list):
    """Send multiple files to discovered server."""
    print("[CLIENT] Discovering file transfer server...")
    server_ip = discover_server()
    
    if not server_ip:
        print("[ERROR] No file transfer server found")
        print("        Make sure file_transfer_server.py is running on the other PC")
        return
    
    print(f"[CLIENT] Found server at {server_ip}")
    print(f"[CLIENT] Sending {len(file_list)} files...\n")
    
    success = 0
    for file_path in file_list:
        if send_file(server_ip, file_path):
            success += 1
    
    print(f"\n[CLIENT] Complete: {success}/{len(file_list)} files transferred")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+', help='Files to send')
    args = parser.parse_args()
    
    send_files(args.files)
