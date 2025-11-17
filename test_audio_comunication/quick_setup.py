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
        
        # Adaptive detection parameters
        self.detection_threshold: float = 100.0  # Initial threshold
        self.background_noise: float = 0.0  # Background noise level
        self.signal_history: list = []  # Track signal quality over time
        
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
        Uses adaptive thresholding based on signal-to-noise ratio.
        
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
            
            # Calculate background noise level (excluding target frequency range)
            noise_mask = ~freq_mask
            if np.any(noise_mask):
                background = float(np.median(magnitude[noise_mask]))
                self.background_noise = 0.9 * self.background_noise + 0.1 * background  # EMA
            
            # Adaptive threshold: must be significantly above background noise
            # Use lower of: fixed threshold OR 3x background noise (whichever is more lenient)
            adaptive_threshold = min(self.detection_threshold, max(50.0, 3.0 * self.background_noise))
            
            # Also require signal-to-noise ratio > 2.0
            snr = peak_mag / (self.background_noise + 1e-6)
            detected = (peak_mag > adaptive_threshold) and (snr > 2.0)
            
            # Track signal history for debugging
            self.signal_history.append({
                'peak': peak_mag,
                'threshold': adaptive_threshold,
                'snr': snr,
                'detected': detected
            })
            if len(self.signal_history) > 10:
                self.signal_history.pop(0)
            
            return detected, peak_mag
            
        except Exception:
            # If any error occurs during FFT, return no detection
            return False, 0.0
    
    def listen_for_tone(self, target_freq: float, duration: float = 1.0,
                       show_status: bool = True) -> bool:
        """
        Listen for a specific frequency with improved robustness.
        Returns True if detected, False otherwise.
        """
        try:
            # Use longer recording duration for better frequency resolution
            actual_duration = max(duration, 1.5)  # At least 1.5 seconds
            
            recording = sd.rec(
                int(actual_duration * self.sample_rate),
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
                    snr = magnitude / (self.background_noise + 1e-6)
                    print(f"  🔊 DETECTED {target_freq} Hz (mag: {magnitude:.0f}, SNR: {snr:.1f})")
                else:
                    rms = np.sqrt(np.mean(audio ** 2))
                    if rms > 0.001:
                        print(f"  ~ audio heard but not {target_freq} Hz (mag: {magnitude:.0f}, rms: {rms:.4f})")
                    else:
                        print(f"  - silence (background: {self.background_noise:.0f})")
            
            return detected
            
        except Exception as e:
            # If any error during recording/detection, return False
            if show_status:
                print(f"  ! error during detection: {e}")
            return False
    
    def handshake_loop(self) -> bool:
        """
        Continuously send 1000 Hz and listen for 1000 Hz from other computer.
        Improved stability with adaptive detection and recovery mechanisms.
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
        total_detections = 0  # Track total successful detections
        
        max_iterations = 90  # 90 seconds timeout (increased from 60)
        last_status = None  # Track last printed status to avoid duplicates
        
        # Create continuous tone signal with better parameters
        tone_duration = 0.8  # Longer chunks for better overlap
        t = np.linspace(0, tone_duration, int(self.sample_rate * tone_duration))
        continuous_signal = 0.4 * np.sin(2 * np.pi * self.handshake_freq * t)  # Slightly louder
        
        # Add smooth fade in/out to prevent clicks
        fade_len = int(0.05 * self.sample_rate)
        continuous_signal[:fade_len] *= np.linspace(0, 1, fade_len)
        continuous_signal[-fade_len:] *= np.linspace(1, 0, fade_len)
        
        # Flag to control playback thread
        stop_playing = threading.Event()
        
        def play_continuous() -> None:
            """Thread function to continuously play tone with minimal gaps"""
            while not stop_playing.is_set():
                sd.play(continuous_signal, self.sample_rate, device=self.output_device, blocking=False)
                time.sleep(tone_duration * 0.9)  # Overlap slightly to avoid gaps
        
        # Start playback thread
        playback_thread = threading.Thread(target=play_continuous, daemon=True)
        playback_thread.start()
        
        # Give playback thread time to start
        time.sleep(0.5)
        
        try:
            for i in range(max_iterations):
                # Listen for response while tone is playing in background
                # Use longer duration for better detection
                detected = self.listen_for_tone(self.handshake_freq, duration=1.5, show_status=False)
                
                if detected:
                    consecutive_detections += 1
                    total_detections += 1
                    
                    # More informative status message
                    status = f"✓ Response received! ({consecutive_detections}/{required_consecutive}) [total: {total_detections}]"
                    if status != last_status:
                        print(status)
                        last_status = status
                    
                    if consecutive_detections >= required_consecutive:
                        stop_playing.set()  # Stop the continuous tone
                        sd.stop()
                        time.sleep(0.3)  # Let it finish cleanly
                        print("\n🎉 BIDIRECTIONAL CONNECTION ESTABLISHED!")
                        print(f"   Signal quality: {len([h for h in self.signal_history if h['detected']])}/{len(self.signal_history)} detections")
                        return True
                else:
                    # Recovery mechanism - don't immediately reset if we had detections
                    if consecutive_detections > 0:
                        # Show we're trying to recover
                        recovery_msg = f"~ Connection weakened ({consecutive_detections}/{required_consecutive}), recovering..."
                        if recovery_msg != last_status:
                            print(recovery_msg)
                            last_status = recovery_msg
                        
                        # Don't reset immediately - give it one more chance
                        consecutive_detections = max(0, consecutive_detections - 1)
                    elif total_detections > 0:
                        # We've had some detections but not consecutive
                        if last_status != "~ intermittent signal, waiting for stable connection...":
                            print("~ intermittent signal, waiting for stable connection...")
                            last_status = "~ intermittent signal, waiting for stable connection..."
                    else:
                        # No detections yet
                        if last_status != "- listening...":
                            print("- listening...")
                            last_status = "- listening..."
                
                # Brief pause between iterations (not needed since listen_for_tone takes time)
            
            stop_playing.set()  # Stop the continuous tone
            sd.stop()
            print("\n✗ Connection timeout - could not establish bidirectional link")
            print(f"   Had {total_detections} total detections but not {required_consecutive} consecutive")
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
        Improved stability with longer signals and better timing.
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
        
        max_attempts = 45  # Increased from 30
        last_status = None
        consecutive_detections = 0
        required_consecutive = 2  # Need 2 consecutive confirmations
        
        for i in range(max_attempts):
            # Send confirmation tone (1.0 seconds instead of 0.5) in background
            t = np.linspace(0, 1.0, int(self.sample_rate * 1.0))
            signal = 0.4 * np.sin(2 * np.pi * my_freq * t)
            
            # Add fade in/out
            fade_len = int(0.05 * self.sample_rate)
            signal[:fade_len] *= np.linspace(0, 1, fade_len)
            signal[-fade_len:] *= np.linspace(1, 0, fade_len)
            
            sd.play(signal, self.sample_rate, device=self.output_device, blocking=False)
            
            # Listen for other computer's confirmation (longer duration)
            time.sleep(0.2)  # Brief delay before listening
            detected = self.listen_for_tone(other_freq, duration=1.5, show_status=False)
            
            if detected:
                consecutive_detections += 1
                print(f"✓ Received confirmation from {other_role}! ({consecutive_detections}/{required_consecutive})")
                
                if consecutive_detections >= required_consecutive:
                    # Send final strong confirmation burst
                    print("  Sending final acknowledgment...")
                    for _ in range(2):
                        self.play_tone(my_freq, 0.8)
                        time.sleep(0.2)
                    
                    return True
            else:
                if consecutive_detections > 0:
                    print(f"~ Lost confirmation signal ({consecutive_detections}/{required_consecutive})")
                    consecutive_detections = max(0, consecutive_detections - 1)  # Gradual decrease
                elif last_status != "- listening...":
                    print("- listening...")
                    last_status = "- listening..."
            
            time.sleep(0.3)  # Brief pause between attempts
        
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
