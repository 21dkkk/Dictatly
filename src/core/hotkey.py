"""
Low-Level Windows Keyboard Hook (WH_KEYBOARD_LL).
Accurately discriminates Left vs Right modifier keys (Right Ctrl, Right Alt, Right Shift, Right Win),
supports single keys, modifier-only chords, and full key combinations.
Includes auto-repeat suppression and clean 64-bit ctypes prototypes.
"""

import time
import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Optional, Set, Dict

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_EXTENDED = 0x01
LLKHF_INJECTED = 0x10

# Virtual Key Mappings
VK_MAP = {
    0xA2: "VK_LCONTROL",
    0xA3: "VK_RCONTROL",
    0xA0: "VK_LSHIFT",
    0xA1: "VK_RSHIFT",
    0xA4: "VK_LMENU",      # Left Alt
    0xA5: "VK_RMENU",      # Right Alt (AltGr)
    0x5B: "VK_LWIN",
    0x5C: "VK_RWIN",
    0x14: "VK_CAPITAL",   # Caps Lock
    0x20: "VK_SPACE",
    0x0D: "VK_RETURN",
    0x1B: "VK_ESCAPE",
    0x09: "VK_TAB",
    0x2D: "VK_INSERT",
    0x2E: "VK_DELETE",
    0x70: "VK_F1",
    0x71: "VK_F2",
    0x72: "VK_F3",
    0x73: "VK_F4",
    0x74: "VK_F5",
    0x75: "VK_F6",
    0x76: "VK_F7",
    0x77: "VK_F8",
    0x78: "VK_F9",
    0x79: "VK_F10",
    0x7A: "VK_F11",
    0x7B: "VK_F12",
}

# Display names for UI
KEY_DISPLAY_NAMES = {
    "VK_RCONTROL": "Right Ctrl",
    "VK_LCONTROL": "Left Ctrl",
    "VK_RMENU": "Right Alt",
    "VK_LMENU": "Left Alt",
    "VK_RSHIFT": "Right Shift",
    "VK_LSHIFT": "Left Shift",
    "VK_RWIN": "Right Win",
    "VK_LWIN": "Left Win",
    "VK_CAPITAL": "Caps Lock",
    "VK_SPACE": "Space",
    "VK_RETURN": "Enter",
    "VK_ESCAPE": "Esc",
    "VK_TAB": "Tab",
    "VK_INSERT": "Insert",
    "VK_DELETE": "Delete",
    "VK_F1": "F1",
    "VK_F2": "F2",
    "VK_F3": "F3",
    "VK_F4": "F4",
    "VK_F5": "F5",
    "VK_F6": "F6",
    "VK_F7": "F7",
    "VK_F8": "F8",
    "VK_F9": "F9",
    "VK_F10": "F10",
    "VK_F11": "F11",
    "VK_F12": "F12",
}

def normalize_key_string(key_combo: str) -> str:
    """Sort and normalize combo string, e.g. 'VK_RSHIFT+VK_RCONTROL'."""
    parts = [p.strip() for p in key_combo.split("+") if p.strip()]
    return "+".join(sorted(parts))

def key_combo_to_display(key_combo: str) -> str:
    """Format combo string into human readable name."""
    parts = [p.strip() for p in key_combo.split("+") if p.strip()]
    display_parts = [KEY_DISPLAY_NAMES.get(p, p.replace("VK_", "")) for p in parts]
    return " + ".join(display_parts)

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong)
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

# Explicit 64-bit prototypes for Win32 Hook API
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK

user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL

user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_longlong

SINGLE_MODIFIER_KEYS = {
    "VK_RCONTROL", "VK_LCONTROL",
    "VK_RMENU", "VK_LMENU",
    "VK_RSHIFT", "VK_LSHIFT",
    "VK_RWIN", "VK_LWIN",
    "VK_CAPITAL"
}

class GlobalHotkeyManager:
    def __init__(self):
        self._hook = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._proc: Optional[HOOKPROC] = None
        
        self._pressed_keys: Set[str] = set()
        self._active_single_key: Optional[str] = None
        self._chord_triggered: bool = False
        self._active_ptt_combo: Optional[str] = None
        self._lock = threading.Lock()
        
        # Registered hotkeys: normalized_combo -> callback
        self._hotkey_callbacks: Dict[str, Callable[[], None]] = {}
        self._hotkey_press_callbacks: Dict[str, Callable[[], None]] = {}
        self._hotkey_release_callbacks: Dict[str, Callable[[], None]] = {}
        
        # Pause mode (gaming / meeting mute)
        self.is_paused: bool = False
        
        # Cancel key callback (Esc during recording)
        self.on_escape_pressed: Optional[Callable[[], None]] = None

        # Capture mode (when recording new hotkey in Settings)
        self.is_recording_new_hotkey: bool = False
        self.on_hotkey_recorded: Optional[Callable[[str], None]] = None

    def register_hotkey(self, combo: str, callback: Callable[[], None]):
        """Register toggle callback for a given combo (e.g. 'VK_RCONTROL')."""
        norm = normalize_key_string(combo)
        with self._lock:
            self._hotkey_callbacks[norm] = callback
            print(f"[Hotkey] Registered: {norm} ({key_combo_to_display(norm)})")

    def register_hotkey_handlers(self, combo: str, on_press: Optional[Callable[[], None]] = None, on_release: Optional[Callable[[], None]] = None):
        """Register separate on_press and on_release handlers for push-to-talk."""
        norm = normalize_key_string(combo)
        with self._lock:
            if on_press:
                self._hotkey_press_callbacks[norm] = on_press
            if on_release:
                self._hotkey_release_callbacks[norm] = on_release
            print(f"[Hotkey] Registered handlers: {norm} (press={bool(on_press)}, release={bool(on_release)})")

    def unregister_hotkey(self, combo: str):
        norm = normalize_key_string(combo)
        with self._lock:
            self._hotkey_callbacks.pop(norm, None)
            self._hotkey_press_callbacks.pop(norm, None)
            self._hotkey_release_callbacks.pop(norm, None)

    def clear_hotkeys(self):
        with self._lock:
            self._hotkey_callbacks.clear()
            self._hotkey_press_callbacks.clear()
            self._hotkey_release_callbacks.clear()
            self._active_single_key = None
            self._chord_triggered = False
            self._active_ptt_combo = None

    def set_paused(self, paused: bool):
        """Temporarily pauses or resumes all global hotkeys (e.g. for meetings/gaming)."""
        with self._lock:
            self.is_paused = paused
            self._pressed_keys.clear()
            self._active_single_key = None
            self._active_ptt_combo = None
            print(f"[Hotkey] Paused state set to: {paused}")

    def _get_clean_combo(self, keys: Set[str]) -> str:
        c = set(keys)
        # If Right Alt (AltGr) is down, Windows driver injects a synthetic Left Control.
        # Strip synthetic VK_LCONTROL so AltGr combos match cleanly.
        if "VK_RMENU" in c and "VK_LCONTROL" in c:
            c.remove("VK_LCONTROL")
        return "+".join(sorted(c))

    def _resolve_vk(self, vk_code: int, scan_code: int, flags: int) -> str:
        """Resolve precise VK including Left/Right distinction."""
        is_extended = bool(flags & LLKHF_EXTENDED)

        if vk_code in (0x11, 0xA2, 0xA3):  # VK_CONTROL, VK_LCONTROL, VK_RCONTROL
            return "VK_RCONTROL" if (is_extended or vk_code == 0xA3) else "VK_LCONTROL"
        elif vk_code in (0x12, 0xA4, 0xA5):  # VK_MENU, VK_LMENU, VK_RMENU (Alt)
            return "VK_RMENU" if (is_extended or vk_code == 0xA5) else "VK_LMENU"
        elif vk_code in (0x10, 0xA0, 0xA1):  # VK_SHIFT, VK_LSHIFT, VK_RSHIFT
            return "VK_RSHIFT" if (scan_code == 0x36 or vk_code == 0xA1) else "VK_LSHIFT"
        elif vk_code in (0x5B, 0x5C):  # Win keys
            return "VK_RWIN" if (is_extended or vk_code == 0x5C) else "VK_LWIN"
        elif vk_code in VK_MAP:
            return VK_MAP[vk_code]
        elif 0x41 <= vk_code <= 0x5A:  # A-Z
            return chr(vk_code)
        elif 0x30 <= vk_code <= 0x39:  # 0-9
            return chr(vk_code)
        elif 0x70 <= vk_code <= 0x87:  # F1-F24
            return f"VK_F{vk_code - 0x70 + 1}"
        else:
            return f"VK_0x{vk_code:02X}"

    def _hook_callback(self, nCode: int, wParam: wintypes.WPARAM, lParam: wintypes.LPARAM) -> ctypes.c_longlong:
        if nCode >= 0:
            try:
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                # Ignore injected / synthetic keystrokes to prevent recursive loops and input hangs
                if kb.flags & LLKHF_INJECTED:
                    return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                # If hotkeys are paused for meeting/gaming, pass through all keys
                if self.is_paused and not self.is_recording_new_hotkey:
                    return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                key_name = self._resolve_vk(kb.vkCode, kb.scanCode, kb.flags)
                
                is_down = (wParam in (WM_KEYDOWN, WM_SYSKEYDOWN))
                is_up = (wParam in (WM_KEYUP, WM_SYSKEYUP))

                if is_down:
                    # Check for Escape cancellation while dictating
                    if key_name == "VK_ESCAPE" and self.on_escape_pressed and not self.is_recording_new_hotkey:
                        cb = self.on_escape_pressed
                        self.on_escape_pressed = None
                        threading.Thread(target=cb, daemon=True).start()
                        return 1  # Suppress Escape key so it solely cancels dictation

                    with self._lock:
                        already_pressed = key_name in self._pressed_keys
                        self._pressed_keys.add(key_name)
                        clean_combo = self._get_clean_combo(self._pressed_keys)

                    if self.is_recording_new_hotkey:
                        if self.on_hotkey_recorded:
                            self.on_hotkey_recorded(clean_combo)
                        return 1  # Suppress key in recording mode

                    # Suppress keyboard auto-repeat (if already down, don't re-trigger)
                    if already_pressed:
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    # 1. Check if an explicit on_press callback is registered for this combo (Push-to-Talk)
                    press_cb = self._hotkey_press_callbacks.get(clean_combo)
                    if press_cb:
                        self._active_ptt_combo = clean_combo
                        threading.Thread(target=press_cb, daemon=True).start()
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    # 2. Check if this is a multi-key chord or a solitary key (Toggle mode)
                    parts = clean_combo.split("+")
                    with self._lock:
                        if len(parts) > 1:
                            cb = self._hotkey_callbacks.get(clean_combo)
                            if cb:
                                self._chord_triggered = True
                                threading.Thread(target=cb, daemon=True).start()
                        else:
                            if clean_combo in SINGLE_MODIFIER_KEYS:
                                # Solitary modifier: prime to trigger on release if no chord is pressed
                                self._active_single_key = clean_combo
                                self._chord_triggered = False
                            else:
                                # Regular key (e.g. F8, Space): trigger immediately on KeyDown
                                cb = self._hotkey_callbacks.get(clean_combo)
                                if cb:
                                    threading.Thread(target=cb, daemon=True).start()

                elif is_up:
                    with self._lock:
                        self._pressed_keys.discard(key_name)
                        if key_name == "VK_RMENU":
                            self._pressed_keys.discard("VK_LCONTROL")

                        # Check explicit on_release callback (Push-to-Talk)
                        rel_cb = None
                        if self._active_ptt_combo and key_name in self._active_ptt_combo.split("+"):
                            rel_cb = self._hotkey_release_callbacks.get(self._active_ptt_combo)
                            self._active_ptt_combo = None
                        elif key_name in self._hotkey_release_callbacks:
                            rel_cb = self._hotkey_release_callbacks.get(key_name)

                        if rel_cb:
                            threading.Thread(target=rel_cb, daemon=True).start()

                        # If solitary modifier released without a chord fired during hold (Toggle mode)
                        elif self._active_single_key == key_name:
                            if not self._chord_triggered:
                                cb = self._hotkey_callbacks.get(key_name)
                                if cb:
                                    threading.Thread(target=cb, daemon=True).start()
                            self._active_single_key = None
                            self._chord_triggered = False
            except Exception:
                pass

        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        """Start the Windows low-level hook in a dedicated message pump thread."""
        if self._thread and self._thread.is_alive():
            return

        def run():
            self._thread_id = kernel32.GetCurrentThreadId()
            self._proc = HOOKPROC(self._hook_callback)
            
            # For WH_KEYBOARD_LL (global hook), hMod must be None/NULL on Windows
            self._hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self._proc,
                None,
                0
            )
            if not self._hook:
                err = ctypes.GetLastError()
                print(f"[Hotkey] Failed to install keyboard hook. Error code: {err}")
                return

            print(f"[Hotkey] Low-level keyboard hook installed successfully (handle: {self._hook}).")

            # Standard Win32 Message Loop
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the hook and exit message loop."""
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            self._thread_id = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
