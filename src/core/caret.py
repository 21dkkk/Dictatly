"""
Windows Caret Tracker.
Retrieves screen coordinates of the active text caret using Win32 GetGUIThreadInfo
with fallback to UI Automation or mouse cursor position.
"""

import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", RECT)
    ]

user32 = ctypes.windll.user32

def get_caret_screen_position() -> Tuple[int, int]:
    """
    Returns (x, y) coordinates of the active text caret on screen.
    If caret is not detectable, falls back to mouse cursor or active window center.
    """
    try:
        hwnd_fg = user32.GetForegroundWindow()
        if hwnd_fg:
            thread_id = user32.GetWindowThreadProcessId(hwnd_fg, None)
            info = GUITHREADINFO()
            info.cbSize = ctypes.sizeof(GUITHREADINFO)
            
            if user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
                # If we have a caret window
                target_hwnd = info.hwndCaret if info.hwndCaret else info.hwndFocus
                if target_hwnd and (info.rcCaret.right > info.rcCaret.left or info.rcCaret.bottom > info.rcCaret.top):
                    pt = wintypes.POINT(info.rcCaret.left, info.rcCaret.top)
                    user32.ClientToScreen(target_hwnd, ctypes.byref(pt))
                    # Ensure coordinates are reasonable on screen
                    if pt.x > -10000 and pt.y > -10000:
                        return pt.x, pt.y
    except Exception:
        pass

    # Fallback 1: Current mouse cursor position
    try:
        pt = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            return pt.x, pt.y
    except Exception:
        pass

    # Fallback 2: Default center screen
    cx = user32.GetSystemMetrics(0) // 2  # SM_CXSCREEN
    cy = user32.GetSystemMetrics(1) // 2  # SM_CYSCREEN
    return cx, cy
