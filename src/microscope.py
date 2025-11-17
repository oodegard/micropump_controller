"""
Microscope control via audio communication

Uses FSK audio modem for bidirectional communication with airgapped microscope PC.
Sends CAPTURE command and waits for DONE response.
"""

import sounddevice as sd
import numpy as np
import time
from pathlib import Path
from typing import Optional, Tuple
import logging

# Add test_audio_comunication to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "test_audio_comunication"))
from audio_config import load_audio_config, save_audio_config
from audio_protocol import AudioModem, Command, FSKConfig


class Microscope:
    """
    Bidirectional microscope controller using FSK audio modem.
    
    Sends CAPTURE command to trigger acquisition, waits for DONE response.
    Automatically establishes handshake with receiver on initialization.
    """
    
    def __init__(self, output_device: Optional[int] = None, input_device: Optional[int] = None,
                 auto_handshake: bool = True):
        """
        Initialize microscope controller.
        
        Args:
            output_device: Audio output device ID. If None, uses saved or default device.
            input_device: Audio input device ID. If None, uses saved or default device.
            auto_handshake: If True, automatically perform handshake during initialization.
        """
        self.is_initialized = False
        self.is_connected = False
        self.last_error = ""
        self.output_device = output_device
        self.input_device = input_device
        self.sample_rate: int = 44100
        
        # Handshake frequencies (matching quick_setup.py)
        self.calling_tone: int = 900   # Sender sends this
        self.answer_tone: int = 1100   # Receiver responds with this
        
        # Detection parameters
        self.detection_threshold: float = 15.0
        self.background_noise: float = 0.0
        self.signal_history: list = []
        
        # Load saved devices if not specified
        config = load_audio_config()
        
        if self.output_device is None:
            self.output_device = config.get('output_device')
            if self.output_device is None:
                try:
                    self.output_device = sd.default.device[1]
                    save_audio_config(output_device=self.output_device)
                except Exception as e:
                    self.last_error = f"Failed to get default output device: {e}"
                    logging.error(self.last_error)
                    return
        
        if self.input_device is None:
            self.input_device = config.get('input_device')
            if self.input_device is None:
                try:
                    self.input_device = sd.default.device[0]
                    save_audio_config(input_device=self.input_device)
                except Exception as e:
                    self.last_error = f"Failed to get default input device: {e}"
                    logging.error(self.last_error)
                    return
        
        # Initialize FSK modem
        self.modem = AudioModem(FSKConfig())
        
        self.is_initialized = True
        logging.info(f"Microscope controller initialized (output: {self.output_device}, input: {self.input_device})")
        
        # Perform handshake if requested
        if auto_handshake:
            print("\nEstablishing connection with microscope...")
            if not self.establish_handshake():
                self.last_error = "Handshake failed"
                self.is_initialized = False
                logging.error("Failed to establish handshake with microscope")
    
    def acquire(self, timeout: float = 300.0) -> bool:
        """
        Trigger image acquisition on microscope and wait for completion.
        
        Sends CAPTURE command via audio, waits for DONE response from microscope.
        Automatically establishes handshake if not already connected.
        
        Args:
            timeout: Maximum time to wait for acquisition completion (default: 5 minutes)
        
        Returns:
            True if acquisition completed successfully, False on timeout or error
        """
        if not self.is_initialized:
            print(f"✗ Microscope not initialized: {self.last_error}")
            return False
        
        # Establish handshake if not already connected
        if not self.is_connected:
            print("📡 Establishing connection with microscope...")
            try:
                if not self.establish_handshake():
                    print("✗ Failed to establish connection with microscope")
                    return False
            except KeyboardInterrupt:
                print("\n✗ Connection interrupted by user")
                raise
        
        try:
            print("🔊 Triggering microscope acquisition...")
            
            # Send CAPTURE command
            audio = self.modem.encode_command(Command.CAPTURE)
            sd.play(audio, self.modem.config.sample_rate, device=self.output_device)
            sd.wait()
            
            print("✓ CAPTURE command sent")
            logging.info("CAPTURE command sent to microscope")
            
            # Wait for DONE response
            print(f"⏳ Waiting for acquisition to complete (timeout: {timeout}s)...")
            done_received = self._wait_for_done(timeout)
            
            if done_received:
                print("✓ Microscope acquisition complete!")
                logging.info("Received DONE signal from microscope")
                return True
            else:
                print("✗ Timeout waiting for microscope completion")
                logging.warning(f"No DONE signal received within {timeout}s")
                return False
            
        except KeyboardInterrupt:
            print("\n✗ Acquisition interrupted by user")
            raise
        except Exception as e:
            self.last_error = f"Acquisition failed: {e}"
            print(f"✗ {self.last_error}")
            logging.error(self.last_error)
            return False
    
    def detect_frequency(self, audio: np.ndarray, target_freq: float, 
                        tolerance: float = 50.0) -> Tuple[bool, float]:
        """
        Detect if a specific frequency is present in audio.
        Uses adaptive thresholding based on signal-to-noise ratio.
        
        Returns: (detected, peak_magnitude)
        """
        if len(audio) == 0 or np.all(audio == 0):
            return False, 0.0
        
        try:
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1 / self.sample_rate)
            magnitude = np.abs(fft)
            
            # Find peak near target frequency
            freq_mask = (freqs >= target_freq - tolerance) & (freqs <= target_freq + tolerance)
            if not np.any(freq_mask):
                return False, 0.0
            
            peak_mag = float(np.max(magnitude[freq_mask]))
            
            if np.isnan(peak_mag) or np.isinf(peak_mag):
                return False, 0.0
            
            # Calculate background noise
            noise_mask = ~freq_mask
            if np.any(noise_mask):
                background = float(np.median(magnitude[noise_mask]))
                self.background_noise = 0.9 * self.background_noise + 0.1 * background
            
            # Adaptive threshold
            adaptive_threshold = min(self.detection_threshold, max(10.0, 1.5 * self.background_noise))
            
            # Require SNR > 1.2
            snr = peak_mag / (self.background_noise + 1e-6)
            detected = (peak_mag > adaptive_threshold) and (snr > 1.2)
            
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
            return False, 0.0
    
    def listen_for_tone(self, target_freq: float, duration: float = 1.5) -> bool:
        """
        Listen for a specific frequency.
        Returns True if detected, False otherwise.
        """
        try:
            actual_duration = max(duration, 1.5)
            
            recording = sd.rec(
                int(actual_duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                device=self.input_device,
                dtype='float32'
            )
            sd.wait()
            
            audio = recording[:, 0]
            
            if len(audio) == 0:
                return False
            
            detected, magnitude = self.detect_frequency(audio, target_freq)
            return detected
            
        except Exception:
            return False
    
    def establish_handshake(self) -> bool:
        """
        Sender (calling) side of handshake:
        1. Send continuous 900 Hz calling tone
        2. Listen for 1100 Hz answer tone from receiver
        3. Once answer detected 3 times, STOP calling and confirm
        
        Returns:
            True if handshake successful, False otherwise
        """
        print("\n" + "=" * 70)
        print("ESTABLISHING CONNECTION - SENDER MODE")
        print("=" * 70)
        print("\nSending 900 Hz calling tone...")
        print("Waiting for 1100 Hz answer from receiver...")
        print("(Press Ctrl+C to cancel)\n")
        
        # Create calling tone
        tone_duration = 0.5
        t = np.linspace(0, tone_duration, int(self.sample_rate * tone_duration))
        calling_signal = 0.4 * np.sin(2 * np.pi * self.calling_tone * t)
        
        # Add fade
        fade_len = int(0.02 * self.sample_rate)
        calling_signal[:fade_len] *= np.linspace(0, 1, fade_len)
        calling_signal[-fade_len:] *= np.linspace(1, 0, fade_len)
        
        consecutive_detections = 0
        required_consecutive = 3
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Send calling tone
                sd.play(calling_signal, self.sample_rate, device=self.output_device, blocking=True)
                
                # Brief delay
                time.sleep(0.2)
                
                # Listen for answer tone
                print(f"[{iteration}] Listening for 1100 Hz answer tone...", end=' ', flush=True)
                detected = self.listen_for_tone(self.answer_tone, duration=1.5)
                
                if detected:
                    consecutive_detections += 1
                    print(f"✓ DETECTED! ({consecutive_detections}/{required_consecutive})")
                    
                    if consecutive_detections >= required_consecutive:
                        # STOP sending calling tone so receiver knows we're done
                        sd.stop()
                        print("\n✓ Answer confirmed! Stopping calling tone...")
                        
                        # Wait for receiver to detect we stopped
                        time.sleep(2.0)
                        
                        print("🎉 CONNECTION ESTABLISHED!")
                        self.is_connected = True
                        return True
                else:
                    if len(self.signal_history) > 0:
                        last_sig = self.signal_history[-1]
                        print(f"not detected (peak: {last_sig['peak']:.0f}, threshold: {last_sig['threshold']:.0f})")
                    else:
                        print("not detected")
                    
                    if consecutive_detections > 0:
                        print("  Lost answer tone... resetting")
                    consecutive_detections = 0
                    
        except KeyboardInterrupt:
            sd.stop()
            print("\n✗ Connection cancelled by user")
            raise  # Re-raise to allow caller to handle
        except Exception as e:
            sd.stop()
            print(f"\n✗ Handshake error: {e}")
            logging.error(f"Handshake error: {e}")
            return False
    
    def _wait_for_done(self, timeout: float) -> bool:
        """
        Listen for DONE command from microscope.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if DONE received, False on timeout
        """
        sample_rate = self.modem.config.sample_rate
        start_time = time.time()
        chunk_duration = 5.0  # Record in 5-second chunks
        chunk_num = 0
        
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            remaining = int(timeout - elapsed)
            chunk_num += 1
            
            print(f"  Listening for DONE... ({remaining}s remaining, chunk #{chunk_num})")
            
            # Record audio chunk
            recording = sd.rec(
                int(chunk_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=self.input_device,
                dtype='float32'
            )
            sd.wait()
            
            # Check audio levels for debugging
            audio_data = recording[:, 0]
            max_amp = np.max(np.abs(audio_data))
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            if max_amp > 0.01:
                print(f"    🔊 Sound detected! max={max_amp:.4f}, rms={rms:.4f}")
                debug_mode = True
            elif max_amp > 0.001:
                print(f"    ~ Weak audio: max={max_amp:.4f}, rms={rms:.4f}")
                debug_mode = False
            else:
                print(f"    - Silence: max={max_amp:.4f}")
                debug_mode = False
            
            # Try to decode
            command = self.modem.decode_command(audio_data, debug=debug_mode)
            
            if command == Command.DONE:
                print("    ✓ DONE command received!")
                return True
            elif command is not None:
                print(f"    ⚠ Unexpected command: {command.name} (expecting DONE)")
        
        return False
    
    def close(self) -> None:
        """Cleanup resources"""
        logging.info("Microscope controller closed")


# Backwards compatibility alias
MicroscopeController = Microscope


# For testing
if __name__ == "__main__":
    print("=" * 70)
    print("MICROSCOPE CONTROLLER TEST")
    print("=" * 70)
    
    microscope = Microscope()
    
    if not microscope.is_initialized:
        print(f"✗ Failed to initialize: {microscope.last_error}")
    else:
        print("✓ Microscope controller initialized")
        print(f"  Using output device: {microscope.output_device}")
        
        input("\nPress Enter to send trigger signal...")
        
        if microscope.acquire():
            print("\n✓ Success!")
        else:
            print("\n✗ Failed!")
        
        microscope.close()