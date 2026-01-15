"""Simple message box for user interaction."""

from typing import Optional


class MessageBox:
    """Windows message box for pausing protocol execution."""

    @staticmethod
    def show_ok(message: str, title: str = "OK") -> bool:
        """Show OK dialog. Blocks until user clicks OK.
        
        Args:
            message: Message text to display
            title: Window title (default: "OK")
            
        Returns:
            True if OK was clicked (always true for now)
        """
        try:
            import ctypes
            # MessageBoxW(hwnd, text, caption, type)
            # type=0 means MB_OK (single OK button)
            result = ctypes.windll.user32.MessageBoxW(0, message, title, 0)
            return result == 1  # IDOK
        except Exception as e:
            # Fallback for non-Windows or error
            print(f"[MESSAGE] {message}")
            return True
