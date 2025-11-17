"""
Microscope Listener - Bidirectional audio communication for microscope control

This runs on the MICROSCOPE PC (airgapped computer).
1. Establishes handshake with sender (responds to calling tone)
2. Listens for CAPTURE command via FSK audio modem
3. Clicks the "Acquire" button at specified position
4. Monitors button state (waits for grey, then normal again)
5. Sends DONE command back when acquisition completes

Usage:
    python microscope_listener.py --button-x 100 --button-y 200
"""

import sounddevice as sd
import numpy as np
import pyautogui
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple
from PIL import ImageGrab

# Add test_audio_comunication to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "test_audio_comunication"))
from audio_config import load_audio_config, save_audio_config
from audio_protocol import AudioModem, Command, FSKConfig

# Screen click configuration (will be set from command line args or use default)
BUTTON_IMAGE_PATH = None  # Path to button image for recognition
DEFAULT_BUTTON_IMAGE = "run.png"  # Default image in project root

# Handshake frequencies (matching Microscope class)
CALLING_TONE = 900   # Sender sends this
ANSWER_TONE = 1100   # Receiver (this PC) responds with this

# Detection parameters
DETECTION_THRESHOLD = 15.0
BACKGROUND_NOISE = 0.0
SIGNAL_HISTORY = []


def get_default_audio_devices() -> Tuple[None, None]:
    """
    Just use system default audio devices.
    User controls routing via Windows Sound settings.
    
    Returns:
        (None, None) to indicate use system defaults
    """
    print("=" * 70)
    print("MICROSCOPE LISTENER - Using System Default Audio")
    print("=" * 70)
    print("\n✓ Using Windows default audio devices")
    print("  Configure audio routing in Windows Sound settings")
    print("  (Just like playing music - uses speakers if jack not connected)\n")
    return None, None


def find_button_on_screen(image_path: str, confidence: float = 0.99) -> Optional[Tuple[int, int]]:
    """
    Find the Acquire button on screen using image recognition.
    
    Args:
        image_path: Path to button image file
        confidence: Match confidence (0.0 to 1.0)
    
    Returns:
        (x, y) center coordinates of button, or None if not found
    """
    print(f"\n🔍 Looking for button using image: {image_path} (confidence >= {confidence})")
    
    try:
        # Try to find all matches to show similarity scores
        try:
            all_locations = list(pyautogui.locateAllOnScreen(image_path, confidence=0.1))
            if all_locations:
                print(f"  ℹ Found {len(all_locations)} potential matches (confidence >= 0.1)")
        except Exception:
            pass
        
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if location:
            # Get center of matched region
            center_x = location.left + location.width // 2
            center_y = location.top + location.height // 2
            print(f"✓ Button found at ({center_x}, {center_y})")
            return (center_x, center_y)
        else:
            print(f"✗ Button image not found on screen with confidence >= {confidence}")
            print(f"  ℹ Try lowering confidence value if needed")
            return None
    except Exception as e:
        print(f"✗ Error finding button: {e}")
        return None


def is_button_visible(image_path: str, confidence: float = 0.99) -> bool:
    """
    Check if button is visible on screen (acquisition complete).
    
    Args:
        image_path: Path to button image file
        confidence: Match confidence (0.0 to 1.0)
    
    Returns:
        True if button is found on screen (acquisition complete)
    """
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        return location is not None
    except Exception:
        return False


def wait_for_acquisition_complete(image_path: str, max_wait: float = 600.0, 
                                   confidence: float = 0.99) -> bool:
    """
    Monitor button visibility until acquisition completes.
    
    Wait 1 second, then check if button disappeared (acquisition running).
    Then wait for it to reappear (acquisition done).
    
    Args:
        image_path: Path to button image file
        max_wait: Maximum time to wait in seconds
        confidence: Match confidence (0.0 to 1.0)
    
    Returns:
        True if acquisition completed, False on timeout
    """
    print("  Waiting 1 second before monitoring...")
    time.sleep(1.0)
    
    # Check if button disappeared (acquisition started)
    print(f"  Checking if acquisition started (confidence >= {confidence})...")
    if is_button_visible(image_path, confidence):
        print("  ⚠ Button still visible - acquisition may not have started")
        print("     (This could mean processing is instant or button doesn't change)")
    else:
        print("  ✓ Button disappeared (acquisition running)")
    
    # Now wait for it to reappear
    print(f"  Monitoring button visibility (max {max_wait}s)...")
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < max_wait:
        check_count += 1
        elapsed = time.time() - start_time
        
        if is_button_visible(image_path, confidence):
            print(f"  ✓ Button reappeared after {elapsed:.1f}s ({check_count} checks)")
            return True
        
        # Progress updates every 10 checks
        if check_count % 10 == 0:
            print(f"  ... still waiting ({elapsed:.0f}s elapsed, check #{check_count})")
        
        time.sleep(2.0)
    
    print(f"  ✗ Timeout after {max_wait}s ({check_count} checks)")
    return False


def send_done_signal(output_device: Optional[int], modem: AudioModem) -> bool:
    """
    Send DONE command back to controller.
    
    Args:
        output_device: Audio output device ID (None = system default)
        modem: AudioModem instance
    
    Returns:
        True if sent successfully
    """
    try:
        print("\n🔊 Sending DONE command...")
        audio = modem.encode_command(Command.DONE)
        sd.play(audio, modem.config.sample_rate, device=output_device)
        sd.wait()
        print("✓ DONE command sent")
        return True
    except Exception as e:
        print(f"✗ Failed to send DONE: {e}")
        return False


def detect_frequency(audio: np.ndarray, target_freq: float, sample_rate: int = 44100,
                    tolerance: float = 50.0) -> Tuple[bool, float]:
    """
    Detect if a specific frequency is present in audio.
    
    Returns: (detected, peak_magnitude)
    """
    global BACKGROUND_NOISE, SIGNAL_HISTORY
    
    if len(audio) == 0 or np.all(audio == 0):
        return False, 0.0
    
    try:
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), 1 / sample_rate)
        magnitude = np.abs(fft)
        
        freq_mask = (freqs >= target_freq - tolerance) & (freqs <= target_freq + tolerance)
        if not np.any(freq_mask):
            return False, 0.0
        
        peak_mag = float(np.max(magnitude[freq_mask]))
        
        if np.isnan(peak_mag) or np.isinf(peak_mag):
            return False, 0.0
        
        # Background noise
        noise_mask = ~freq_mask
        if np.any(noise_mask):
            background = float(np.median(magnitude[noise_mask]))
            BACKGROUND_NOISE = 0.9 * BACKGROUND_NOISE + 0.1 * background
        
        adaptive_threshold = min(DETECTION_THRESHOLD, max(10.0, 1.5 * BACKGROUND_NOISE))
        snr = peak_mag / (BACKGROUND_NOISE + 1e-6)
        detected = (peak_mag > adaptive_threshold) and (snr > 1.2)
        
        SIGNAL_HISTORY.append({
            'peak': peak_mag,
            'threshold': adaptive_threshold,
            'snr': snr,
            'detected': detected
        })
        if len(SIGNAL_HISTORY) > 10:
            SIGNAL_HISTORY.pop(0)
        
        return detected, peak_mag
        
    except Exception:
        return False, 0.0


def listen_for_tone(target_freq: float, input_device: int, sample_rate: int = 44100,
                   duration: float = 1.5) -> bool:
    """
    Listen for a specific frequency.
    Returns True if detected, False otherwise.
    """
    try:
        actual_duration = max(duration, 1.5)
        
        recording = sd.rec(
            int(actual_duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=input_device,
            dtype='float32'
        )
        sd.wait()
        
        audio = recording[:, 0]
        
        if len(audio) == 0:
            return False
        
        detected, magnitude = detect_frequency(audio, target_freq, sample_rate)
        return detected
        
    except Exception:
        return False


def establish_handshake_receiver(input_device: int, output_device: int, 
                                sample_rate: int = 44100) -> bool:
    """
    Receiver (answering) side of handshake:
    1. Listen for 900 Hz calling tone from sender (need 3 consecutive)
    2. Once confirmed, respond with continuous 1100 Hz answer tone
    3. Keep sending until sender confirms (by stopping calling tone)
    
    Returns:
        True if handshake successful, False otherwise
    """
    global SIGNAL_HISTORY
    
    print("\n" + "=" * 70)
    print("ESTABLISHING CONNECTION - RECEIVER MODE")
    print("=" * 70)
    print("\nListening for 900 Hz calling tone from sender...")
    print("(Press Ctrl+C to cancel)\n")
    
    # Phase 1: Confirm calling tone
    consecutive_calling = 0
    required_calling_detections = 3
    
    try:
        print("- listening for calling tone...")
        
        while consecutive_calling < required_calling_detections:
            detected = listen_for_tone(CALLING_TONE, input_device, sample_rate, duration=1.5)
            
            if detected:
                consecutive_calling += 1
                print(f"✓ Calling tone detected! ({consecutive_calling}/{required_calling_detections})")
            else:
                if consecutive_calling > 0:
                    print(f"Lost calling tone, resetting ({consecutive_calling} -> 0)")
                consecutive_calling = 0
                
            time.sleep(0.3)
        
        print("\n✓ Calling tone confirmed! Starting answer phase...")
        
        # Phase 2: Respond with answer tone continuously
        print("Sending 1100 Hz answer tone continuously...")
        
        # Create answer tone
        tone_duration = 0.5
        t = np.linspace(0, tone_duration, int(sample_rate * tone_duration))
        answer_signal = 0.4 * np.sin(2 * np.pi * ANSWER_TONE * t)
        
        # Add fade
        fade_len = int(0.02 * sample_rate)
        answer_signal[:fade_len] *= np.linspace(0, 1, fade_len)
        answer_signal[-fade_len:] *= np.linspace(1, 0, fade_len)
        
        # Keep sending and checking if sender stopped
        iteration = 0
        no_calling_count = 0
        
        while True:
            iteration += 1
            
            # Send answer tone
            sd.play(answer_signal, sample_rate, device=output_device, blocking=True)
            time.sleep(0.2)
            
            # Check if sender stopped calling
            print(f"[{iteration}] Sending answer, checking for calling tone...", end=' ', flush=True)
            still_calling = listen_for_tone(CALLING_TONE, input_device, sample_rate, duration=1.0)
            
            if not still_calling:
                no_calling_count += 1
                print(f"no calling tone (sender may have confirmed) [{no_calling_count}/3]")
                
                if no_calling_count >= 3:
                    sd.stop()
                    print("\n🎉 CONNECTION ESTABLISHED!")
                    print("(Sender stopped calling tone - they detected our answer)")
                    return True
            else:
                print("✓ still hearing calling tone (sender waiting for our answer)")
                no_calling_count = 0
        
    except KeyboardInterrupt:
        sd.stop()
        print("\n✗ Connection cancelled by user")
        return False
    except Exception as e:
        sd.stop()
        print(f"\n✗ Handshake error: {e}")
        return False


def listen_and_respond(input_device: Optional[int], output_device: Optional[int], image_path: str, confidence: float = 0.99) -> None:
    """
    Main listening loop - waits for CAPTURE, clicks button, monitors, sends DONE.
    
    Args:
        input_device: Audio input device ID (None = system default)
        output_device: Audio output device ID (None = system default)
        image_path: Path to button image for recognition
        confidence: Button image matching confidence (0.0 to 1.0)
    """
    # Verify button image exists
    if not Path(image_path).exists():
        print(f"\n✗ ERROR: Button image not found: {image_path}")
        print("Please provide a valid image file of the Acquire button.")
        return
    
    print(f"\nUsing button image: {image_path}")
    print(f"Image matching confidence: {confidence}")
    
    # Initialize modem
    modem = AudioModem(FSKConfig())
    sample_rate = modem.config.sample_rate
    
    print("\n" + "=" * 70)
    print("🎧 LISTENING FOR CAPTURE COMMAND")
    print("=" * 70)
    print(f"\nListening on device {input_device}")
    print(f"Will send DONE on device {output_device}")
    print(f"Button image: {image_path}")
    print(f"Confidence threshold: {confidence}")
    print("\nPress Ctrl+C to stop\n")
    
    chunk_duration = 5.0  # Record in 5-second chunks
    chunk_count = 0
    
    try:
        while True:
            chunk_count += 1
            timestamp = time.strftime("%H:%M:%S")
            
            print(f"[{timestamp}] Listening for CAPTURE... (chunk #{chunk_count})")
            
            # Record audio chunk
            recording = sd.rec(
                int(chunk_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=input_device,
                dtype='float32'
            )
            sd.wait()
            
            # Check audio levels
            audio_data = recording[:, 0]
            max_amp = np.max(np.abs(audio_data))
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            debug_mode = False
            if max_amp > 0.01:
                print(f"  🔊 Sound detected! max={max_amp:.4f}, rms={rms:.4f}")
                debug_mode = True
            elif max_amp > 0.001:
                print(f"  ~ Weak audio: max={max_amp:.4f}")
            
            # Try to decode
            command = modem.decode_command(audio_data, debug=debug_mode)
            
            if command == Command.PING:
                print("  ✓ PING received - sending PONG...")
                # Respond with PONG
                pong_audio = modem.encode_command(Command.PONG)
                sd.play(pong_audio, modem.config.sample_rate, device=output_device)
                sd.wait()
                print("  ✓ PONG sent\n")
                
            elif command == Command.CAPTURE:
                print("  ✓ CAPTURE command received!")
                
                # Find and click Acquire button
                print("  🖱️  Finding and clicking Acquire button...")
                button_pos = find_button_on_screen(image_path, confidence=confidence)
                if not button_pos:
                    print("  ✗ Could not find button on screen!")
                    print("  ℹ Try lowering confidence if button exists but not detected")
                    continue
                
                pyautogui.click(button_pos[0], button_pos[1])
                print("  ✓ Button clicked")
                
                # Wait for acquisition to complete
                print("  ⏳ Monitoring acquisition...")
                if wait_for_acquisition_complete(image_path, confidence=confidence):
                    print("  ✓ Acquisition complete!")
                    
                    # Send DONE signal
                    send_done_signal(output_device, modem)
                    
                    print("\n✅ Cycle complete - ready for next trigger\n")
                else:
                    print("  ✗ Acquisition monitoring failed")
                    print("\n⚠ Ready for next trigger (despite error)\n")
                
            elif command is not None:
                print(f"  ⚠ Unexpected command: {command.name} (ignoring)")
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Stopped listening")
        print("=" * 70)


def main() -> None:
    """Main entry point"""
    global BUTTON_IMAGE_PATH
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Microscope Listener - Responds to audio commands and clicks Acquire button'
    )
    parser.add_argument('--button-image', type=str, 
                       help=f'Path to button image file (default: {DEFAULT_BUTTON_IMAGE})')
    parser.add_argument('--confidence', type=float, default=0.99,
                       help='Image matching confidence threshold 0.0-1.0 (default: 0.99)')
    args = parser.parse_args()
    
    # Set button image path
    if args.button_image:
        BUTTON_IMAGE_PATH = args.button_image
    else:
        BUTTON_IMAGE_PATH = DEFAULT_BUTTON_IMAGE
    
    print(f"Button image: {BUTTON_IMAGE_PATH}")
    print(f"Confidence threshold: {args.confidence}")
    
    print("\n")
    print("=" * 70)
    print("MICROSCOPE LISTENER - SIMPLE FSK MODE")
    print("Listens for PING (responds with PONG), CAPTURE, sends DONE")
    print("=" * 70)
    
    # Get default audio devices (None = system default)
    input_device, output_device = get_default_audio_devices()
    
    # No separate handshake - just listen and respond to PING/CAPTURE
    print("✓ Ready to receive commands (PING or CAPTURE)\n")
    
    # Start listening for commands
    listen_and_respond(input_device, output_device, BUTTON_IMAGE_PATH)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
