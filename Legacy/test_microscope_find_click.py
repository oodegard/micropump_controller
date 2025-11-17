"""
Quick test to check microscope find_and_click functionality.
Tests both the Python client and C# server communication.
"""

from src.microscope import Microscope
import time

def main():
    print("=" * 60)
    print("Testing Microscope Template Matching")
    print("=" * 60)
    
    # Initialize microscope controller
    print("\n[1] Initializing microscope controller...")
    microscope = Microscope()
    
    if not microscope.initialize():
        print(f"✗ Initialization failed: {microscope.get_error_details()}")
        print(f"  Suggested fix: {microscope.get_suggested_fix()}")
        return 1
    
    print("✓ Microscope controller initialized")
    print(f"  Shared folder: {microscope.shared_folder}")
    
    # Test 1: Take a screenshot first
    print("\n[2] Testing screenshot capability...")
    if microscope.take_screenshot():
        print("✓ Screenshot saved successfully")
        print(f"  Check: {microscope.shared_folder / 'screenshot.jpg'}")
    else:
        print(f"✗ Screenshot failed: {microscope.get_error_details()}")
    
    time.sleep(1)
    
    # Test 2: Try template matching with Run1_start
    print("\n[3] Testing template matching with 'Run1_start'...")
    print("  (This will fail if buttons/Run1_start.png doesn't exist)")
    
    success = microscope.run(image_path="Run1_start")
    
    if success:
        print("✓ Template matching succeeded!")
        print("  Button was found and clicked")
    else:
        error = microscope.get_error_details()
        print(f"✗ Template matching failed: {error}")
        
        if "not found" in error.lower() or "match failed" in error.lower():
            print("\n  This is expected if you haven't created button screenshots yet.")
            print("  To create button screenshots:")
            print("    1. Open microscope software on Windows 7 PC")
            print("    2. Use Snipping Tool to capture the Run button")
            print("    3. Save as: C:\\RemoteDesktop\\buttons\\Run1_start.png")
            print("    4. Make sure the C# server can see it")
    
    time.sleep(1)
    
    # Test 3: Fallback to coordinate clicking
    print("\n[4] Testing coordinate-based clicking (fallback)...")
    print("  Clicking at (450, 120) - update these coordinates for your setup")
    
    success = microscope.click(x=450, y=120)
    
    if success:
        print("✓ Coordinate click succeeded!")
    else:
        print(f"✗ Coordinate click failed: {microscope.get_error_details()}")
    
    # Test 4: Try with dict format (like YAML uses for coordinates)
    print("\n[5] Testing dict-format coordinate click...")
    success = microscope.run(image_path={"action": "click", "x": 20, "y": 1060})
    
    if success:
        print("✓ Dict-format click succeeded!")
    else:
        print(f"✗ Dict-format click failed: {microscope.get_error_details()}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print("Next steps:")
    print("  1. Create button screenshots in buttons/ folder")
    print("  2. Test template matching with actual button images")
    print("  3. Update YAML config with working button names or coordinates")
    print()
    
    microscope.close()
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
