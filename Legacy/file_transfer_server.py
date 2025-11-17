"""
Simple file transfer server - receives files over ethernet.
Run this on the computer that needs to receive files.
"""

import socket
import json
import os
import base64
from pathlib import Path

DISCOVERY_PORT = 50123
TRANSFER_PORT = 50126

def start_server(save_dir="."):
    """Start file transfer server."""
    save_path = Path(save_dir).absolute()
    save_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"File Transfer Server")
    print(f"{'='*60}")
    print(f"Save directory: {save_path}")
    print(f"Ready to receive files...")
    print(f"Press Ctrl+C to stop\n")
    
    # Discovery responder
    discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    discovery_sock.bind(('', DISCOVERY_PORT))
    discovery_sock.settimeout(1.0)
    
    # Transfer server
    transfer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transfer_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    transfer_sock.bind(('', TRANSFER_PORT))
    transfer_sock.listen(5)
    transfer_sock.settimeout(1.0)
    
    print(f"[SERVER] Listening on port {TRANSFER_PORT}")
    
    try:
        while True:
            # Handle discovery
            try:
                data, addr = discovery_sock.recvfrom(1024)
                message = json.loads(data.decode())
                if message.get('type') == 'discover_file_transfer':
                    response = json.dumps({
                        'type': 'file_transfer_server',
                        'save_dir': str(save_path)
                    }).encode()
                    discovery_sock.sendto(response, addr)
                    print(f"[DISCOVERY] Responded to {addr[0]}")
            except socket.timeout:
                pass
            
            # Handle file transfers
            try:
                client_sock, addr = transfer_sock.accept()
                client_sock.settimeout(30.0)
                
                # Receive file data
                data = b''
                while True:
                    chunk = client_sock.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                
                # Parse transfer
                transfer = json.loads(data.decode())
                filename = transfer['filename']
                content = base64.b64decode(transfer['content'])
                
                # Save file
                file_path = save_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
                
                print(f"[RECEIVED] {filename} ({len(content)} bytes)")
                
                # Send confirmation
                response = json.dumps({'status': 'ok', 'saved_to': str(file_path)}).encode()
                client_sock.sendall(response)
                client_sock.close()
                
            except socket.timeout:
                pass
                
    except KeyboardInterrupt:
        print("\n[SERVER] Stopping...")
    finally:
        discovery_sock.close()
        transfer_sock.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', default='.', help='Directory to save received files')
    args = parser.parse_args()
    
    start_server(args.dir)
