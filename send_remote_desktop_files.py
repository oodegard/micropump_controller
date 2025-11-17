"""
Send remote desktop files to the other computer.
This transfers all necessary files to run the remote desktop server.
"""

import subprocess
import sys

# Files needed on the microscope/target PC
REQUIRED_FILES = [
    'remote_desktop_server.py',
    'pyproject.toml',
    'file_transfer_server.py',  # In case they need to send files back
]

def main():
    print("\n" + "="*60)
    print("Remote Desktop File Transfer")
    print("="*60)
    print("\nThis will send the following files to the other PC:")
    for f in REQUIRED_FILES:
        print(f"  - {f}")
    
    print("\n[STEP 1] Make sure file_transfer_server.py is running on the OTHER PC:")
    print("         python file_transfer_server.py")
    
    input("\nPress Enter when the server is running on the other PC...")
    
    print("\n[STEP 2] Transferring files...")
    
    cmd = [sys.executable, 'file_transfer_client.py'] + REQUIRED_FILES
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "="*60)
        print("✓ Transfer Complete!")
        print("="*60)
        print("\nNext steps on the OTHER PC:")
        print("  1. uv sync                              # Install dependencies")
        print("  2. uv run python remote_desktop_server.py   # Start server")
        print("\nThen on THIS PC:")
        print("  uv run python remote_desktop_client.py      # Connect and control")
        print("\n" + "="*60)
    else:
        print("\n[ERROR] Transfer failed. Make sure the server is running.")

if __name__ == "__main__":
    main()
