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
    
    def __init__(self):
        """
        Initialize microscope controller.
        
        Uses system default audio devices (configured in Windows Sound settings).
        If audio jack not connected, will use speakers/microphone - just like playing music.
        """
        self.is_initialized = False
        self.last_error = ""
        self.output_device = None  # None = use system default
        self.sample_rate: int = 44100
        
        # Initialize FSK modem
        self.modem = AudioModem(FSKConfig())
        
        self.is_initialized = True
        logging.info("Microscope controller initialized (using system default audio)")
    
    def acquire(self) -> bool:
        """
        Trigger image acquisition on microscope.
        
        Sends CAPTURE command via audio. Microscope will automatically click button.
        
        Returns:
            True if signal sent successfully, False on error
        """
        if not self.is_initialized:
            print(f"✗ Microscope not initialized: {self.last_error}")
            return False
        
        try:
            print("🔊 Sending CAPTURE signal to microscope...")
            
            # Send CAPTURE command
            audio = self.modem.encode_command(Command.CAPTURE)
            sd.play(audio, self.modem.config.sample_rate, device=self.output_device)
            sd.wait()
            
            print("✓ CAPTURE signal sent")
            logging.info("CAPTURE command sent to microscope")
            return True
            
        except KeyboardInterrupt:
            print("\n✗ Interrupted by user")
            raise
        except Exception as e:
            self.last_error = f"Failed to send signal: {e}"
            print(f"✗ {self.last_error}")
            logging.error(self.last_error)
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