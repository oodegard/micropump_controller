"""
Debug Listener - Continuously listen and show what frequencies are detected

This will help diagnose if the signal from the other computer is being received.
"""

import numpy as np
import sounddevice as sd
import time


def analyze_audio(audio: np.ndarray, sample_rate: int = 44100) -> None:
    """Analyze audio and display all detected frequencies"""
    
    # Calculate basic stats
    rms = np.sqrt(np.mean(audio ** 2))
    max_amp = np.max(np.abs(audio))
    
    # FFT analysis
    fft = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sample_rate)
    magnitude = np.abs(fft)
    
    # Find ALL significant peaks
    threshold = 10.0  # Very low threshold to see everything
    significant_indices = np.where(magnitude > threshold)[0]
    
    # Sort by magnitude
    sorted_indices = significant_indices[np.argsort(magnitude[significant_indices])[::-1]]
    
    # Print results
    print(f"RMS: {rms:.6f}  |  Max: {max_amp:.6f}")
    
    if len(sorted_indices) > 0:
        print("Detected frequencies (magnitude > 10):")
        for i, idx in enumerate(sorted_indices[:15]):  # Top 15 frequencies
            freq = freqs[idx]
            mag = magnitude[idx]
            
            # Highlight target frequencies
            marker = ""
            if 950 <= freq <= 1050:
                marker = "  ← 1000 Hz TARGET!"
            elif 1150 <= freq <= 1250:
                marker = "  ← 1200 Hz (sender confirm)"
            elif 1050 <= freq <= 1150:
                marker = "  ← 1100 Hz (receiver confirm)"
            
            print(f"  {i+1}. {freq:7.1f} Hz  (magnitude: {mag:8.0f}){marker}")
    else:
        print("  No significant frequencies detected (very quiet)")
    
    print()


def main() -> None:
    """Continuously listen and analyze"""
    print("=" * 70)
    print("DEBUG LISTENER - Continuous Audio Analysis")
    print("=" * 70)
    print("\nThis will show ALL frequencies detected, including background noise.")
    print("Looking for 1000 Hz signal from the other computer.\n")
    
    # Auto-detect input device
    try:
        default_id = sd.default.device[0]
        default_device = sd.query_devices(default_id)
        print(f"Using microphone: {default_device['name']}")
    except:
        default_id = None
        print("Using default microphone")
    
    print("\nListening... (Press Ctrl+C to stop)\n")
    print("=" * 70)
    
    sample_rate = 44100
    chunk_duration = 2.0  # 2 second chunks for better frequency resolution
    
    chunk_num = 0
    
    try:
        while True:
            chunk_num += 1
            print(f"\n[Chunk {chunk_num}] Recording {chunk_duration}s...")
            
            # Record
            recording = sd.rec(
                int(chunk_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=default_id,
                dtype='float32'
            )
            sd.wait()
            
            # Analyze
            audio = recording[:, 0]
            analyze_audio(audio, sample_rate)
            
            time.sleep(0.5)  # Brief pause between recordings
            
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("STOPPED")
        print("=" * 70)
        print("\nIf you saw 1000 Hz in the list, the signal is being received!")
        print("If not, try:")
        print("  - Increase volume on the other computer")
        print("  - Move speaker closer to microphone")
        print("  - Check microphone is not muted")


if __name__ == "__main__":
    main()
