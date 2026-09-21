"""
Main Application Coordinator for Dictatly.
Coordinates audio capture, global hotkeys, caret tracker, ASR engine, AI cleaner,
floating capsule HUD, history, and settings.
"""

import sys
import time
import threading
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, QTimer, Slot
from PySide6.QtWidgets import QApplication

from .config import AppConfig
from .localization import t
from .core.audio import AudioRecorder
from .core.caret import get_caret_screen_position
from .core.hotkey import GlobalHotkeyManager, key_combo_to_display
from .core.injector import inject_text
from .core.database import HistoryDatabase
from .core.security import decrypt_secret
from .core.sound import play_audio_cue
from .core.text_postprocess import apply_vocabulary, format_smart_punctuation
from .engine.transcriber import SpeechTranscriber
from .engine.ai_cleaner import AICleaner
from .ui.hud import RecordingHUD, HUDState
from .ui.history_window import QuickHistoryWindow
from .ui.settings_window import SettingsWindow
from .ui.onboarding_dialog import OnboardingDialog
from .ui.tray import SystemTrayManager
from .core.autostart import set_autostart

class DictatlyApp(QObject):
    # Signals for thread-safe UI updates from background threads
    hud_state_signal = Signal(int)
    hud_volume_signal = Signal(float)
    hud_position_signal = Signal(int, int)
    batch_progress_signal = Signal(int, int, float)  # current, total, progress 0..1
    batch_finished_signal = Signal()
    open_history_signal = Signal()
    open_settings_signal = Signal()

    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.db = HistoryDatabase()

        # Core Engines
        self.audio = AudioRecorder(
            device_index=self.config["microphone_device"],
            silence_timeout_seconds=float(self.config.get("silence_timeout_seconds", 0)),
            device_name=self.config.get("microphone_device_name")
        )
        self.audio.on_volume_level = self._on_volume_level
        self.audio.on_error = self._on_audio_error

        self.transcriber = SpeechTranscriber(
            model_size=self.config["whisper_model"],
            device_pref=self.config["compute_device"]
        )

        self.hotkey_mgr = GlobalHotkeyManager()

        # Pre-warm Whisper model in background thread
        threading.Thread(target=self.transcriber.load_model, daemon=True).start()

        # UI Components
        self.hud = RecordingHUD(
            size_mode=self.config["capsule_size"],
            theme=self.config["capsule_theme"]
        )
        self.hud_hwnd: int = int(self.hud.winId()) if self.hud else 0
        self.history_window: Optional[QuickHistoryWindow] = None
        self.settings_window: Optional[SettingsWindow] = None
        self.tray = SystemTrayManager(self.config)
        self.target_hwnd: Optional[int] = None

        # Wire Signals
        self.hud_state_signal.connect(self.hud.set_state)
        self.hud_volume_signal.connect(self.hud.set_volume)
        self.hud_position_signal.connect(self.hud.move_to_caret)
        self.batch_progress_signal.connect(self._on_batch_progress)
        self.batch_finished_signal.connect(self._on_batch_finished)

        self.open_history_signal.connect(self.toggle_history)
        self.open_settings_signal.connect(self.show_settings)

        # Connect Tray Actions
        self.tray.open_settings_requested.connect(self.show_settings)
        self.tray.open_history_requested.connect(self.toggle_history)
        self.tray.toggle_pause_requested.connect(self._on_pause_hotkeys_toggled)
        self.tray.toggle_dictation_requested.connect(self.toggle_dictation)
        self.tray.exit_requested.connect(self.exit_app)

        # Register & start Global Hotkeys
        self._register_all_hotkeys()
        self.hotkey_mgr.start()

        # Startup notification
        lang = self.config["interface_language"]
        main_key_display = key_combo_to_display(self.config["hotkey_main"])
        msg = t("app_ready_notification", lang, hotkey=main_key_display)
        QTimer.singleShot(800, lambda: self.tray.show_notification("Dictatly", msg))

        # Single-instance IPC server
        self._ipc_server = None
        self._start_ipc_server()

        # First-run onboarding check
        self.onboarding_dialog: Optional[OnboardingDialog] = None
        if not self.config.get("first_run_completed", False):
            QTimer.singleShot(400, self.show_onboarding)
        elif self.config.get("autostart_with_windows", False):
            set_autostart(True)

    def _register_all_hotkeys(self):
        """Registers configured hotkeys."""
        self.hotkey_mgr.clear_hotkeys()
        mode = self.config.get("recording_mode", "toggle")

        # 1. Main Hotkey
        main_key = self.config["hotkey_main"]
        if main_key:
            if mode == "push_to_talk":
                self.hotkey_mgr.register_hotkey_handlers(
                    main_key,
                    on_press=lambda: self._start_dictation(),
                    on_release=lambda: self._finish_dictation(inverted_enter=False)
                )
            else:
                self.hotkey_mgr.register_hotkey(main_key, lambda: self.toggle_dictation(inverted_enter=False))

        # 2. Alternative Finish Hotkey
        alt_key = self.config["hotkey_alt"]
        if alt_key:
            if mode == "push_to_talk":
                self.hotkey_mgr.register_hotkey_handlers(
                    alt_key,
                    on_press=lambda: self._start_dictation(),
                    on_release=lambda: self._finish_dictation(inverted_enter=True)
                )
            else:
                self.hotkey_mgr.register_hotkey(alt_key, lambda: self.toggle_dictation(inverted_enter=True))

        # 3. Quick History Hotkey
        hist_key = self.config["hotkey_history"]
        if hist_key:
            self.hotkey_mgr.register_hotkey(hist_key, self.open_history_signal.emit)

    def _on_audio_error(self, err_msg: str):
        """Surfaces audio hardware failure notifications to the system tray."""
        lang = self.config.get("interface_language", "ru")
        title = "Dictatly — Ошибка аудио" if lang == "ru" else "Dictatly — Audio Error"
        msg = f"Микрофон недоступен: {err_msg}" if lang == "ru" else f"Microphone error: {err_msg}"
        self.tray.show_notification(title, msg)
        self.hud_state_signal.emit(HUDState.IDLE)

    def _on_volume_level(self, vol: float):
        """RMS Volume update to capsule equalizer bars."""
        if self.audio.is_recording:
            self.hud_volume_signal.emit(vol)

    def _on_silence_timeout(self):
        """Auto-stop dictation when silence duration exceeds threshold."""
        print("[App] Silence timeout reached, auto-stopping dictation.")
        self._finish_dictation(inverted_enter=False)

    def toggle_dictation(self, inverted_enter: bool = False):
        """Toggles push-to-talk / toggle-to-talk recording."""
        if not self.audio.is_recording:
            self._start_dictation()
        else:
            self._finish_dictation(inverted_enter=inverted_enter)

    def _start_dictation(self):
        """Starts audio recording and displays HUD at caret position."""
        if self.audio.is_recording:
            return

        # Arm silence timeout
        self.audio.on_silence_timeout = self._on_silence_timeout

        # Capture target window handle right when dictation begins
        import ctypes
        self.target_hwnd = ctypes.windll.user32.GetForegroundWindow()

        # Find caret position
        cx, cy = get_caret_screen_position()
        self.hud_position_signal.emit(cx, cy)
        self.hud_state_signal.emit(HUDState.RECORDING)

        started = self.audio.start()
        if not started:
            self.hud_state_signal.emit(HUDState.IDLE)
            lang = self.config.get("interface_language", "ru")
            msg = "Не удалось открыть аудиоустройство записи." if lang == "ru" else "Could not open audio capture device."
            self.tray.show_notification("Dictatly", msg)
        else:
            self.hotkey_mgr.on_escape_pressed = self._cancel_dictation
            play_audio_cue("start", enabled=self.config.get("sound_effects_enabled", True))

    def _cancel_dictation(self):
        """Instantly cancels and discards the active dictation recording via Escape."""
        if not self.audio.is_recording:
            return
        print("[App] Dictation cancelled via Escape key.")
        self.hotkey_mgr.on_escape_pressed = None
        self.audio.stop()
        self.hud_state_signal.emit(HUDState.IDLE)
        play_audio_cue("stop", enabled=self.config.get("sound_effects_enabled", True))

    def _on_pause_hotkeys_toggled(self, paused: bool):
        """Pauses or resumes global hotkeys (for gaming, calls, etc.)."""
        if paused and self.audio.is_recording:
            self._cancel_dictation()
        self.hotkey_mgr.set_paused(paused)
        lang = self.config.get("interface_language", "ru")
        title = "Dictatly"
        msg = t("tray_hotkeys_paused" if paused else "tray_hotkeys_resumed", lang)
        self.tray.show_notification(title, msg)

    def _finish_dictation(self, inverted_enter: bool = False):
        """Stops recording, runs ASR, AI cleaning, and text injection."""
        if not self.audio.is_recording:
            return

        self.hotkey_mgr.on_escape_pressed = None
        play_audio_cue("stop", enabled=self.config.get("sound_effects_enabled", True))

        duration = self.audio.recording_duration
        audio_data = self.audio.stop()

        if audio_data is None:
            print(f"[App] Audio clip duration too short ({duration:.2f}s < 0.25s). Discarding.")
            self.hud_state_signal.emit(HUDState.IDLE)
            return

        print(f"[App] Audio recorded: {len(audio_data)} samples ({duration:.2f}s). Transcribing...")
        # Show transcribing spinner
        self.hud_state_signal.emit(HUDState.TRANSCRIBING)

        # Fail-safe watchdog: guarantee HUD resets to IDLE even if worker hangs or crashes
        watchdog = threading.Timer(20.0, lambda: self.hud_state_signal.emit(HUDState.IDLE))
        watchdog.daemon = True
        watchdog.start()

        # Determine Enter behavior
        default_enter = self.config["enter_after_insert"]
        press_enter = not default_enter if inverted_enter else default_enter

        # Resolve target window handle to guarantee focus when background worker completes
        import ctypes
        user32 = ctypes.windll.user32
        cur_fg = user32.GetForegroundWindow()
        hud_hwnd = self.hud_hwnd
        settings_hwnd = int(self.settings_window.winId()) if (self.settings_window and self.settings_window.isVisible()) else 0
        history_hwnd = int(self.history_window.winId()) if (self.history_window and self.history_window.isVisible()) else 0

        target_hwnd = self.target_hwnd
        if cur_fg and cur_fg not in (hud_hwnd, settings_hwnd, history_hwnd):
            target_hwnd = cur_fg

        def worker():
            try:
                # 1. Local ASR
                lang = self.config["dictation_language"]
                text = self.transcriber.transcribe_audio(audio_data, language=lang)
                if not text:
                    print("[App] Transcription produced no text.")
                    return

                print(f"[App] Recognized: {repr(text)}")

                # 2. Optional AI text cleanup
                if self.config["ai_cleanup_enabled"]:
                    api_key = decrypt_secret(self.config["ai_api_key_encrypted"])
                    if api_key:
                        cleaner = AICleaner(
                            base_url=self.config["ai_base_url"],
                            model=self.config["ai_model"],
                            api_key=api_key
                        )
                        text = cleaner.clean_text(text)
                        print(f"[App] After AI cleanup: {repr(text)}")

                # 3. Custom vocabulary & smart punctuation
                replacements = self.config.get("custom_replacements", {})
                text = apply_vocabulary(text, replacements)
                text = format_smart_punctuation(text, enabled=self.config.get("smart_punctuation_enabled", True))

                # 4. Text injection at cursor
                suffix = self.config["paste_suffix"]
                print(f"[App] Pasting text at active caret...")
                inject_text(text, suffix_mode=suffix, press_enter=press_enter, target_hwnd=target_hwnd)

                # 5. Save to history database
                self.db.add_entry(text, duration=duration, source="mic")

                # 6. Success state on HUD
                self.hud_state_signal.emit(HUDState.SUCCESS)
                time.sleep(0.24)
            except Exception as e:
                print(f"[App] Error in dictation worker: {e}")
            finally:
                watchdog.cancel()
                self.hud_state_signal.emit(HUDState.IDLE)

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def toggle_history(self):
        """Show or hide Quick History window."""
        if self.history_window is None:
            self.history_window = QuickHistoryWindow(self.db, self.config)
            self.history_window.batch_transcribe_requested.connect(self._start_batch_transcribe)

        if self.history_window.isVisible():
            self.history_window.hide()
        else:
            self.history_window.refresh_list()
            self.history_window.show()
            self.history_window.raise_()
            self.history_window.activateWindow()
            try:
                from .core.injector import force_foreground_window
                force_foreground_window(int(self.history_window.winId()))
            except Exception:
                pass

    @Slot()
    def show_settings(self):
        """Open Settings / Control Panel."""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.config, self.hotkey_mgr)
            self.settings_window.settings_saved.connect(self._on_settings_saved)
            self.settings_window.restart_service_requested.connect(self._on_restart_app_requested)
            self.settings_window.preview_hud_requested.connect(self._preview_hud)

        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
        try:
            from .core.injector import force_foreground_window
            force_foreground_window(int(self.settings_window.winId()))
        except Exception:
            pass

    def _preview_hud(self, size_mode: str):
        """Displays temporary HUD above settings window to preview size."""
        self.hud.set_mode_and_theme(size_mode=size_mode, theme="dark")
        if self.settings_window and self.settings_window.isVisible():
            geo = self.settings_window.geometry()
            cx = geo.center().x()
            cy = geo.top() - 10
            self.hud.move_to_caret(cx, cy)
        self.hud.set_volume(0.65)
        self.hud.set_state(HUDState.RECORDING)
        QTimer.singleShot(2500, lambda: self.hud.set_state(HUDState.IDLE))

    @Slot()
    def show_onboarding(self):
        """Show initial onboarding setup dialog."""
        if self.onboarding_dialog is None:
            self.onboarding_dialog = OnboardingDialog(self.config)
        self.onboarding_dialog.show()
        self.onboarding_dialog.raise_()
        self.onboarding_dialog.activateWindow()

    def _on_settings_saved(self):
        """Apply newly saved settings."""
        self.hud.set_mode_and_theme(
            size_mode=self.config["capsule_size"],
            theme="dark"
        )
        self.audio.set_device(
            self.config.get("microphone_device"),
            self.config.get("microphone_device_name")
        )
        self.audio.silence_timeout_seconds = float(self.config.get("silence_timeout_seconds", 0))
        self.tray.update_language()
        self._register_all_hotkeys()

        # Update model if changed
        if (self.transcriber.model_size != self.config["whisper_model"] or
            self.transcriber.device_pref != self.config["compute_device"]):
            self.transcriber.model_size = self.config["whisper_model"]
            self.transcriber.device_pref = self.config["compute_device"]
            self.transcriber._model = None
            threading.Thread(target=self.transcriber.load_model, daemon=True).start()

    def _on_restart_app_requested(self):
        """Handler for restart requested from Settings."""
        # Allow UI button to render 'Restarting...' state briefly, then launch replacement
        QTimer.singleShot(150, lambda: self.restart_app(reopen_settings=True))

    def _start_ipc_server(self):
        """Starts Windows Named Pipe server for single-instance CLI IPC."""
        from multiprocessing.connection import Listener
        def ipc_worker():
            pipe_name = r'\\.\pipe\Dictatly_IPC'
            print(f"[IPC] Initializing named pipe listener: {pipe_name}")
            while not getattr(self, "_is_shutting_down", False):
                try:
                    with Listener(pipe_name, 'AF_PIPE') as listener:
                        self._ipc_listener = listener
                        with listener.accept() as conn:
                            cmd = conn.recv()
                            print(f"[IPC] Received command: {cmd}")
                            if cmd == "shutdown" or getattr(self, "_is_shutting_down", False):
                                break
                            elif cmd == "settings":
                                self.open_settings_signal.emit()
                            elif cmd == "history":
                                self.open_history_signal.emit()
                except Exception as e:
                    if getattr(self, "_is_shutting_down", False):
                        break
                    print(f"[IPC] Listener error: {e}")
                    time.sleep(0.1)

        self._is_shutting_down = False
        self._ipc_listener = None
        t = threading.Thread(target=ipc_worker, daemon=True)
        t.start()

    def _stop_ipc_server(self):
        """Cleanly unblocks and terminates Named Pipe server."""
        self._is_shutting_down = True
        try:
            from multiprocessing.connection import Client
            with Client(r'\\.\pipe\Dictatly_IPC', 'AF_PIPE') as conn:
                conn.send("shutdown")
        except Exception:
            pass
        try:
            if hasattr(self, "_ipc_listener") and self._ipc_listener:
                self._ipc_listener.close()
                self._ipc_listener = None
        except Exception:
            pass

    def restart_app(self, reopen_settings: bool = True):
        """Cleanly terminates current process and launches a fresh Dictatly instance."""
        import subprocess
        from .core.autostart import get_pythonw_executable, get_project_root

        # 1. Stop active recording & keyboard hook
        try:
            if self.audio.is_recording:
                self.audio.stop()
            self.hotkey_mgr.stop()
        except Exception:
            pass

        # 2. Close IPC pipe and release single instance mutex so new instance doesn't collide
        self._stop_ipc_server()

        try:
            main_mod = sys.modules.get("__main__")
            if main_mod and hasattr(main_mod, "release_single_instance_mutex"):
                main_mod.release_single_instance_mutex()
            else:
                from main import release_single_instance_mutex
                release_single_instance_mutex()
        except Exception:
            pass

        # 3. Format launch command line
        root_dir = get_project_root()
        args = ["--restart"]
        if reopen_settings:
            args.append("--settings")

        if getattr(sys, "frozen", False):
            cmd = [sys.executable] + args
        else:
            py_exe = str(get_pythonw_executable())
            main_py = str(root_dir / "main.py")
            cmd = [py_exe, main_py] + args

        # 4. Launch new detached process
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(cmd, cwd=str(root_dir), creationflags=creation_flags)
        except Exception as e:
            print(f"[App] Failed to spawn restart process: {e}")

        # 5. Terminate current process
        QApplication.quit()
        sys.exit(0)

    def _restart_services(self):
        """Restarts hotkey hook and audio streams in-place."""
        def worker():
            try:
                # 1. Stop active recording if any and reset HUD
                if self.audio.is_recording:
                    self.audio.stop()
                self.hud_state_signal.emit(HUDState.IDLE)

                # 2. Reset and re-apply audio device
                self.audio.set_device(
                    self.config.get("microphone_device"),
                    self.config.get("microphone_device_name")
                )
                self.audio.silence_timeout_seconds = float(self.config.get("silence_timeout_seconds", 0))

                # 3. Stop and re-register global hotkey hook
                self.hotkey_mgr.stop()
                time.sleep(0.05)
                self._register_all_hotkeys()
                self.hotkey_mgr.start()

                # 4. Notify UI of successful restart
                if self.settings_window:
                    QTimer.singleShot(0, lambda: self.settings_window.notify_service_restarted(True))

                lang = self.config["interface_language"]
                msg = t("service_restarted", lang)
                QTimer.singleShot(0, lambda: self.tray.show_notification("Dictatly", msg))
            except Exception as e:
                print(f"[App] Error restarting services: {e}")
                if self.settings_window:
                    QTimer.singleShot(0, lambda: self.settings_window.notify_service_restarted(False, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _start_batch_transcribe(self, file_paths: List[str]):
        """Processes drag & dropped audio files."""
        if not file_paths or not self.history_window:
            return

        self.history_window.progress_bar.setVisible(True)
        self.history_window.progress_bar.setValue(0)
        lang = self.config["interface_language"]
        self.history_window.drop_zone.set_text(t("batch_processing", lang), "")

        export_dir = Path(self.config["export_folder"])
        export_dir.mkdir(parents=True, exist_ok=True)

        def worker():
            total = len(file_paths)
            for idx, fpath in enumerate(file_paths):
                path_obj = Path(fpath)
                
                def on_file_prog(prog: float):
                    self.batch_progress_signal.emit(idx + 1, total, prog)

                text = self.transcriber.transcribe_file(
                    fpath,
                    language=self.config["dictation_language"],
                    on_progress=on_file_prog
                )
                
                if text:
                    replacements = self.config.get("custom_replacements", {})
                    text = apply_vocabulary(text, replacements)
                    text = format_smart_punctuation(text, enabled=self.config.get("smart_punctuation_enabled", True))

                    # Save .txt file in export folder
                    out_txt = export_dir / f"{path_obj.stem}.txt"
                    try:
                        out_txt.write_text(text, encoding="utf-8")
                    except Exception as e:
                        print(f"[Batch] Error writing {out_txt}: {e}")

                    # Add to history
                    self.db.add_entry(text, duration=0.0, source="file")

            self.batch_finished_signal.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _on_batch_progress(self, current: int, total: int, prog: float):
        if self.history_window:
            percent = int(((current - 1 + prog) / total) * 100)
            self.history_window.progress_bar.setValue(percent)

    def _on_batch_finished(self):
        lang = self.config["interface_language"]
        if self.history_window:
            self.history_window.progress_bar.setVisible(False)
            sub_hint = t("batch_drop_sub_finished", lang)
            self.history_window.drop_zone.set_text(t("batch_import_hint", lang), sub_hint)
            self.history_window.refresh_list()
        self.tray.show_notification("Dictatly", t("batch_complete", lang))

    def exit_app(self):
        """Clean shutdown."""
        self._stop_ipc_server()
        try:
            main_mod = sys.modules.get("__main__")
            if main_mod and hasattr(main_mod, "release_single_instance_mutex"):
                main_mod.release_single_instance_mutex()
        except Exception:
            pass
        self.hotkey_mgr.stop()
        self.audio.stop()
        if hasattr(self, "db") and self.db:
            self.db.close()
        QApplication.quit()

# Backward-compatibility alias
SuperDictateApp = DictatlyApp
