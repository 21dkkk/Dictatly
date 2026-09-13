"""
Configuration manager for SuperDictate Windows.
Persists settings in %APPDATA%/SuperDictate/config.json.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

def get_app_data_dir() -> Path:
    """Return platform app data directory: %APPDATA%/SuperDictate."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    p = Path(appdata) / "SuperDictate"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_default_export_dir() -> Path:
    """Return default export directory (Desktop)."""
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        desktop = Path(userprofile) / "Desktop"
        if desktop.exists():
            return desktop
    return Path.home()

DEFAULT_CONFIG: Dict[str, Any] = {
    # Hotkeys (Win32 Virtual Key names / codes)
    "hotkey_main": "VK_RCONTROL",          # Right Control
    "hotkey_alt": "VK_RSHIFT+VK_RCONTROL",  # Alternative Finish (inverts Enter behavior)
    "hotkey_history": "VK_RMENU+VK_RCONTROL", # Quick History (Right Alt + Right Ctrl)
    
    # Behavior
    "enter_after_insert": False,
    "paste_suffix": "space",                # "space", "none", "newline"
    
    # Audio & Model
    "microphone_device": None,             # None = default input device
    "dictation_language": "auto",          # "auto", "ru", "en"
    "whisper_model": "large-v3-turbo",     # "large-v3-turbo", "small", "base"
    "compute_device": "auto",              # "auto", "cuda", "cpu"
    "export_folder": str(get_default_export_dir()),
    
    # UI & Appearance
    "interface_language": "ru",            # "ru" or "en"
    "capsule_size": "medium",              # "small", "medium", "large"
    "capsule_theme": "dark",               # "dark", "light"
    
    # AI Text Cleanup (OpenAI / Groq API compatible)
    "ai_cleanup_enabled": False,
    "ai_base_url": "https://api.groq.com/openai/v1",
    "ai_model": "openai/gpt-oss-20b",
    "ai_api_key_encrypted": "",            # DPAPI encrypted base64
}

class AppConfig:
    def __init__(self):
        self.config_dir = get_app_data_dir()
        self.config_path = self.config_dir / "config.json"
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        self._data = dict(DEFAULT_CONFIG)
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._data.update(loaded)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Using defaults.")
        else:
            self.save()

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any):
        self._data[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any):
        self.set(key, value)
