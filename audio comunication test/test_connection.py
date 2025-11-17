"""
Test script to verify audio communication setup.

This script can be used to test the connection by:
1. Recording a sample to verify input is working
2. Playing a test tone to verify output is working
3. Running a loopback test (if you connect output to input on same PC)
"""

import numpy as np
import sounddevice as sd
import time
from audio_comm import AudioCommander, AudioListener, list_audio_devices, SAMPLE_RATE

def test_output():
    """Test audio output by playing a simple beep."""
    print("\n=== Testing Audio Output ===")
    print("You should hear a beep...")
    
    duration = 0.5  # seconds
    frequency = 1000  # Hz
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    beep = 0.3 * np.sin(2 * np.pi * frequency * t)
    
    sd.play(beep, samplerate=SAMPLE_RATE)
    sd.wait()
    print("Output test complete.")

def test_input():
    """Test audio input by recording and showing levels."""
    print("\n=== Testing Audio Input ===")
    print("Speak or make noise near the microphone for 3 seconds...")
    
    duration = 3  # seconds
    recording = sd.rec(int(duration * SAMPLE_RATE), 
                      samplerate=SAMPLE_RATE, 
                      channels=1,
                      dtype='float32')
    sd.wait()
    
    # Calculate signal strength
    max_level = np.max(np.abs(recording))
    avg_level = np.mean(np.abs(recording))
    
    print(f"Recording complete.")
    print(f"  Max level: {max_level:.4f}")
    print(f"  Avg level: {avg_level:.4f}")
    
    if max_level < 0.01:
        print("  WARNING: Very low signal! Check microphone connection.")
    elif max_level > 0.9:
        print("  WARNING: Signal may be clipping! Reduce input volume.")
    else:
        print("  Signal levels look good!")

def test_command_send():
    """Test sending a command."""
    print("\n=== Testing Command Send ===")
    print("Sending RUN command...")
    
    commander = AudioCommander()
    success = commander.send_command('RUN')
    
    if success:
        print("Command sent successfully!")
    else:
        print("Failed to send command.")

def test_command_receive():
    """Test receiving commands for a short duration."""
    print("\n=== Testing Command Receive ===")
    print("Listening for 10 seconds...")
    print("Send a command from the other PC now!")
    
    received_commands = []
    
    def callback(command):
        received_commands.append(command)
        print(f"  Detected: {command}")
    
    listener = AudioListener(callback=callback)
    listener.start_listening()
    
    time.sleep(10)
    listener.stop_listening()
    
    print(f"\nReceived {len(received_commands)} command(s)")

def main():
    print("Audio Communication - CONNECTION TEST")
    print("=" * 50)
    list_audio_devices()
    
    print("\nSelect test:")
    print("  1. Test output (play beep)")
    print("  2. Test input (record and show levels)")
    print("  3. Test command send")
    print("  4. Test command receive")
    print("  5. Run all tests")
    print("  q. Quit")
    
    while True:
        choice = input("\n> ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '1':
            test_output()
        elif choice == '2':
            test_input()
        elif choice == '3':
            test_command_send()
        elif choice == '4':
            test_command_receive()
        elif choice == '5':
            test_output()
            time.sleep(1)
            test_input()
            time.sleep(1)
            test_command_send()
            time.sleep(1)
            test_command_receive()
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
