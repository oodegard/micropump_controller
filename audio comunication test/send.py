"""
Sender mode - Run this on the PC that will send commands.

This script provides an interactive interface to send commands to the other PC.
"""

import sys
from audio_comm import AudioCommander, list_audio_devices, COMMAND_TONES

def main():
    print("Audio Communication - SEND MODE")
    print("=" * 50)
    list_audio_devices()
    
    commander = AudioCommander()
    
    print("\nAvailable commands:")
    for i, cmd in enumerate(COMMAND_TONES.keys(), 1):
        print(f"  {i}. {cmd}")
    print("  q. Quit")
    
    print("\nEnter command number to send, or 'q' to quit:")
    
    commands_list = list(COMMAND_TONES.keys())
    
    while True:
        try:
            user_input = input("\n> ").strip().lower()
            
            if user_input == 'q':
                print("Goodbye!")
                break
            
            if user_input.isdigit():
                idx = int(user_input) - 1
                if 0 <= idx < len(commands_list):
                    command = commands_list[idx]
                    commander.send_command(command)
                else:
                    print("Invalid command number")
            else:
                # Try to match command name
                cmd_upper = user_input.upper()
                if cmd_upper in COMMAND_TONES:
                    commander.send_command(cmd_upper)
                else:
                    print("Unknown command. Enter a number or 'q' to quit.")
                    
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
