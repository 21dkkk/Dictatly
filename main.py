"""
Dictatly for Windows.
Fast, private, local dictation with floating caret HUD, global hotkeys,
hardware-accelerated Faster-Whisper, and optional AI cleanup.
"""

import os
import sys
import ctypes
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add project root to sys.path
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure NVIDIA DLL directories are discovered
def setup_cuda_paths():
    if sys.platform == "win32":
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).parent
            for d in [exe_dir, exe_dir / "_internal"]:
                if d.exists():
                    try:
                        os.add_dll_directory(str(d))
                    except Exception:
                        pass
                    if str(d) not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")
            return

        site_packages = Path(sys.prefix) / "Lib" / "site-packages"
        for sub in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin", "ctranslate2"]:
            p = site_packages / sub
            if p.exists():
                try:
                    os.add_dll_directory(str(p))
                except Exception:
                    pass
                if str(p) not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")

setup_cuda_paths()

from PySide6.QtGui import QIcon
from src.app import DictatlyApp

_GLOBAL_MUTEX = None

def release_single_instance_mutex():
    """Explicitly release and close the Windows single instance mutex."""
    global _GLOBAL_MUTEX
    if _GLOBAL_MUTEX:
        try:
            ctypes.windll.kernel32.CloseHandle(_GLOBAL_MUTEX)
        except Exception:
            pass
        _GLOBAL_MUTEX = None

def acquire_single_instance_mutex() -> bool:
    """Acquire single instance mutex, retrying during restarts if needed."""
    global _GLOBAL_MUTEX
    import time
    mutex_name = "Global\\Dictatly_SingleInstance_Mutex"
    kernel32 = ctypes.windll.kernel32

    # If restart flag present, give prior instance a brief grace period to release mutex
    max_attempts = 15 if any(arg in sys.argv for arg in ("--restart", "--settings", "--history")) else 1
    for attempt in range(max_attempts):
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()
        if last_error != 183:  # 183 = ERROR_ALREADY_EXISTS
            _GLOBAL_MUTEX = mutex
            return True
        kernel32.CloseHandle(mutex)
        time.sleep(0.1)

    # If still busy and invoked with explicit restart/command flag, terminate previous instances cleanly
    if any(arg in sys.argv for arg in ("--settings", "--history", "--restart")):
        import subprocess
        try:
            current_pid = os.getpid()
            ps_script = (
                f"Get-CimInstance Win32_Process | "
                f"Where-Object {{ ($_.Name -eq 'Dictatly.exe' -or $_.CommandLine -like '*main.py*') -and $_.ProcessId -ne {current_pid} }} | "
                f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
            )
            creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                timeout=3,
                creationflags=creation_flags
            )
        except Exception:
            pass

        time.sleep(0.15)
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        _GLOBAL_MUTEX = mutex
        return True

    return False

def main():
    # Explicit Windows AppUserModelID for system toast notifications
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dictatly.WindowsApp.1.0")
    except Exception:
        pass

    if not acquire_single_instance_mutex():
        print("[Dictatly] Another instance is already running.")
        sys.exit(0)

    # Enable High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Dictatly")

    # Global window icon
    icon_path = BASE_DIR / "resources" / "app_icon.ico"
    if not icon_path.exists():
        icon_path = BASE_DIR / "resources" / "app_icon_64.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    if "--install-shortcuts" in sys.argv:
        from src.core.autostart import create_shortcuts
        res = create_shortcuts(desktop=True, start_menu=True)
        print(f"[Dictatly] Shortcuts created: {res}")
        sys.exit(0)

    # Initialize Main App Coordinator
    dictate_app = DictatlyApp()

    # If launched with --settings or --history
    if "--settings" in sys.argv:
        dictate_app.show_settings()
    elif "--history" in sys.argv:
        dictate_app.toggle_history()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
