"""
Quick Setup - Automatic Two-PC Audio Communication Setup

Just run this on BOTH computers - it will:
1. Auto-detect audio devices
2. Establish bidirectional connection with 1000 Hz handshake
3. Ask user to identify as sender or receiver
4. Confirm roles with 1200 Hz (sender) or 1100 Hz (receiver)

No manual device selection needed!
"""

import numpy as np
import sounddevice as sd
import time
import sys
import threading
from typing import Optional, Tuple
from enum import Enum


class Role(Enum):
    """Computer role in the system"""
    SENDER = "sender"  # Microfluidics PC
    RECEIVER = "receiver"  # Microscope PC


class QuickSetup:
    """Automatic audio communication setup"""
    
    def __init__(self):
        self.sample_rate: int = 44100
        self.input_device: Optional[int] = None
        self.output_device: Optional[int] = None
        self.is_connected: bool = False
        self.role: Optional[Role] = None
        
        # Frequencies for setup protocol
        self.handshake_freq: int = 1000  # Both send this initially
        self.sender_confirm_freq: int = 1200  # Sender confirms with this
        self.receiver_confirm_freq: int = 1100  # Receiver confirms with this
        
    def find_working_input_device(self) -> Optional[int]:
        """
        Automatically find a working input device by testing each one.
        Returns device ID or None if none found.
        """
        print("🎤 Auto-detecting microphone...")
        
        all_devices = sd.query_devices()
        input_devices = [(i, dev) for i, dev in enumerate(all_devices) 
                        if dev['max_input_channels'] > 0]
        
        if not input_devices:
            print("  ✗ No input devices found!")
            return None
        
        # Try default first
        try:
            default_id = sd.default.device[0]
            default_device = sd.query_devices(default_id)
            if default_device['max_input_channels'] > 0:
                print(f"  ✓ Using default: {default_device['name'][:50]}")
                return default_id
        except:
            pass
        
        # Otherwise use first available
        device_id, device = input_devices[0]
        print(f"  ✓ Using: {device['name'][:50]}")
        return device_id
    
    def find_working_output_device(self) -> Optional[int]:
        """
        Automatically find a working output device.
        Returns device ID or None if none found.
        """
        print("🔊 Auto-detecting speakers...")
        
        try:
            default_id = sd.default.device[1]
            default_device = sd.query_devices(default_id)
            print(f"  ✓ Using default: {default_device['name'][:50]}")
            return default_id
        except Exception as e:
            print(f"  ✗ No output device found: {e}")
            return None
    
    def play_tone(self, frequency: float, duration: float) -> None:
        """Play a continuous tone"""
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        signal = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Add fade to prevent clicks
        fade_len = int(0.01 * self.sample_rate)
        if len(signal) > 2 * fade_len:
            signal[:fade_len] *= np.linspace(0, 1, fade_len)
            signal[-fade_len:] *= np.linspace(1, 0, fade_len)
        
        sd.play(signal, self.sample_rate, device=self.output_device)
        sd.wait()
    
    def detect_frequency(self, audio: np.ndarray, target_freq: float, 
                        tolerance: float = 50.0) -> Tuple[bool, float]:
        """
        Detect if a specific frequency is present in audio.
        
        Returns: (detected, peak_magnitude)
        """
        # Check for valid audio data
        if len(audio) == 0 or np.all(audio == 0):
            return False, 0.0
        
        # FFT analysis with error handling
        try:
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1 / self.sample_rate)
            magnitude = np.abs(fft)
            
            # Find peak near target frequency
            freq_mask = (freqs >= target_freq - tolerance) & (freqs <= target_freq + tolerance)
            if not np.any(freq_mask):
                return False, 0.0
            
            peak_mag = float(np.max(magnitude[freq_mask]))
            
            # Check for invalid values
            if np.isnan(peak_mag) or np.isinf(peak_mag):
                return False, 0.0
            
            # Check if peak is significant (threshold for detection)
            threshold = 100.0  # Minimum magnitude to consider as signal
            detected = peak_mag > threshold
            
            return detected, peak_mag
            
        except Exception:
            # If any error occurs during FFT, return no detection
            return False, 0.0
    
    def listen_for_tone(self, target_freq: float, duration: float = 1.0,
                       show_status: bool = True) -> bool:
        """
        Listen for a specific frequency.
        Returns True if detected, False otherwise.
        """
        try:
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                device=self.input_device,
                dtype='float32'
            )
            sd.wait()
            
            # Extract audio data safely
            audio = recording[:, 0]
            
            # Check for valid audio
            if len(audio) == 0:
                return False
            
            detected, magnitude = self.detect_frequency(audio, target_freq)
            
            if show_status:
                if detected:
                    print(f"  🔊 DETECTED {target_freq} Hz (magnitude: {magnitude:.0f})")
                else:
                    rms = np.sqrt(np.mean(audio ** 2))
                    if rms > 0.001:
                        print(f"  ~ audio heard but not {target_freq} Hz (rms: {rms:.4f})")
                    else:
                        print(f"  - silence")
            
            return detected
            
        except Exception as e:
            # If any error during recording/detection, return False
            if show_status:
                print(f"  ! error during detection: {e}")
            return False
    
    def handshake_loop(self) -> bool:
        """
        Continuously send 1000 Hz and listen for 1000 Hz from other computer.
        Once bidirectional connection established, return True.
        """
        print("\n" + "=" * 70)
        print("ESTABLISHING CONNECTION")
        print("=" * 70)
        print("\nSending continuous 1000 Hz handshake signal...")
        print("Listening for response from other computer...")
        print("(Press Ctrl+C to cancel)\n")
        
        consecutive_detections = 0
        required_consecutive = 3  # Need 3 consecutive detections to confirm
        
        max_iterations = 60  # 60 seconds timeout
        last_status = None  # Track last printed status to avoid duplicates
        
        # Create continuous tone signal
        tone_duration = 0.5  # Half second chunks, will loop
        t = np.linspace(0, tone_duration, int(self.sample_rate * tone_duration))
        continuous_signal = 0.3 * np.sin(2 * np.pi * self.handshake_freq * t)
        
        # Flag to control playback thread
        stop_playing = threading.Event()
        
        def play_continuous() -> None:
            """Thread function to continuously play tone"""
            while not stop_playing.is_set():
                sd.play(continuous_signal, self.sample_rate, device=self.output_device)
                sd.wait()
        
        # Start playback thread
        playback_thread = threading.Thread(target=play_continuous, daemon=True)
        playback_thread.start()
        
        try:
            for i in range(max_iterations):
                # Listen for response while tone is playing in background
                detected = self.listen_for_tone(self.handshake_freq, duration=1.0, show_status=False)
                
                if detected:
                    consecutive_detections += 1
                    status = f"✓ Response received! ({consecutive_detections}/{required_consecutive})"
                    if status != last_status:
                        print(status)
                        last_status = status
                    
                    if consecutive_detections >= required_consecutive:
                        stop_playing.set()  # Stop the continuous tone
                        sd.stop()
                        time.sleep(0.2)  # Let it finish
                        print("\n🎉 BIDIRECTIONAL CONNECTION ESTABLISHED!")
                        return True
                else:
                    if consecutive_detections > 0:
                        print("Lost connection... resetting")
                        last_status = None
                    elif last_status != "- listening...":
                        print("- listening...")
                        last_status = "- listening..."
                    consecutive_detections = 0
            
            stop_playing.set()  # Stop the continuous tone
            sd.stop()
            print("\n✗ Connection timeout - could not establish bidirectional link")
            return False
            
        except KeyboardInterrupt:
            stop_playing.set()
            sd.stop()
            raise
    
    def ask_role(self) -> Optional[Role]:
        """
        Ask user to identify as sender or receiver.
        Returns Role or None if cancelled.
        """
        print("\n" + "=" * 70)
        print("IDENTIFY COMPUTER ROLE")
        print("=" * 70)
        print("\nWhich computer is this?")
        print("  [S] Sender (Microfluidics PC - controls experiments)")
        print("  [R] Receiver (Microscope PC - captures images)")
        print()
        
        while True:
            response = input("Enter S or R: ").strip().upper()
            
            if response == 'S':
                return Role.SENDER
            elif response == 'R':
                return Role.RECEIVER
            else:
                print("Invalid input. Please enter S or R.")
    
    def confirm_role(self) -> bool:
        """
        Confirm role by:
        - Sender sends 1200 Hz
        - Receiver sends 1100 Hz
        
        Then both listen for the other's confirmation.
        Returns True if successful.
        """
        print("\n" + "=" * 70)
        print("CONFIRMING ROLES")
        print("=" * 70)
        
        if self.role == Role.SENDER:
            my_freq = self.sender_confirm_freq
            other_freq = self.receiver_confirm_freq
            other_role = "RECEIVER"
            print(f"\nI am SENDER - sending {my_freq} Hz")
            print(f"Waiting for RECEIVER to send {other_freq} Hz...")
            print("(Press Ctrl+C to cancel)\n")
        else:
            my_freq = self.receiver_confirm_freq
            other_freq = self.sender_confirm_freq
            other_role = "SENDER"
            print(f"\nI am RECEIVER - sending {my_freq} Hz")
            print(f"Waiting for SENDER to send {other_freq} Hz...")
            print("(Press Ctrl+C to cancel)\n")
        
        max_attempts = 30
        last_status = None
        
        for i in range(max_attempts):
            # Send confirmation tone (0.5 seconds) in background
            t = np.linspace(0, 0.5, int(self.sample_rate * 0.5))
            signal = 0.3 * np.sin(2 * np.pi * my_freq * t)
            sd.play(signal, self.sample_rate, device=self.output_device, blocking=False)
            
            # Listen for other computer's confirmation
            time.sleep(0.1)
            detected = self.listen_for_tone(other_freq, duration=0.5, show_status=False)
            
            if detected:
                print(f"✓ Received confirmation from {other_role}!")
                
                # Send one final confirmation
                print("  Sending final acknowledgment...")
                self.play_tone(my_freq, 0.5)
                
                return True
            else:
                if last_status != "- listening...":
                    print("- listening...")
                    last_status = "- listening..."
            
            time.sleep(0.5)
        
        print(f"\n✗ Timeout - did not receive confirmation from other computer")
        return False
    
    def run(self) -> bool:
        """
        Run the complete setup process.
        Returns True if successful.
        """
        print("=" * 70)
        print("QUICK AUDIO SETUP")
        print("=" * 70)
        print("\nAutomatic bidirectional audio communication setup")
        print("Run this on BOTH computers simultaneously!\n")
        
        # Step 1: Auto-detect audio devices
        self.input_device = self.find_working_input_device()
        self.output_device = self.find_working_output_device()
        
        if self.input_device is None or self.output_device is None:
            print("\n✗ Could not find working audio devices!")
            print("Please check:")
            print("  - Microphone is connected and not muted")
            print("  - Speakers/headphones are connected")
            print("  - Windows audio permissions are enabled")
            return False
        
        print("\n✓ Audio devices configured")
        
        # Step 2: Establish bidirectional connection with handshake
        if not self.handshake_loop():
            return False
        
        self.is_connected = True
        
        # Step 3: Ask user to identify role
        self.role = self.ask_role()
        if self.role is None:
            return False
        
        # Step 4: Confirm roles with frequency exchange
        if not self.confirm_role():
            return False
        
        # Success!
        print("\n" + "=" * 70)
        print("✓ SETUP COMPLETE!")
        print("=" * 70)
        print(f"\nThis computer is configured as: {self.role.value.upper()}")
        print("Audio communication is working bidirectionally.")
        print("\nReady to run communication tests!")
        print("=" * 70)
        
        return True


def main() -> None:
    """Main entry point"""
    setup = QuickSetup()
    
    try:
        success = setup.run()
        
        if success:
            print("\n✓ You can now run the full two-PC test:")
            if setup.role == Role.SENDER:
                print("  uv run python two_pc_test.py sender")
            else:
                print("  uv run python two_pc_test.py receiver")
            
            sys.exit(0)
        else:
            print("\n✗ Setup failed. Please check your audio devices.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n✗ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
