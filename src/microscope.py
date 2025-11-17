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
    
    def __init__(self, auto_handshake: bool = True):
        """
        Initialize microscope controller.
        
        Uses system default audio devices (configured in Windows Sound settings).
        If audio jack not connected, will use speakers/microphone - just like playing music.
        
        Args:
            auto_handshake: If True, automatically perform handshake during initialization.
                          Note: Handshake uses PING/PONG commands.
        """
        self.is_initialized = False
        self.is_connected = False
        self.last_error = ""
        self.output_device = None  # None = use system default
        self.input_device = None   # None = use system default
        self.sample_rate: int = 44100
        
        # Initialize FSK modem
        self.modem = AudioModem(FSKConfig())
        
        self.is_initialized = True
        logging.info("Microscope controller initialized (using system default audio devices)")
        
        # Perform handshake if requested (using PING/PONG)
        if auto_handshake:
            print("\nEstablishing connection with microscope using PING/PONG...")
            if not self.establish_handshake():
                self.last_error = "Handshake failed - no PONG received"
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
        
        # Establish handshake if not already connected (using PING/PONG)
        if not self.is_connected:
            print("📡 Establishing connection with microscope (PING/PONG)...")
            try:
                if not self.establish_handshake():
                    print("✗ Failed to establish connection - no PONG received")
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
    
    def establish_handshake(self) -> bool:
        """
        Simple handshake using FSK modem PING/PONG commands.
        Much simpler than frequency detection - just send PING, wait for PONG.
        
        Returns:
            True if PONG received, False otherwise
        """
        print("\n" + "=" * 70)
        print("ESTABLISHING CONNECTION - PING/PONG")
        print("=" * 70)
        print("\nSending PING command...")
        print("Waiting for PONG response...")
        print("(Press Ctrl+C to cancel)\n")
        
        max_attempts = 3
        
        try:
            for attempt in range(1, max_attempts + 1):
                print(f"[Attempt {attempt}/{max_attempts}] Sending PING...")
                
                # Send PING command
                audio = self.modem.encode_command(Command.PING)
                sd.play(audio, self.modem.config.sample_rate, device=self.output_device)
                sd.wait()
                
                print("  ✓ PING sent, listening for PONG...")
                
                # Listen for PONG (5 second timeout per attempt)
                chunk_duration = 5.0
                recording = sd.rec(
                    int(chunk_duration * self.modem.config.sample_rate),
                    samplerate=self.modem.config.sample_rate,
                    channels=1,
                    device=self.input_device,
                    dtype='float32'
                )
                sd.wait()
                
                # Check for PONG
                audio_data = recording[:, 0]
                command = self.modem.decode_command(audio_data, debug=False)
                
                if command == Command.PONG:
                    print("  ✓ PONG received!")
                    print("\n🎉 CONNECTION ESTABLISHED!")
                    self.is_connected = True
                    return True
                else:
                    if command:
                        print(f"  ⚠ Received {command.name} instead of PONG")
                    else:
                        print("  ✗ No PONG received")
                
                if attempt < max_attempts:
                    print("  Waiting 1 second before retry...")
                    time.sleep(1.0)
            
            print(f"\n✗ No PONG received after {max_attempts} attempts")
            return False
                    
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