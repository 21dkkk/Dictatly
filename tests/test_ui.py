"""
UI verification test for PySide6 widgets (Settings, History, HUD).
"""

import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import AppConfig
from src.core.database import HistoryDatabase
from src.core.hotkey import GlobalHotkeyManager
from src.ui.hud import RecordingHUD, HUDState
from src.ui.settings_window import SettingsWindow
from src.ui.history_window import QuickHistoryWindow

class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_hud_widget(self):
        hud = RecordingHUD(size_mode="medium", theme="dark")
        hud.set_state(HUDState.RECORDING)
        hud.set_volume(0.5)
        hud.move_to_caret(500, 500)
        hud.set_state(HUDState.TRANSCRIBING)
        hud.set_state(HUDState.SUCCESS)
        hud.set_state(HUDState.IDLE)

    def test_settings_window(self):
        cfg = AppConfig()
        mgr = GlobalHotkeyManager()
        win = SettingsWindow(cfg, mgr)
        self.assertIsNotNone(win)

    def test_history_window(self):
        cfg = AppConfig()
        db = HistoryDatabase()
        win = QuickHistoryWindow(db, cfg)
        win.refresh_list()
        self.assertIsNotNone(win)

if __name__ == "__main__":
    unittest.main()
