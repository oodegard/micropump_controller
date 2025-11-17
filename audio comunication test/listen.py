"""
Listener mode - Run this on the PC that will receive commands.

This script continuously listens for audio commands and responds appropriately:
- When RUN is received, it sends RUN_COMMAND_RECEIVED back
- Logs all received commands with timestamps
"""

import time
from audio_comm import AudioListener, AudioCommander, list_audio_devices, command_received_handler

def main():
    print("Audio Communication - LISTEN MODE")
    print("=" * 50)
    list_audio_devices()
    
    print("\nStarting listener...")
    print("This PC will:")
    print("  - Listen for incoming commands")
    print("  - Auto-respond to RUN with RUN_COMMAND_RECEIVED")
    print("  - Log all received commands")
    print("\nPress Ctrl+C to stop\n")
    
    # Set up listener with callback
    listener = AudioListener(callback=command_received_handler)
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
