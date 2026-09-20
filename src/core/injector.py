"""
Text Injector for Windows.
Injects transcribed text at active cursor location via Windows Clipboard + Ctrl+V simulation.
Ensures full 64-bit ctypes compatibility, modifier key release, and reliable pasting.
"""

import time
import ctypes
from ctypes import wintypes
from typing import Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
KEYEVENTF_KEYUP = 0x0002

VK_CONTROL = 0x11
VK_V = 0x56
VK_RETURN = 0x0D

# Explicit 64-bit prototypes for memory and clipboard APIs
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL

user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE

user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE

user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulonglong]
user32.keybd_event.restype = None

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wintypes.SHORT

user32.GetOpenClipboardWindow.argtypes = []
user32.GetOpenClipboardWindow.restype = wintypes.HWND

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL

user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL

user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
user32.MapVirtualKeyW.restype = wintypes.UINT

def force_foreground_window(hwnd: int) -> bool:
    """
    Reliably restores foreground window from a background thread.
    Bypasses Windows Foreground Lock timeout using AttachThreadInput and AllowSetForegroundWindow.
    """
    if not hwnd or not user32.IsWindow(hwnd):
        return False
    cur_fg = user32.GetForegroundWindow()
    if cur_fg == hwnd:
        return True

    fg_thread = user32.GetWindowThreadProcessId(cur_fg, None)
    my_thread = kernel32.GetCurrentThreadId()

    attached = False
    if fg_thread and fg_thread != my_thread:
        attached = bool(user32.AttachThreadInput(my_thread, fg_thread, True))

    try:
        user32.AllowSetForegroundWindow(0xFFFFFFFF)  # ASFW_ANY
        res = user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        return bool(res)
    finally:
        if attached:
            user32.AttachThreadInput(my_thread, fg_thread, False)

def get_clipboard_text() -> Optional[str]:
    """Retrieve current text from Windows clipboard."""
    for _ in range(5):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return None

    try:
        h_glb = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_glb:
            return None
        ptr = kernel32.GlobalLock(h_glb)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h_glb)
    finally:
        user32.CloseClipboard()

def set_clipboard_text(text: str) -> bool:
    """Set text into Windows clipboard with 64-bit memory management."""
    if text is None:
        return False

    data_bytes = text.encode("utf-16-le") + b"\x00\x00"
    bytes_len = len(data_bytes)

    for _ in range(10):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        print("[Injector] Failed to open clipboard after retries.")
        return False

    try:
        user32.EmptyClipboard()
        h_glb = kernel32.GlobalAlloc(GMEM_MOVEABLE, bytes_len)
        if not h_glb:
            print("[Injector] GlobalAlloc failed.")
            return False

        ptr = kernel32.GlobalLock(h_glb)
        if not ptr:
            kernel32.GlobalFree(h_glb)
            print("[Injector] GlobalLock failed.")
            return False

        try:
            ctypes.memmove(ptr, data_bytes, bytes_len)
        finally:
            kernel32.GlobalUnlock(h_glb)

        res = user32.SetClipboardData(CF_UNICODETEXT, h_glb)
        if not res:
            kernel32.GlobalFree(h_glb)
            print(f"[Injector] SetClipboardData failed: {ctypes.GetLastError()}")
            return False

        return True
    finally:
        user32.CloseClipboard()

KEYEVENTF_EXTENDEDKEY = 0x0001

def send_paste_combination():
    """Simulates Ctrl+V reliably with hardware scan codes and proper dwell time."""
    # Unconditionally release any modifier keys (Ctrl, Alt, Shift, Win)
    for vk in (0xA3, 0xA2, 0x11, 0xA5, 0xA4, 0x12, 0xA1, 0xA0, 0x10, 0x5B, 0x5C):
        scan = user32.MapVirtualKeyW(vk, 0)
        flags = KEYEVENTF_KEYUP
        if vk in (0xA3, 0xA5, 0x5C):
            flags |= KEYEVENTF_EXTENDEDKEY
        user32.keybd_event(vk, scan, flags, 0)
    time.sleep(0.02)

    ctrl_scan = user32.MapVirtualKeyW(VK_CONTROL, 0)
    v_scan = user32.MapVirtualKeyW(VK_V, 0)

    # Press Ctrl + V with scan codes and sufficient dwell time (30ms) for Electron/Chromium/WPF message pumps
    user32.keybd_event(VK_CONTROL, ctrl_scan, 0, 0)
    time.sleep(0.025)
    user32.keybd_event(VK_V, v_scan, 0, 0)
    time.sleep(0.035)
    user32.keybd_event(VK_V, v_scan, KEYEVENTF_KEYUP, 0)
    time.sleep(0.025)
    user32.keybd_event(VK_CONTROL, ctrl_scan, KEYEVENTF_KEYUP, 0)

def send_enter_key():
    """Simulates Enter key with hardware scan code."""
    time.sleep(0.04)
    scan = user32.MapVirtualKeyW(VK_RETURN, 0)
    user32.keybd_event(VK_RETURN, scan, 0, 0)
    time.sleep(0.025)
    user32.keybd_event(VK_RETURN, scan, KEYEVENTF_KEYUP, 0)

def inject_text(text: str, suffix_mode: str = "space", press_enter: bool = False, target_hwnd: Optional[int] = None):
    """
    Injects transcribed text at active cursor location.
    Copies text to clipboard, waits for any clipboard listeners to release, and fires Ctrl+V.
    """
    if not text:
        return

    # Apply suffix
    if suffix_mode == "space" and not text.endswith(" "):
        text = text + " "
    elif suffix_mode == "newline" and not text.endswith("\n"):
        text = text + "\n"

    # 1. Restore target window focus if specified
    if target_hwnd:
        force_foreground_window(target_hwnd)
        time.sleep(0.04)

    # 2. Put text into clipboard
    success = set_clipboard_text(text)
    if not success:
        print("[Injector] Could not set clipboard text.")
        return

    # 3. Wait for any Windows Clipboard listeners (Clipboard History, etc.) to release lock
    t0 = time.time()
    while user32.GetOpenClipboardWindow() and (time.time() - t0) < 0.35:
        time.sleep(0.02)

    # Short settle delay for target application to observe clipboard update
    time.sleep(0.06)

    # 4. Re-verify foreground window right before firing Ctrl+V
    if target_hwnd and user32.GetForegroundWindow() != target_hwnd:
        force_foreground_window(target_hwnd)
        time.sleep(0.04)

    print(f"[Injector] Text placed into clipboard ({len(text)} chars). Simulating Ctrl+V...")
    send_paste_combination()

    if press_enter:
        send_enter_key()


