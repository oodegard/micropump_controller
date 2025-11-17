"""
Test script for Microscope class with integrated handshake

Run this on the SENDER PC (microfluidics controller)
"""

from src.microscope import Microscope

def main():
    print("=" * 70)
    print("MICROSCOPE HANDSHAKE TEST - SENDER")
    print("=" * 70)
    print("\nThis will:")
    print("1. Auto-detect audio devices")
    print("2. Establish handshake with receiver (microscope PC)")
    print("3. Wait for you to test sending a command")
    print()
    
    # Initialize microscope (auto handshake enabled by default)
    microscope = Microscope()
    
    if not microscope.is_initialized:
        print(f"\n✗ Failed to initialize: {microscope.last_error}")
        return
    
    if not microscope.is_connected:
        print("\n✗ Handshake failed - receiver not responding")
        return
    
    print("\n" + "=" * 70)
    print("✓ HANDSHAKE SUCCESSFUL!")
    print("=" * 70)
    print("\nMicroscope is ready for commands.")
    print("\nNext steps:")
    print("  - Test with: microscope.acquire()")
    print("  - Or integrate into your experiment workflow")
    print()
    
    # Optional: test acquire
    test = input("Test CAPTURE/DONE cycle? (y/n): ").strip().lower()
    if test == 'y':
        print("\nSending CAPTURE command...")
        if microscope.acquire():
            print("\n✓ Acquisition cycle complete!")
        else:
            print("\n✗ Acquisition failed")
    
    microscope.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
