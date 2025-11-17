"""
Bidirectional audio communication system for PC-to-PC control.

This module sends and receives simple commands via audio (microphone/speaker jack):
- RUN: Initiates a command on the receiving PC
- RUN_COMMAND_RECEIVED: Acknowledges receipt of RUN command
- RUN_DONE: Signals completion of the command

The system uses DTMF-like tone sequences for reliable communication over audio cables.
"""

import numpy as np
import sounddevice as sd
from scipy import signal
from typing import Optional, Callable
import time
import threading
from dataclasses import dataclass

# Audio parameters
SAMPLE_RATE = 44100  # Hz
TONE_DURATION = 0.15  # seconds per tone
SILENCE_DURATION = 0.05  # seconds between tones
AMPLITUDE = 0.5  # Volume level (0.0 to 1.0)

# Command encoding using dual-tone frequencies (Hz)
# Each command uses a unique pair of frequencies
COMMAND_TONES = {
    'RUN': (697, 1209),  # Low + Mid
    'RUN_COMMAND_RECEIVED': (770, 1336),  # Mid-Low + Mid
    'RUN_DONE': (852, 1477),  # Mid + High
}

# Detection thresholds
DETECTION_THRESHOLD = 0.05  # Minimum signal strength to consider (lowered for better sensitivity)
FREQUENCY_TOLERANCE = 100  # Hz tolerance for frequency matching (increased for cable transmission)


@dataclass
class AudioConfig:
    """Configuration for audio input/output devices."""
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    sample_rate: int = SAMPLE_RATE
    
    @classmethod
    def auto_detect(cls) -> 'AudioConfig':
        """Auto-detect default audio devices."""
        return cls()


class AudioCommander:
    """Handles sending commands via audio output."""
    
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig.auto_detect()
        
    def _generate_tone(self, freq1: float, freq2: float, duration: float) -> np.ndarray:
        """Generate a dual-tone signal."""
        t = np.linspace(0, duration, int(self.config.sample_rate * duration))
        tone1 = np.sin(2 * np.pi * freq1 * t)
        tone2 = np.sin(2 * np.pi * freq2 * t)
        combined = (tone1 + tone2) * AMPLITUDE / 2
        
        # Apply envelope to reduce clicking
        envelope = np.ones_like(combined)
        fade_samples = int(0.01 * self.config.sample_rate)  # 10ms fade
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        
        return combined * envelope
    
    def send_command(self, command: str) -> bool:
        """Send a command via audio output."""
        if command not in COMMAND_TONES:
            print(f"Unknown command: {command}")
            return False
        
        freq1, freq2 = COMMAND_TONES[command]
        
        # Generate tone sequence (send 3 times for reliability)
        tones = []
        for _ in range(3):
            tones.append(self._generate_tone(freq1, freq2, TONE_DURATION))
            tones.append(np.zeros(int(self.config.sample_rate * SILENCE_DURATION)))
        
        audio_signal = np.concatenate(tones)
        
        try:
            print(f"Sending command: {command} ({freq1}Hz + {freq2}Hz)")
            sd.play(audio_signal, samplerate=self.config.sample_rate, 
                   device=self.config.output_device)
            sd.wait()
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False


class AudioListener:
    """Handles receiving commands via audio input."""
    
    def __init__(self, config: AudioConfig = None, callback: Optional[Callable[[str], None]] = None):
        self.config = config or AudioConfig.auto_detect()
        self.callback = callback
        self.is_listening = False
        self._listen_thread = None
        
    def _detect_tones(self, audio_data: np.ndarray) -> Optional[str]:
        """Detect which command tones are present in audio data."""
        # Compute FFT
        fft = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.config.sample_rate)
        magnitude = np.abs(fft) / len(audio_data)
        
        # Find peaks above threshold
        peaks_idx = signal.find_peaks(magnitude, height=DETECTION_THRESHOLD)[0]
        detected_freqs = freqs[peaks_idx]
        detected_mags = magnitude[peaks_idx]
        
        # Print detected frequencies if any significant signal present
        if len(detected_freqs) > 0:
            # Get top frequencies by magnitude
            top_peaks = sorted(zip(detected_freqs, detected_mags), 
                             key=lambda x: x[1], reverse=True)[:8]
            freq_str = ", ".join([f"{freq:.1f}Hz ({mag:.3f})" for freq, mag in top_peaks])
            print(f"Detected frequencies: {freq_str}")
        
        # Match against known command tones with scoring
        best_match = None
        best_score = 0
        
        for command, (freq1, freq2) in COMMAND_TONES.items():
            # Find closest matches to target frequencies
            matches1 = [(f, m) for f, m in zip(detected_freqs, detected_mags) 
                       if abs(f - freq1) < FREQUENCY_TOLERANCE]
            matches2 = [(f, m) for f, m in zip(detected_freqs, detected_mags) 
                       if abs(f - freq2) < FREQUENCY_TOLERANCE]
            
            if matches1 and matches2:
                # Score based on magnitude of detected frequencies
                score = max(m for f, m in matches1) + max(m for f, m in matches2)
                
                # Also consider frequency accuracy
                best_f1 = min(matches1, key=lambda x: abs(x[0] - freq1))
                best_f2 = min(matches2, key=lambda x: abs(x[0] - freq2))
                freq_error = abs(best_f1[0] - freq1) + abs(best_f2[0] - freq2)
                
                # Penalize large frequency errors
                score = score * (1 - freq_error / 400)
                
                if score > best_score:
                    best_score = score
                    best_match = command
                    print(f"  -> Matches {command}: {best_f1[0]:.1f}Hz≈{freq1}Hz, {best_f2[0]:.1f}Hz≈{freq2}Hz (score: {score:.3f})")
        
        return best_match
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process incoming audio data."""
        if status:
            print(f"Audio status: {status}")
        
        # Convert to mono if stereo
        if len(indata.shape) > 1:
            audio_mono = indata.mean(axis=1)
        else:
            audio_mono = indata.flatten()
        
        # Detect command
        command = self._detect_tones(audio_mono)
        if command and self.callback:
            self.callback(command)
    
    def start_listening(self):
        """Start listening for commands in background thread."""
        if self.is_listening:
            print("Already listening")
            return
        
        self.is_listening = True
        
        def listen_loop():
            blocksize = int(TONE_DURATION * self.config.sample_rate)
            try:
                with sd.InputStream(callback=self._audio_callback,
                                  device=self.config.input_device,
                                  channels=1,
                                  samplerate=self.config.sample_rate,
                                  blocksize=blocksize):
                    print("Listening for commands... Press Ctrl+C to stop")
                    while self.is_listening:
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error in listen loop: {e}")
                self.is_listening = False
        
        self._listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self._listen_thread.start()
    
    def stop_listening(self):
        """Stop listening for commands."""
        self.is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)


def list_audio_devices():
    """List available audio input and output devices."""
    print("\n=== Available Audio Devices ===")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        device_type = []
        if device['max_input_channels'] > 0:
            device_type.append("INPUT")
        if device['max_output_channels'] > 0:
            device_type.append("OUTPUT")
        print(f"{i}: {device['name']} ({', '.join(device_type)})")
    print()


# Example usage functions
def command_received_handler(command: str):
    """
    Example callback for received commands.
    NOTE: For production use, implement your handler in listen.py instead.
    """
    print(f">>> RECEIVED: {command}")


if __name__ == "__main__":
    print("Audio Communication System")
    print("=" * 50)
    list_audio_devices()
    
    print("\nTest Mode: This will send all three commands in sequence")
    print("Make sure the other PC is running in listen mode!\n")
    
    commander = AudioCommander()
    
    time.sleep(1)
    commander.send_command('RUN')
    time.sleep(1)
    commander.send_command('RUN_COMMAND_RECEIVED')
    time.sleep(1)
    commander.send_command('RUN_DONE')
    
    print("\nCommands sent! Check the receiving PC.")
