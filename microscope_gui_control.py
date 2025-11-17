"""
Microscope GUI control via audio commands.

This script listens for audio commands and controls the microscope GUI:
- When RUN is received, it finds and clicks the run button, then sends acknowledgments
- Sends RUN_COMMAND_RECEIVED after button click
- Sends RUN_DONE when complete

The button image (run.png) should be placed in the same directory as this script.
"""

import sys
import os
import time
import pyautogui
from typing import Optional

# Add audio communication test folder to path
_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio comunication test")
if _AUDIO_DIR not in sys.path:
    sys.path.insert(0, _AUDIO_DIR)

from audio_comm import AudioListener, AudioCommander, list_audio_devices

# Configuration
BUTTON_IMAGE = "run.png"  # Path to the button image to find and click
CONFIDENCE = 0.8  # Match confidence (0.0 to 1.0)
MOUSE_MOVE_AWAY_OFFSET = 200  # Pixels to move mouse away after click


def find_and_click_button(button_image: str) -> bool:
    """
    Find the button on screen and click it.
    
    Args:
        button_image: Path to the button image file
        
    Returns:
        True if button was found and clicked, False otherwise
    """
    try:
        # Get absolute path if relative
        if not os.path.isabs(button_image):
            button_image = os.path.join(os.path.dirname(__file__), button_image)
        
        if not os.path.exists(button_image):
            print(f"  [ERROR] Button image not found: {button_image}")
            return False
        
        print(f"  [TASK] Searching for button on screen...")
        
        # Locate the button on screen
        location = pyautogui.locateOnScreen(button_image, confidence=CONFIDENCE)
        
        if location is None:
            print(f"  [ERROR] Button not found on screen (confidence={CONFIDENCE})")
            return False
        
        # Get center coordinates
        center = pyautogui.center(location)
        print(f"  [TASK] Button found at position: {center}")
        
        # Click the button
        print(f"  [TASK] Clicking button...")
        pyautogui.click(center)
        time.sleep(0.1)  # Brief pause after click
        
        # Move mouse away
        screen_width, screen_height = pyautogui.size()
        new_x = min(center.x + MOUSE_MOVE_AWAY_OFFSET, screen_width - 10)
        new_y = center.y
        
        print(f"  [TASK] Moving mouse away to ({new_x}, {new_y})...")
        pyautogui.moveTo(new_x, new_y, duration=0.2)
        
        print(f"  [TASK] Button click completed successfully")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Exception during button click: {e}")
        return False


def command_handler(command: str):
    """Handle received audio commands."""
    print(f">>> RECEIVED: {command}")
    
    commander = AudioCommander()
    
    if command == 'RUN':
        # Find and click the button
        success = find_and_click_button(BUTTON_IMAGE)
        
        # Send acknowledgment
        time.sleep(0.3)
        print("  -> Sending acknowledgment...")
        commander.send_command('RUN_COMMAND_RECEIVED')
        
        if success:
            # Signal completion
            time.sleep(0.3)
            print("  -> Sending completion signal...")
            commander.send_command('RUN_DONE')
            print("  ✓ Workflow complete\n")
        else:
            print("  ✗ Workflow failed - button not clicked\n")


def main():
    print("Microscope GUI Control - Audio Command Listener")
    print("=" * 60)
    
    # Check if button image exists
    button_path = os.path.join(os.path.dirname(__file__), BUTTON_IMAGE)
    if not os.path.exists(button_path):
        print(f"\n⚠ WARNING: Button image not found: {button_path}")
        print("Please ensure 'run.png' is in the same directory as this script.")
        print("You can still run the script, but button clicking will fail.\n")
    else:
        print(f"✓ Button image found: {button_path}\n")
    
    list_audio_devices()
    
    print("\nStarting listener...")
    print("This script will:")
    print("  - Listen for RUN command")
    print("  - Find and click the run button on screen")
    print("  - Send RUN_COMMAND_RECEIVED acknowledgment")
    print("  - Send RUN_DONE when complete")
    print(f"\nButton image: {BUTTON_IMAGE}")
    print(f"Confidence threshold: {CONFIDENCE}")
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
