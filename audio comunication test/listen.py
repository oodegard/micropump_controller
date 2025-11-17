"""
Listener mode - Run this on the PC that will receive commands.

This script continuously listens for audio commands and responds appropriately:
- When RUN is received, it sends RUN_COMMAND_RECEIVED, performs a task, then sends RUN_DONE
- Logs all received commands with timestamps
"""

import sys
import os
import time

# Add src folder to path
_SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from microscope import Microscope

def perform_task():
    """
    Placeholder for the actual task to be performed.
    Replace this with your real task logic.
    """
    print("  [TASK] Starting task execution...")
    time.sleep(2)  # Simulate task taking 2 seconds
    print("  [TASK] Task completed!")

def create_command_handler(microscope: Microscope):
    """Create command handler with microscope instance for sending responses."""
    def command_handler(command: str):
        """Handle received commands and execute appropriate responses."""
        print(f">>> RECEIVED: {command}")
        
        if command == 'RUN':
            # Acknowledge receipt
            time.sleep(0.3)
            print("  -> Sending acknowledgment...")
            microscope.send_command('RUN_COMMAND_RECEIVED')
            
            # Perform the actual task
            perform_task()
            
            # Signal completion
            time.sleep(0.3)
            print("  -> Sending completion signal...")
            microscope.send_command('RUN_DONE')
            print("  ✓ Workflow complete\n")
    
    return command_handler

def main():
    print("Audio Communication - LISTEN MODE")
    print("=" * 50)
    
    microscope = Microscope()
    microscope.list_audio_devices()
    
    print("\nStarting listener...")
    print("This PC will:")
    print("  - Listen for RUN command")
    print("  - Send RUN_COMMAND_RECEIVED acknowledgment")
    print("  - Execute task")
    print("  - Send RUN_DONE when complete")
    print("\nPress Ctrl+C to stop\n")
    
    # Set up listener with callback
    handler = create_command_handler(microscope)
    microscope.start_listening(callback=handler)
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping listener...")
        microscope.stop_listening()
        print("Listener stopped.")

if __name__ == "__main__":
    main()
