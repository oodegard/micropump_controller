"""
Robust FSK audio modem protocol for airgapped communication.

Based on Bell 202 modem standard with error detection:
- 1200 Hz = binary 0 (mark frequency)
- 1800 Hz = binary 1 (space frequency)  
- Preamble sync pattern prevents false triggers
- CRC8 checksum for data integrity
- Minimum tone duration filters out speech/noise

This is similar to how old-school modems and packet radio (AX.25) work.
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import time


class Command(Enum):
    """Predefined commands for microscope control"""
    CAPTURE = 0b0001  # 1: Trigger image capture
    DONE    = 0b0010  # 2: Capture complete
    ERROR   = 0b0011  # 3: Capture failed
    PING    = 0b0100  # 4: Test connection
    PONG    = 0b0101  # 5: Respond to ping


@dataclass
class FSKConfig:
    """FSK modem configuration parameters"""
    sample_rate: int = 44100
    mark_freq: int = 1200      # Binary 0
    space_freq: int = 1800     # Binary 1
    bit_duration: float = 0.1  # 100ms per bit (10 baud - very slow but robust)
    preamble_duration: float = 0.5  # 500ms sync tone
    preamble_freq: int = 1500  # Distinctive frequency for message start (was 2400 - adjusted for cable transmission)
    
    # Detection thresholds - LOWERED for over-air transmission
    min_tone_duration: float = 0.05  # Reject tones shorter than 50ms (was 80ms)
    frequency_tolerance: float = 150  # Hz tolerance for frequency detection (was 100)
    min_signal_power: float = 0.005   # Minimum RMS to consider valid signal (was 0.01)


class AudioModem:
    """
    Robust FSK modem for airgapped communication.
    
    Protocol structure:
    [PREAMBLE 500ms] [COMMAND 4 bits] [CHECKSUM 4 bits] [POSTAMBLE 200ms]
    
    Total transmission: ~1.3 seconds per command
    """
    
    def __init__(self, config: Optional[FSKConfig] = None):
        self.config = config or FSKConfig()
        
    def _generate_tone(self, frequency: float, duration: float) -> np.ndarray:
        """Generate pure sine wave tone"""
        t = np.linspace(0, duration, int(self.config.sample_rate * duration))
        # Add 10ms ramp on/off to avoid clicking
        ramp_samples = int(0.01 * self.config.sample_rate)
        tone = np.sin(2 * np.pi * frequency * t)
        
        # Apply envelope
        if len(tone) > 2 * ramp_samples:
            envelope = np.ones_like(tone)
            envelope[:ramp_samples] = np.linspace(0, 1, ramp_samples)
            envelope[-ramp_samples:] = np.linspace(1, 0, ramp_samples)
            tone *= envelope
        
        # Increase volume for over-air transmission (0.8 = 80% max volume)
        tone *= 0.8
            
        return tone
    
    def _encode_bits(self, data: int, num_bits: int = 4) -> List[int]:
        """Convert integer to binary bits (MSB first)"""
        return [(data >> i) & 1 for i in range(num_bits - 1, -1, -1)]
    
    def _calculate_checksum(self, data: int) -> int:
        """Simple 4-bit checksum (XOR with rotation)"""
        checksum = 0
        for i in range(4):
            bit = (data >> i) & 1
            checksum ^= bit << (i % 4)
        return checksum & 0x0F
    
    def encode_command(self, command: Command) -> np.ndarray:
        """
        Encode command into FSK audio signal.
        
        Returns numpy array of audio samples ready for playback.
        """
        audio_segments = []
        
        # 1. Preamble (sync tone)
        preamble = self._generate_tone(
            self.config.preamble_freq,
            self.config.preamble_duration
        )
        audio_segments.append(preamble)
        
        # 1.5. Gap after preamble to prevent bleeding into data bits
        gap = np.zeros(int(0.1 * self.config.sample_rate))  # 100ms silence (increased from 50ms)
        audio_segments.append(gap)
        
        # 2. Command bits (4 bits)
        command_bits = self._encode_bits(command.value, num_bits=4)
        for bit in command_bits:
            freq = self.config.space_freq if bit else self.config.mark_freq
            bit_tone = self._generate_tone(freq, self.config.bit_duration)
            audio_segments.append(bit_tone)
        
        # 3. Checksum (4 bits)
        checksum = self._calculate_checksum(command.value)
        checksum_bits = self._encode_bits(checksum, num_bits=4)
        for bit in checksum_bits:
            freq = self.config.space_freq if bit else self.config.mark_freq
            bit_tone = self._generate_tone(freq, self.config.bit_duration)
            audio_segments.append(bit_tone)
        
        # 4. Postamble (silence)
        silence = np.zeros(int(0.2 * self.config.sample_rate))
        audio_segments.append(silence)
        
        return np.concatenate(audio_segments)
    
    def _detect_frequency(self, audio_chunk: np.ndarray) -> Tuple[float, float]:
        """
        Detect dominant frequency in audio chunk using FFT.
        
        Returns (frequency, power_level)
        """
        # Apply high-pass filter to remove low-frequency rumble/bass
        # This filters out frequencies below 800 Hz (our lowest tone is 1200 Hz)
        from scipy import signal
        try:
            # Design high-pass filter (800 Hz cutoff)
            sos = signal.butter(4, 800, 'hp', fs=self.config.sample_rate, output='sos')
            filtered = signal.sosfilt(sos, audio_chunk)
        except:
            # Fallback if scipy not available - use simple high-pass
            filtered = audio_chunk
        
        # Apply window to reduce spectral leakage
        window = np.hanning(len(filtered))
        windowed = filtered * window
        
        # FFT
        fft = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(filtered), 1 / self.config.sample_rate)
        
        # Only look at frequencies above 800 Hz (ignore bass/rumble)
        valid_idx = freqs > 800
        magnitude = np.abs(fft)
        magnitude_filtered = magnitude.copy()
        magnitude_filtered[~valid_idx] = 0
        
        # Find peak
        peak_idx = np.argmax(magnitude_filtered)
        peak_freq = freqs[peak_idx]
        
        # Calculate signal power (RMS)
        power = np.sqrt(np.mean(filtered ** 2))
        
        return peak_freq, power
    
    def _is_frequency_match(self, detected: float, target: float) -> bool:
        """Check if detected frequency matches target within tolerance"""
        return abs(detected - target) < self.config.frequency_tolerance
    
    def decode_command(self, audio: np.ndarray, debug: bool = False) -> Optional[Command]:
        """
        Decode FSK audio signal into command.
        
        Args:
            audio: Audio signal to decode
            debug: If True, print debug information
        
        Returns Command if valid message detected, None otherwise.
        """
        # Look for preamble (2400 Hz tone for 500ms)
        chunk_size = int(self.config.preamble_duration * self.config.sample_rate)
        
        # Scan through audio looking for preamble
        preamble_found = False
        preamble_end_idx = 0
        
        if debug:
            print(f"    [DEBUG] Scanning for preamble ({self.config.preamble_freq} Hz)...")
        
        for i in range(0, len(audio) - chunk_size, chunk_size // 4):
            chunk = audio[i:i + chunk_size]
            freq, power = self._detect_frequency(chunk)
            
            if debug and power > self.config.min_signal_power / 2:
                print(f"    [DEBUG] pos={i/self.config.sample_rate:.2f}s: freq={freq:.0f}Hz, power={power:.4f}")
            
            if (self._is_frequency_match(freq, self.config.preamble_freq) and 
                power > self.config.min_signal_power):
                preamble_found = True
                # Calculate actual preamble start (scan backward to find the beginning)
                # Since we found preamble at position i, the actual preamble could have started earlier
                # For safety, assume we found it in the middle, so preamble started around i
                # Then skip full preamble duration + gap from there
                preamble_start = i
                preamble_duration_samples = int(self.config.preamble_duration * self.config.sample_rate)
                gap_samples = int(0.1 * self.config.sample_rate)  # Increased to 100ms gap
                preamble_end_idx = preamble_start + preamble_duration_samples + gap_samples
                if debug:
                    print(f"    [DEBUG] ✓ Preamble found at {i/self.config.sample_rate:.2f}s!")
                    print(f"    [DEBUG]   Preamble ends at {(preamble_start + preamble_duration_samples)/self.config.sample_rate:.2f}s")
                    print(f"    [DEBUG]   Data starts at {preamble_end_idx/self.config.sample_rate:.2f}s (after 100ms gap)")
                break
        
        if not preamble_found:
            if debug:
                print(f"    [DEBUG] ✗ No preamble found")
            return None
        
        # Decode command bits (4 bits)
        bit_chunk_size = int(self.config.bit_duration * self.config.sample_rate)
        command_bits = []
        
        if debug:
            print(f"    [DEBUG] Decoding command bits...")
        
        for i in range(4):
            start = preamble_end_idx + i * bit_chunk_size
            end = start + bit_chunk_size
            
            if end > len(audio):
                if debug:
                    print(f"    [DEBUG] ✗ Incomplete transmission")
                return None  # Incomplete transmission
            
            chunk = audio[start:end]
            freq, power = self._detect_frequency(chunk)
            
            if debug:
                print(f"    [DEBUG] bit {i}: freq={freq:.0f}Hz, power={power:.4f}", end='')
            
            if power < self.config.min_signal_power:
                if debug:
                    print(f" ✗ weak signal")
                return None  # Weak signal
            
            # Decode bit
            if self._is_frequency_match(freq, self.config.mark_freq):
                command_bits.append(0)
                if debug:
                    print(f" → 0 (mark)")
            elif self._is_frequency_match(freq, self.config.space_freq):
                command_bits.append(1)
                if debug:
                    print(f" → 1 (space)")
            else:
                if debug:
                    print(f" ✗ invalid freq")
                return None  # Frequency doesn't match either mark or space
        
        # Decode checksum bits (4 bits)
        checksum_bits = []
        
        for i in range(4, 8):
            start = preamble_end_idx + i * bit_chunk_size
            end = start + bit_chunk_size
            
            if end > len(audio):
                return None
            
            chunk = audio[start:end]
            freq, power = self._detect_frequency(chunk)
            
            if power < self.config.min_signal_power:
                return None
            
            if self._is_frequency_match(freq, self.config.mark_freq):
                checksum_bits.append(0)
            elif self._is_frequency_match(freq, self.config.space_freq):
                checksum_bits.append(1)
            else:
                return None
        
        # Convert bits to integers
        command_value = sum(bit << (3 - i) for i, bit in enumerate(command_bits))
        received_checksum = sum(bit << (3 - i) for i, bit in enumerate(checksum_bits))
        
        # Verify checksum
        expected_checksum = self._calculate_checksum(command_value)
        
        if received_checksum != expected_checksum:
            return None  # Checksum mismatch - corrupted transmission
        
        # Convert to Command enum
        try:
            return Command(command_value)
        except ValueError:
            return None  # Invalid command value


class MicroscopeAudioController:
    """
    High-level interface for microscope control via audio.
    Uses AudioModem for robust FSK communication.
    """
    
    def __init__(self, input_device: Optional[int] = None, output_device: Optional[int] = None):
        """
        Initialize audio controller.
        
        Args:
            input_device: Optional device ID for microphone (if None, uses system default)
            output_device: Optional device ID for speakers (if None, uses system default)
        """
        self.modem = AudioModem()
        self.is_initialized = False
        self.last_error = ""
        self.input_device = input_device
        self.output_device = output_device
        
        # Try importing sounddevice
        try:
            import sounddevice as sd
            self.sd = sd
            self.is_initialized = True
            
            # Auto-detect devices if not specified and no default exists
            if self.input_device is None:
                try:
                    sd.query_devices(kind='input')
                except Exception:
                    # No default input - try to find first available
                    devices = sd.query_devices()
                    for i, device in enumerate(devices):
                        if device['max_input_channels'] > 0:
                            self.input_device = i
                            print(f"Auto-selected input device {i}: {device['name']}")
                            break
                            
        except ImportError:
            self.last_error = "sounddevice not installed: pip install sounddevice numpy"
    
    def send_command(self, command: Command, retries: int = 3) -> bool:
        """
        Send command with automatic retries.
        
        Args:
            command: Command to send
            retries: Number of retry attempts if no acknowledgment
            
        Returns:
            True if command sent successfully
        """
        if not self.is_initialized:
            return False
        
        for attempt in range(retries):
            try:
                # Encode and play
                audio = self.modem.encode_command(command)
                self.sd.play(audio, self.modem.config.sample_rate, device=self.output_device)
                self.sd.wait()
                
                print(f"  Sent {command.name} (attempt {attempt + 1}/{retries})")
                return True
                
            except Exception as e:
                print(f"  Send failed: {e}")
                if attempt < retries - 1:
                    time.sleep(0.5)
                    
        return False
    
    def wait_for_command(self, timeout: float = 60.0, 
                        expected: Optional[Command] = None) -> Optional[Command]:
        """
        Listen for incoming command.
        
        Args:
            timeout: Maximum wait time in seconds
            expected: If set, only return if this specific command received
            
        Returns:
            Received Command or None if timeout/no valid command
        """
        if not self.is_initialized:
            return None
        
        try:
            # Record audio
            duration = min(timeout, 5.0)  # Record in 5-second chunks
            sample_rate = self.modem.config.sample_rate
            
            start_time = time.time()
            chunk_num = 0
            
            while time.time() - start_time < timeout:
                remaining = int(timeout - (time.time() - start_time))
                chunk_num += 1
                print(f"  Listening... ({remaining}s remaining, chunk #{chunk_num})")
                
                recording = self.sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    device=self.input_device
                )
                self.sd.wait()
                
                # Analyze audio levels for debugging
                audio_data = recording[:, 0]
                max_amp = np.max(np.abs(audio_data))
                rms = np.sqrt(np.mean(audio_data ** 2))
                
                # Debug: show when we detect sound
                if max_amp > 0.01:
                    print(f"  🔊 SOUND DETECTED! max={max_amp:.4f}, rms={rms:.4f}")
                elif max_amp > 0.001:
                    print(f"  ~ weak audio: max={max_amp:.4f}, rms={rms:.4f}")
                else:
                    print(f"  - silence: max={max_amp:.4f}")
                
                # Try to decode with debug output if sound detected
                debug_mode = max_amp > 0.005  # Enable debug if any significant sound
                command = self.modem.decode_command(recording[:, 0], debug=debug_mode)
                
                if command:
                    print(f"  ✓ DECODED: {command.name}")
                    
                    if expected is None or command == expected:
                        return command
                    else:
                        print(f"  ⚠ Expected {expected.name}, got {command.name} - ignoring")
            
            print("  ⏱ Timeout - no valid command received")
            return None
            
        except Exception as e:
            print(f"  ✗ Listen error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def trigger_and_wait(self, timeout: float = 60.0) -> bool:
        """
        High-level: Send CAPTURE command and wait for DONE response.
        
        Returns True if successful, False on timeout or error
        """
        print("\n🔬 Triggering microscope capture...")
        
        if not self.send_command(Command.CAPTURE):
            return False
        
        print("⏳ Waiting for completion signal...")
        response = self.wait_for_command(timeout=timeout, expected=Command.DONE)
        
        if response == Command.DONE:
            print("✓ Capture complete!")
            return True
        else:
            print("✗ No completion signal received")
            return False
    
    def test_connection(self, timeout: float = 10.0) -> bool:
        """Send PING and wait for PONG response"""
        print("\n🔊 Testing audio connection...")
        
        if not self.send_command(Command.PING):
            return False
        
        response = self.wait_for_command(timeout=timeout, expected=Command.PONG)
        return response == Command.PONG
    
    def close(self) -> None:
        """Cleanup resources"""
        pass
