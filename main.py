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
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure NVIDIA DLL directories are discovered
def setup_cuda_paths():
    if sys.platform == "win32":
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

def main():
    # Explicit Windows AppUserModelID for system toast notifications
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Dictatly.WindowsApp.1.0")
    except Exception:
        pass

    # Windows Single Instance Mutex
    mutex_name = "Global\\Dictatly_SingleInstance_Mutex"
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    
    # 183 = ERROR_ALREADY_EXISTS
    if last_error == 183:
        if any(arg in sys.argv for arg in ("--settings", "--history", "--restart")):
            # Terminate older instance and take over
            import subprocess
            subprocess.run([
                "powershell", "-NoProfile", "-Command",
                f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*main.py*' -and $_.ProcessId -ne {os.getpid()} }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
            ], capture_output=True)
            kernel32.CloseHandle(mutex)
            mutex = kernel32.CreateMutexW(None, False, mutex_name)
        else:
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
