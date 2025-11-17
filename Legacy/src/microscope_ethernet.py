"""
Microscope controller using direct ethernet/network communication.

This module provides zero-configuration ethernet communication between PCs:
- Uses link-local IPv6 addressing (no DHCP/router needed)
- Auto-discovery via UDP broadcast
- Simple TCP communication for commands
- Plug-and-play with direct ethernet cable connection

Commander mode: Send RUN commands (for run_protocol_cli.py)
Listener mode: Receive commands (for microscope_gui_control.py)
"""

import socket
import threading
import time
import json
from typing import Optional, Callable
from dataclasses import dataclass

# Network configuration
DISCOVERY_PORT = 50123  # UDP port for auto-discovery
COMMAND_PORT = 50124    # TCP port for command communication
BROADCAST_INTERVAL = 2  # Seconds between discovery broadcasts
COMMAND_TIMEOUT = 5     # Seconds to wait for command response

COMMANDS = ['RUN', 'RUN_COMMAND_RECEIVED', 'RUN_DONE']


@dataclass
class NetworkConfig:
    """Configuration for network communication."""
    discovery_port: int = DISCOVERY_PORT
    command_port: int = COMMAND_PORT
    timeout: int = COMMAND_TIMEOUT


class Microscope:
    """
    Microscope controller using ethernet for PC-to-PC communication.
    
    Commander mode: Send RUN commands
    Listener mode: Receive commands and respond
    """
    
    def __init__(self, config: NetworkConfig = None):
        """Initialize the microscope controller."""
        self.is_initialized = False
        self.last_error = ""
        self.config = config or NetworkConfig()
        
        # Listener mode state
        self._listener_callback = None
        self._is_listening = False
        self._listen_thread = None
        self._discovery_thread = None
        self._command_server_thread = None
        
        # Commander mode state
        self._peer_address = None
        self._peer_last_seen = 0
        
        try:
            # Get local IP addresses
            self._local_ips = self._get_local_ips()
            if not self._local_ips:
                self.last_error = "No network interfaces found"
                return
            
            self.is_initialized = True
            print(f"[NETWORK] Initialized on interfaces: {', '.join(self._local_ips)}")
        except Exception as e:
            self.last_error = f"Failed to initialize network: {e}"
    
    def _get_local_ips(self) -> list:
        """Get list of local IP addresses (excluding loopback)."""
        ips = []
        try:
            # Get hostname and resolve to IPs
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                ip = info[4][0]
                # Include IPv4 and link-local IPv6, exclude loopback
                if not ip.startswith('127.') and not ip.startswith('::1'):
                    if ip not in ips:
                        ips.append(ip)
        except Exception as e:
            print(f"[NETWORK] Warning: Could not get local IPs: {e}")
        
        # Fallback: try to connect to get local IP
        if not ips:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ips.append(s.getsockname()[0])
                s.close()
            except Exception:
                pass
        
        return ips
    
    # ==================== Commander Mode Methods ====================
    
    def _discover_peer(self) -> Optional[str]:
        """Discover peer on network via UDP broadcast."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)
        
        try:
            # Send discovery broadcast
            message = json.dumps({'type': 'discover', 'role': 'commander'}).encode()
            sock.sendto(message, ('<broadcast>', self.config.discovery_port))
            
            # Wait for response
            try:
                data, addr = sock.recvfrom(1024)
                response = json.loads(data.decode())
                if response.get('type') == 'discover_response':
                    print(f"[NETWORK] Discovered peer at {addr[0]}")
                    return addr[0]
            except socket.timeout:
                pass
        except Exception as e:
            print(f"[NETWORK] Discovery error: {e}")
        finally:
            sock.close()
        
        return None
    
    def send_command(self, command: str) -> bool:
        """Send a command to the peer via TCP."""
        if command not in COMMANDS:
            print(f"Unknown command: {command}")
            return False
        
        # Discover peer if not known or stale
        if not self._peer_address or (time.time() - self._peer_last_seen) > 30:
            print("[NETWORK] Discovering peer...")
            self._peer_address = self._discover_peer()
            if not self._peer_address:
                print("[NETWORK] No peer found on network")
                return False
            self._peer_last_seen = time.time()
        
        # Send command via TCP
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            sock.connect((self._peer_address, self.config.command_port))
            
            message = json.dumps({'command': command}).encode()
            sock.sendall(message)
            
            # Wait for acknowledgment
            data = sock.recv(1024)
            response = json.loads(data.decode())
            
            sock.close()
            
            print(f"Sending command: {command}")
            if response.get('status') == 'ok':
                return True
            else:
                print(f"[NETWORK] Command failed: {response.get('error', 'unknown')}")
                return False
                
        except Exception as e:
            print(f"Error sending command: {e}")
            self._peer_address = None  # Reset peer on error
            return False
    
    def run(self) -> bool:
        """Send RUN command to trigger microscope acquisition."""
        if not self.is_initialized:
            print(f"[MICROSCOPE ERROR] Not initialized: {self.last_error}")
            return False
        
        try:
            print("[MICROSCOPE] Sending RUN command via ethernet...")
            success = self.send_command('RUN')
            if success:
                print("[MICROSCOPE] ✓ RUN command sent successfully")
            else:
                print("[MICROSCOPE] ✗ Failed to send RUN command")
            return success
        except Exception as e:
            print(f"[MICROSCOPE ERROR] Exception during command send: {e}")
            return False
    
    def acquire(self) -> bool:
        """Alias for run() - trigger microscope image acquisition."""
        return self.run()
    
    # ==================== Listener Mode Methods ====================
    
    def _discovery_responder(self):
        """Respond to discovery broadcasts."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.config.discovery_port))
        sock.settimeout(1.0)
        
        print(f"[NETWORK] Discovery responder listening on port {self.config.discovery_port}")
        
        while self._is_listening:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message.get('type') == 'discover' and message.get('role') == 'commander':
                    # Respond to discovery
                    response = json.dumps({'type': 'discover_response', 'role': 'listener'}).encode()
                    sock.sendto(response, addr)
                    print(f"[NETWORK] Responded to discovery from {addr[0]}")
            except socket.timeout:
                continue
            except Exception as e:
                if self._is_listening:
                    print(f"[NETWORK] Discovery error: {e}")
        
        sock.close()
    
    def _command_server(self):
        """TCP server to receive commands."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.config.command_port))
        sock.listen(5)
        sock.settimeout(1.0)
        
        print(f"[NETWORK] Command server listening on port {self.config.command_port}")
        
        while self._is_listening:
            try:
                client_sock, addr = sock.accept()
                client_sock.settimeout(5.0)
                
                data = client_sock.recv(1024)
                message = json.loads(data.decode())
                
                command = message.get('command')
                if command and self._listener_callback:
                    print(f"[NETWORK] Received command from {addr[0]}: {command}")
                    
                    # Send acknowledgment
                    response = json.dumps({'status': 'ok'}).encode()
                    client_sock.sendall(response)
                    
                    # Execute callback
                    self._listener_callback(command)
                else:
                    response = json.dumps({'status': 'error', 'error': 'invalid command'}).encode()
                    client_sock.sendall(response)
                
                client_sock.close()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self._is_listening:
                    print(f"[NETWORK] Command server error: {e}")
        
        sock.close()
    
    def start_listening(self, callback: Callable[[str], None]):
        """
        Start listening for commands.
        
        Args:
            callback: Function to call when a command is received
        """
        if self._is_listening:
            print("Already listening")
            return
        
        self._listener_callback = callback
        self._is_listening = True
        
        # Start discovery responder
        self._discovery_thread = threading.Thread(target=self._discovery_responder, daemon=True)
        self._discovery_thread.start()
        
        # Start command server
        self._command_server_thread = threading.Thread(target=self._command_server, daemon=True)
        self._command_server_thread.start()
        
        print("Listening for commands via ethernet... Press Ctrl+C to stop")
    
    def stop_listening(self):
        """Stop listening for commands."""
        self._is_listening = False
        
        if self._discovery_thread:
            self._discovery_thread.join(timeout=2.0)
        if self._command_server_thread:
            self._command_server_thread.join(timeout=2.0)
    
    # ==================== Utility Methods ====================
    
    def close(self):
        """Clean up resources."""
        self.stop_listening()
    
    def get_error_details(self) -> str:
        """Return detailed error message if initialization failed."""
        return self.last_error
    
    def get_suggested_fix(self) -> str:
        """Return suggested troubleshooting steps."""
        if not self.is_initialized:
            return (
                "Check ethernet cable connection between PCs. "
                "Ensure Windows Firewall allows connections on ports 50123-50124. "
                "Verify network adapter is enabled in Windows Network Settings."
            )
        return ""
