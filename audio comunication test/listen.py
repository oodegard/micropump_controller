"""
Listener mode - Run this on the PC that will receive commands.

This script continuously listens for audio commands and responds appropriately:
- When RUN is received, it sends RUN_COMMAND_RECEIVED, performs a task, then sends RUN_DONE
- Logs all received commands with timestamps
"""

import time
from audio_comm import AudioListener, AudioCommander, list_audio_devices

def perform_task():
    """
    Placeholder for the actual task to be performed.
    Replace this with your real task logic.
    """
    print("  [TASK] Starting task execution...")
    time.sleep(2)  # Simulate task taking 2 seconds
    print("  [TASK] Task completed!")

def command_handler(command: str):
    """Handle received commands and execute appropriate responses."""
    print(f">>> RECEIVED: {command}")
    
    commander = AudioCommander()
    
    if command == 'RUN':
        # Acknowledge receipt
        time.sleep(0.3)
        print("  -> Sending acknowledgment...")
        commander.send_command('RUN_COMMAND_RECEIVED')
        
        # Perform the actual task
        perform_task()
        
        # Signal completion
        time.sleep(0.3)
        print("  -> Sending completion signal...")
        commander.send_command('RUN_DONE')
        print("  ✓ Workflow complete\n")

def main():
    print("Audio Communication - LISTEN MODE")
    print("=" * 50)
    list_audio_devices()
    
    print("\nStarting listener...")
    print("This PC will:")
    print("  - Listen for RUN command")
    print("  - Send RUN_COMMAND_RECEIVED acknowledgment")
    print("  - Execute task")
    print("  - Send RUN_DONE when complete")
    print("\nPress Ctrl+C to stop\n")
    
    # Set up listener with callback
    listener = AudioListener(callback=command_handler)
    listener.start_listening()
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping listener...")
        listener.stop_listening()
        print("Listener stopped.")

if __name__ == "__main__":
    main()
