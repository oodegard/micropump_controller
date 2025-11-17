"""
Simple test script for image detection and clicking

This script:
1. Looks for run.png on the screen
2. Clicks it when found
3. Waits for it to disappear (greyed out/processing)
4. Waits for it to reappear (normal state)
5. Prints "DONE" signal

Usage:
    python test_click_detection.py
    python test_click_detection.py --image path/to/button.png
"""

import pyautogui
import time
from pathlib import Path
from PIL import ImageGrab
import argparse


def find_and_click_image(image_path: str, confidence: float = 0.8) -> bool:
    """
    Find and click an image on screen.
    
    Args:
        image_path: Path to the image file to find
        confidence: Match confidence threshold (0.0-1.0)
    
    Returns:
        True if image found and clicked, False otherwise
    """
    try:
        print(f"[INFO] Searching for image: {image_path} (confidence >= {confidence})")
        
        # Try to find all matches to show similarity scores
        try:
            all_locations = list(pyautogui.locateAllOnScreen(image_path, confidence=0.1))
            if all_locations:
                print(f"[INFO] Found {len(all_locations)} potential matches (confidence >= 0.1)")
        except Exception:
            pass
        
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        
        if location:
            # Get center of the found image
            center = pyautogui.center(location)
            print(f"[SUCCESS] Image found at: {location}")
            print(f"[INFO] Clicking at center: ({center.x}, {center.y})")
            
            # Click the center
            pyautogui.click(center.x, center.y)
            print(f"[SUCCESS] Clicked image")
            return True
        else:
            print(f"[WARNING] Image not found on screen with confidence >= {confidence}")
            print(f"[INFO] Try lowering --confidence value (e.g., 0.6 or 0.7)")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to find/click image: {e}")
        return False


def wait_for_image_to_disappear(image_path: str, timeout: float = 30.0, check_interval: float = 0.5, confidence: float = 0.8) -> bool:
    """
    Wait for an image to disappear from the screen (greyed out/processing).
    
    Args:
        image_path: Path to the image file
        timeout: Maximum time to wait in seconds
        check_interval: How often to check in seconds
        confidence: Match confidence threshold
    
    Returns:
        True if image disappeared, False if timeout
    """
    print(f"[INFO] Waiting for image to disappear (processing state)...")
    print(f"[INFO] Using confidence threshold: {confidence}")
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location is None:
                print(f"[SUCCESS] Image disappeared after {check_count} checks (processing started)")
                return True
            else:
                if check_count % 10 == 0:  # Print every 10 checks
                    elapsed = time.time() - start_time
                    print(f"[INFO] Still visible after {elapsed:.1f}s (check #{check_count})")
        except Exception as e:
            # Image not found (good - it disappeared)
            print(f"[SUCCESS] Image disappeared after {check_count} checks (processing started)")
            return True
        
        time.sleep(check_interval)
    
    print(f"[WARNING] Timeout waiting for image to disappear after {check_count} checks")
    print(f"[INFO] Image may still be visible - try lowering confidence or checking if button changes appearance")
    return False


def wait_for_image_to_reappear(image_path: str, timeout: float = 120.0, check_interval: float = 1.0, confidence: float = 0.8) -> bool:
    """
    Wait for an image to reappear on the screen (processing complete).
    
    Args:
        image_path: Path to the image file
        timeout: Maximum time to wait in seconds
        check_interval: How often to check in seconds
        confidence: Match confidence threshold
    
    Returns:
        True if image reappeared, False if timeout
    """
    print(f"[INFO] Waiting for image to reappear (processing complete)...")
    print(f"[INFO] Using confidence threshold: {confidence}")
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location is not None:
                elapsed = time.time() - start_time
                print(f"[SUCCESS] Image reappeared after {elapsed:.1f} seconds ({check_count} checks)")
                return True
            else:
                if check_count % 10 == 0:  # Print every 10 checks
                    elapsed = time.time() - start_time
                    print(f"[INFO] Still waiting after {elapsed:.1f}s (check #{check_count})")
        except Exception:
            pass
        
        time.sleep(check_interval)
    
    print(f"[WARNING] Timeout waiting for image to reappear after {check_count} checks")
    return False


def main():
    parser = argparse.ArgumentParser(description="Test image detection and clicking")
    parser.add_argument(
        "--image",
        type=str,
        default="run.png",
        help="Path to the button image file (default: run.png)"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.99,
        help="Image matching confidence (0.0-1.0, default: 0.99)"
    )
    parser.add_argument(
        "--disappear-timeout",
        type=float,
        default=30.0,
        help="Timeout for waiting for image to disappear (default: 30s)"
    )
    parser.add_argument(
        "--reappear-timeout",
        type=float,
        default=120.0,
        help="Timeout for waiting for image to reappear (default: 120s)"
    )
    
    args = parser.parse_args()
    
    # Check if image file exists
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[ERROR] Image file not found: {image_path}")
        print(f"[INFO] Looking in parent directory...")
        parent_image = Path(__file__).parent.parent / args.image
        if parent_image.exists():
            image_path = parent_image
            print(f"[SUCCESS] Found image at: {image_path}")
        else:
            print(f"[ERROR] Image file not found in parent directory either")
            return
    
    print("=" * 60)
    print("Image Detection and Click Test")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Confidence: {args.confidence}")
    print("=" * 60)
    
    # Step 1: Find and click the image
    print("\n[STEP 1] Finding and clicking image...")
    if not find_and_click_image(str(image_path), confidence=args.confidence):
        print("[FAILED] Could not find or click image")
        return
    
    print("[SUCCESS] Image clicked successfully")
    time.sleep(0.5)  # Brief pause after click
    
    # Step 2: Wait for image to disappear (processing starts)
    print("\n[STEP 2] Waiting for processing to start...")
    if not wait_for_image_to_disappear(str(image_path), timeout=args.disappear_timeout, confidence=args.confidence):
        print("[WARNING] Image did not disappear as expected")
        print("[INFO] This might mean:")
        print("       - Button doesn't change appearance when clicked")
        print("       - Confidence threshold is too high for the changed appearance")
        print("       - Processing is instant (no visible state change)")
        # Continue anyway - maybe it's instant
    
    # Step 3: Wait for image to reappear (processing completes)
    print("\n[STEP 3] Waiting for processing to complete...")
    if not wait_for_image_to_reappear(str(image_path), timeout=args.reappear_timeout, confidence=args.confidence):
        print("[FAILED] Image did not reappear - processing may have failed or taken too long")
        return
    
    # Step 4: Send "DONE" signal
    print("\n[STEP 4] Processing complete!")
    print("=" * 60)
    print("DONE SIGNAL - Ready to transmit")
    print("=" * 60)
    print("\n[INFO] Test completed successfully!")


if __name__ == "__main__":
    main()
