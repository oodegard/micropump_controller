"""
Microscope controller that sends and receives audio commands for PC-to-PC communication.

This module provides a unified Microscope class that can:
- Send RUN commands via audio (commander mode) for run_protocol_cli.py
- Receive commands via audio (listener mode) for microscope_gui_control.py

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
COMMAND_TONES = {
    'RUN': (697, 1209),
    'RUN_COMMAND_RECEIVED': (770, 1336),
    'RUN_DONE': (852, 1477),
}

# Detection thresholds
DETECTION_THRESHOLD = 0.05
FREQUENCY_TOLERANCE = 100


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


class Microscope:
    """
    Microscope controller supporting both commander and listener modes.
    
    Commander mode: Send RUN commands via audio (for run_protocol_cli.py)
    Listener mode: Receive commands via audio (for microscope_gui_control.py)
    """
    
    def __init__(self, config: AudioConfig = None):
        """Initialize the microscope controller."""
        self.is_initialized = False
        self.last_error = ""
        self.config = config or AudioConfig.auto_detect()
        self._listener_callback = None
        self._is_listening = False
        self._listen_thread = None
        
        try:
            self.is_initialized = True
        except Exception as e:
            self.last_error = f"Failed to initialize Microscope: {e}"
    
    # ==================== Commander Mode Methods ====================
    
    def _generate_tone(self, freq1: float, freq2: float, duration: float) -> np.ndarray:
        """Generate a dual-tone signal."""
        t = np.linspace(0, duration, int(self.config.sample_rate * duration))
        tone1 = np.sin(2 * np.pi * freq1 * t)
        tone2 = np.sin(2 * np.pi * freq2 * t)
        combined = (tone1 + tone2) * AMPLITUDE / 2
        
        # Apply envelope to reduce clicking
        envelope = np.ones_like(combined)
        fade_samples = int(0.01 * self.config.sample_rate)
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
    
    def run(self) -> bool:
        """
        Send RUN command via audio to trigger microscope acquisition.
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        if not self.is_initialized:
            print(f"[MICROSCOPE ERROR] Not initialized: {self.last_error}")
            return False
        
        try:
            print("[MICROSCOPE] Sending RUN command via audio...")
            success = self.send_command('RUN')
            if success:
                print("[MICROSCOPE] ✓ RUN command sent successfully")
            else:
                print("[MICROSCOPE] ✗ Failed to send RUN command")
            return success
        except Exception as e:
            print(f"[MICROSCOPE ERROR] Exception during command send: {e}")
            return False
    
    def acquire(self) -> bool:
        """Alias for run() - trigger microscope image acquisition."""
        return self.run()
    
    # ==================== Listener Mode Methods ====================
    
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
            top_peaks = sorted(zip(detected_freqs, detected_mags), 
                             key=lambda x: x[1], reverse=True)[:8]
            freq_str = ", ".join([f"{freq:.1f}Hz ({mag:.3f})" for freq, mag in top_peaks])
            print(f"Detected frequencies: {freq_str}")
        
        # Match against known command tones with scoring
        best_match = None
        best_score = 0
        
        for command, (freq1, freq2) in COMMAND_TONES.items():
            matches1 = [(f, m) for f, m in zip(detected_freqs, detected_mags) 
                       if abs(f - freq1) < FREQUENCY_TOLERANCE]
            matches2 = [(f, m) for f, m in zip(detected_freqs, detected_mags) 
                       if abs(f - freq2) < FREQUENCY_TOLERANCE]
            
            if matches1 and matches2:
                score = max(m for f, m in matches1) + max(m for f, m in matches2)
                best_f1 = min(matches1, key=lambda x: abs(x[0] - freq1))
                best_f2 = min(matches2, key=lambda x: abs(x[0] - freq2))
                freq_error = abs(best_f1[0] - freq1) + abs(best_f2[0] - freq2)
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
        if command and self._listener_callback:
            self._listener_callback(command)
    
    def start_listening(self, callback: Callable[[str], None]):
        """
        Start listening for commands in background thread.
        
        Args:
            callback: Function to call when a command is received
        """
        if self._is_listening:
            print("Already listening")
            return
        
        self._listener_callback = callback
        self._is_listening = True
        
        def listen_loop():
            blocksize = int(TONE_DURATION * self.config.sample_rate)
            try:
                with sd.InputStream(callback=self._audio_callback,
                                  device=self.config.input_device,
                                  channels=1,
                                  samplerate=self.config.sample_rate,
                                  blocksize=blocksize):
                    print("Listening for commands... Press Ctrl+C to stop")
                    while self._is_listening:
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error in listen loop: {e}")
                self._is_listening = False
        
        self._listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self._listen_thread.start()
    
    def stop_listening(self):
        """Stop listening for commands."""
        self._is_listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
    
    # ==================== Utility Methods ====================
    
    @staticmethod
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
    
    def close(self):
        """Clean up resources."""
        self.stop_listening()
    
    def get_error_details(self) -> str:
        """Return detailed error message if initialization failed."""
        return self.last_error
    
    def get_suggested_fix(self) -> str:
        """Return suggested troubleshooting steps."""
        if not self.is_initialized:
            return (
                "Check that audio devices are properly configured in Windows Sound settings. "
                "For listener mode, verify the other PC is sending commands. "
                "For commander mode, verify the other PC is running microscope_gui_control.py."
            )
        return ""
