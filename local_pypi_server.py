"""
Local PyPI package server - serves Python packages over the network.

This allows the air-gapped microscope PC to install packages from this PC
without needing internet access.

Usage on THIS PC (with internet):
    python local_pypi_server.py

Then on microscope PC:
    uv pip install --index-url http://BIPHUB:8080/simple package-name
"""

import http.server
import socketserver
import os
from pathlib import Path
import subprocess
import sys

PORT = 8080
CACHE_DIR = Path.home() / ".cache" / "uv"

class PyPIHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from UV's cache directory."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CACHE_DIR), **kwargs)
    
    def log_message(self, format, *args):
        print(f"[SERVE] {args[0]}")

def ensure_packages_cached():
    """Pre-download packages from pyproject.toml to cache."""
    print("[SETUP] Pre-downloading packages to cache...")
    print(f"[SETUP] Cache location: {CACHE_DIR}")
    
    # Run uv sync to ensure all dependencies are cached
    try:
        result = subprocess.run(
            ["uv", "sync"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[SETUP] ✓ Packages cached successfully")
        else:
            print(f"[SETUP] Warning: {result.stderr}")
    except Exception as e:
        print(f"[SETUP] Could not pre-cache: {e}")

def start_server():
    """Start the local PyPI server."""
    
    print("\n" + "="*60)
    print("Local PyPI Package Server")
    print("="*60)
    
    if not CACHE_DIR.exists():
        print(f"\n[WARNING] UV cache not found at {CACHE_DIR}")
        print("[INFO] Run 'uv sync' first to populate the cache")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    ensure_packages_cached()
    
    # Get local IP
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"\n[SERVER] Starting on port {PORT}")
    print(f"[SERVER] Serving from: {CACHE_DIR}")
    print(f"\n[INFO] On the OTHER PC, use:")
    print(f"       $env:UV_INDEX_URL='http://{hostname}:{PORT}/simple'")
    print(f"       uv sync")
    print(f"\n       OR")
    print(f"       uv pip install --index-url http://{hostname}:{PORT}/simple package-name")
    print(f"\n[INFO] Press Ctrl+C to stop\n")
    
    with socketserver.TCPServer(("", PORT), PyPIHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[SERVER] Stopping...")

if __name__ == "__main__":
    start_server()
