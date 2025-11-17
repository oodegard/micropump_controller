"""
Build standalone executable for Windows 7 compatibility.

This creates a single .exe file that includes all dependencies
and will run on Windows 7 SP1 without Python installed.
"""

import subprocess
import sys
from pathlib import Path

def build_server_exe():
    """Build remote_desktop_server.exe for Windows 7."""
    
    print("\n" + "="*60)
    print("Building Remote Desktop Server for Windows 7")
    print("="*60)
    
    # PyInstaller command for Windows 7 compatible build
    cmd = [
        "pyinstaller",
        "--onefile",                    # Single executable
        "--windowed",                   # No console window (optional)
        "--name", "remote_desktop_server",
        "--add-data", "src;src",        # Include src directory
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "pyautogui",
        "--hidden-import", "PIL",
        "--collect-all", "pyautogui",
        "remote_desktop_server.py"
    ]
    
    print("\n[BUILD] Creating executable...")
    print(f"[BUILD] Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = Path("dist/remote_desktop_server.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "="*60)
            print("✓ Build Successful!")
            print("="*60)
            print(f"\nExecutable: {exe_path.absolute()}")
            print(f"Size: {size_mb:.1f} MB")
            print(f"\nTo use on Windows 7 microscope PC:")
            print(f"  1. Copy 'dist/remote_desktop_server.exe' to the microscope PC")
            print(f"  2. Double-click to run (no Python needed!)")
            print(f"  3. On this PC: uv run python remote_desktop_client.py")
            print("\n" + "="*60)
        else:
            print("\n[ERROR] Build completed but exe not found")
    else:
        print("\n[ERROR] Build failed")
        print("\nMake sure pyinstaller is installed:")
        print("  uv pip install pyinstaller")

if __name__ == "__main__":
    build_server_exe()
