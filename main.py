"""
Dictatly for Windows.
Fast, private, local dictation with floating caret HUD, global hotkeys,
hardware-accelerated Faster-Whisper, and optional AI cleanup.
"""

import os
import sys
import ctypes
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
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

        candidate_roots = [
            Path(sys.prefix) / "Lib" / "site-packages",
            Path(sys.base_prefix) / "Lib" / "site-packages",
            Path(r"F:\Coding\Dictatly\venv\Lib\site-packages"),
        ]
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidate_roots.append(Path(local_app) / "Programs" / "Python" / "Python312" / "Lib" / "site-packages")
            candidate_roots.append(Path(local_app) / "Dictatly" / "venv" / "Lib" / "site-packages")

        try:
            import site
            for sp in site.getsitepackages():
                candidate_roots.append(Path(sp))
        except Exception:
            pass

        for root in candidate_roots:
            for sub in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin", "ctranslate2"]:
                p = root / sub
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

def setup_logging():
    """Redirect stdout/stderr to rotating %APPDATA%/Dictatly/dictatly.log for diagnostics."""
    try:
        from src.config import get_app_data_dir
        log_dir = get_app_data_dir()
        log_file = log_dir / "dictatly.log"
        if log_file.exists() and log_file.stat().st_size > 1024 * 1024:
            old_log = log_dir / "dictatly.old.log"
            if old_log.exists():
                old_log.unlink()
            log_file.rename(old_log)

        class LogWriter:
            def __init__(self, original, filepath):
                self.original = original
                self.file = open(filepath, "a", encoding="utf-8", buffering=1)

            def write(self, msg):
                if not msg:
                    return
                try:
                    if self.original:
                        self.original.write(msg)
                except Exception:
                    pass
                try:
                    self.file.write(msg)
                except Exception:
                    pass

            def flush(self):
                try:
                    if self.original:
                        self.original.flush()
                except Exception:
                    pass
                try:
                    self.file.flush()
                except Exception:
                    pass

        sys.stdout = LogWriter(sys.stdout, log_file)
        sys.stderr = LogWriter(sys.stderr, log_file)
    except Exception:
        pass

setup_logging()

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

def send_ipc_command(command: str, retries: int = 3, retry_delay: float = 0.15) -> bool:
    """Send command to running Dictatly instance via Windows Named Pipe with brief retries."""
    from multiprocessing.connection import Client
    import time
    for attempt in range(retries):
        try:
            with Client(r'\\.\pipe\Dictatly_IPC', 'AF_PIPE') as conn:
                conn.send(command)
                return True
        except Exception:
            if attempt < retries - 1:
                time.sleep(retry_delay)
    return False

def acquire_single_instance_mutex() -> bool:
    """Acquire session single instance mutex, retrying during restarts if needed."""
    global _GLOBAL_MUTEX
    import time
    mutex_name = "Dictatly_SingleInstance_Mutex_Session"
    kernel32 = ctypes.windll.kernel32

    # If restart flag present, give prior instance a brief grace period to release mutex
    is_restart = "--restart" in sys.argv
    max_attempts = 15 if is_restart else 1
    for attempt in range(max_attempts):
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()
        ERROR_ALREADY_EXISTS = 183
        if mutex and last_error != ERROR_ALREADY_EXISTS:
            _GLOBAL_MUTEX = mutex
            return True
        if mutex:
            kernel32.CloseHandle(mutex)
        time.sleep(0.1)

    # If still busy and invoked with explicit restart flag, terminate previous instances cleanly
    if is_restart:
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
        cmd = "history" if "--history" in sys.argv else "settings"
        send_ipc_command(cmd)
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
