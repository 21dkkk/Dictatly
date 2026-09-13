"""
Windows Autostart and Shortcut Manager for Dictatly.
Manages registry entry in HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
and creates desktop / Start Menu .lnk shortcuts with the official app icon.
"""

import sys
import winreg
from pathlib import Path
from typing import Optional, Dict

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "Dictatly"

def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent

def get_pythonw_executable() -> Path:
    """Resolve pythonw.exe in virtual environment or sys.prefix."""
    root = get_project_root()
    venv_pythonw = root / "venv" / "Scripts" / "pythonw.exe"
    if venv_pythonw.exists():
        return venv_pythonw
    prefix_pythonw = Path(sys.prefix) / "pythonw.exe"
    if prefix_pythonw.exists():
        return prefix_pythonw
    return Path(sys.executable)

def get_launcher_executable() -> Path:
    """Resolve Dictatly.exe if available, else pythonw.exe."""
    root = get_project_root()
    exe = root / "Dictatly.exe"
    if exe.exists():
        return exe
    return get_pythonw_executable()

def get_launch_command() -> str:
    """Format launch command line."""
    root = get_project_root()
    exe = root / "Dictatly.exe"
    if exe.exists():
        return f'"{exe}"'
    pythonw = get_pythonw_executable()
    main_py = root / "main.py"
    return f'"{pythonw}" "{main_py}"'

def get_startup_folder() -> Path:
    """Return user's Windows Startup folder."""
    import os
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    p = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_startup_shortcut_path() -> Path:
    """Return path to Dictatly.lnk inside the Windows Startup folder."""
    return get_startup_folder() / "Dictatly.lnk"

def _is_startup_approved(name: str, subkey: str) -> bool:
    """Check if the entry has been disabled in Windows Task Manager."""
    try:
        path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\{subkey}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, name)
            if isinstance(val, (bytes, bytearray)) and len(val) > 0:
                # 0x03 or 0x01 means disabled in Task Manager
                return (val[0] % 2) == 0
    except (FileNotFoundError, OSError):
        return True
    return True

def _set_startup_approved(name: str, subkey: str, enabled: bool):
    """Update or clear Task Manager approval state."""
    try:
        path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\{subkey}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
            val = b"\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" if enabled else b"\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, val)
    except (FileNotFoundError, OSError):
        pass

def _delete_registry_run_entry():
    """Remove legacy Run registry entry if present."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_REG_NAME)
    except (FileNotFoundError, OSError):
        pass

def is_autostart_enabled() -> bool:
    """Check if Dictatly is configured to run at Windows startup."""
    # 1. Primary check: shortcut in Windows Startup folder
    sc_path = get_startup_shortcut_path()
    if sc_path.exists():
        if _is_startup_approved("Dictatly.lnk", "StartupFolder"):
            return True

    # 2. Secondary check: legacy Run key in registry
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            if value and _is_startup_approved(APP_REG_NAME, "Run"):
                return True
    except (FileNotFoundError, OSError):
        pass

    return False

def set_autostart(enabled: bool) -> bool:
    """Enable or disable Dictatly at Windows startup via Startup folder shortcut."""
    sc_path = get_startup_shortcut_path()
    try:
        if enabled:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            root = get_project_root()
            launcher = get_launcher_executable()
            main_py = str(root / "main.py")
            ico_path = str(root / "resources" / "app_icon.ico")
            if not Path(ico_path).exists():
                ico_path = str(root / "resources" / "app_icon_64.png")

            shortcut = shell.CreateShortcut(str(sc_path))
            shortcut.TargetPath = str(launcher)
            if launcher.name.lower() == "dictatly.exe":
                shortcut.Arguments = ""
                shortcut.IconLocation = f"{launcher},0"
            else:
                shortcut.Arguments = f'"{main_py}"'
                shortcut.IconLocation = f"{ico_path},0"
            shortcut.WorkingDirectory = str(root)
            shortcut.Description = "Dictatly - Local Speech Dictation"
            shortcut.Save()

            # Ensure Task Manager hasn't marked it disabled
            _set_startup_approved("Dictatly.lnk", "StartupFolder", True)

            # Clean up old registry Run entry to prevent duplicate "Python" in Task Manager
            _delete_registry_run_entry()
            print(f"[Autostart] Enabled via Startup shortcut: {sc_path}")
        else:
            if sc_path.exists():
                sc_path.unlink()
                print(f"[Autostart] Removed Startup shortcut: {sc_path}")
            _delete_registry_run_entry()
            print("[Autostart] Disabled")
        return True
    except Exception as e:
        print(f"[Autostart] Error setting autostart: {e}")
        return False

def create_shortcuts(desktop: bool = True, start_menu: bool = True) -> Dict[str, bool]:
    """Create .lnk shortcuts with the official Dictatly icon."""
    results = {"desktop": False, "start_menu": False}
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        root = get_project_root()
        launcher = get_launcher_executable()
        main_py = str(root / "main.py")
        ico_path = str(root / "resources" / "app_icon.ico")
        if not Path(ico_path).exists():
            ico_path = str(root / "resources" / "app_icon_64.png")

        is_native_exe = (launcher.name.lower() == "dictatly.exe")

        if desktop:
            desktop_dir = shell.SpecialFolders("Desktop")
            shortcut_path = Path(desktop_dir) / "Dictatly.lnk"
            shortcut = shell.CreateShortcut(str(shortcut_path))
            shortcut.TargetPath = str(launcher)
            shortcut.Arguments = "" if is_native_exe else f'"{main_py}"'
            shortcut.WorkingDirectory = str(root)
            shortcut.IconLocation = f"{launcher},0" if is_native_exe else f"{ico_path},0"
            shortcut.Description = "Dictatly - Local Speech Dictation"
            shortcut.Save()
            results["desktop"] = True
            print(f"[Shortcut] Created Desktop shortcut: {shortcut_path}")

        if start_menu:
            programs_dir = shell.SpecialFolders("Programs")
            shortcut_path = Path(programs_dir) / "Dictatly.lnk"
            shortcut = shell.CreateShortcut(str(shortcut_path))
            shortcut.TargetPath = str(launcher)
            shortcut.Arguments = "" if is_native_exe else f'"{main_py}"'
            shortcut.WorkingDirectory = str(root)
            shortcut.IconLocation = f"{launcher},0" if is_native_exe else f"{ico_path},0"
            shortcut.Description = "Dictatly - Local Speech Dictation"
            shortcut.Save()
            results["start_menu"] = True
            print(f"[Shortcut] Created Start Menu shortcut: {shortcut_path}")

    except Exception as e:
        print(f"[Shortcut] Error creating shortcuts: {e}")

    return results
