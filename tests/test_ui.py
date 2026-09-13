"""
UI verification test for PySide6 widgets (Settings, History, HUD).
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure headless operation for CI runners
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import AppConfig
from src.core.database import HistoryDatabase
from src.core.hotkey import GlobalHotkeyManager
from src.ui.hud import RecordingHUD, HUDState, CapsulePreviewCanvas
from src.ui.settings_window import SettingsWindow
from src.ui.history_window import QuickHistoryWindow
from src.ui.onboarding_dialog import OnboardingDialog
from src.ui.tray import SystemTrayManager

class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_hud_widget(self):
        hud = RecordingHUD(size_mode="medium", theme="dark")
        self.assertEqual(hud.capsule_w, 96)
        self.assertEqual(hud.capsule_h, 40)

        # Test mode change
        hud.set_mode_and_theme(size_mode="large")
        self.assertEqual(hud.capsule_w, 124)
        self.assertEqual(hud.capsule_h, 48)

        hud.set_mode_and_theme(size_mode="small")
        self.assertEqual(hud.capsule_w, 74)
        self.assertEqual(hud.capsule_h, 32)

        hud.set_state(HUDState.RECORDING)
        hud.set_volume(0.5)
        hud.move_to_caret(500, 500)
        hud.set_state(HUDState.TRANSCRIBING)
        hud.set_state(HUDState.SUCCESS)
        hud.set_state(HUDState.IDLE)

        # Test preview canvas
        preview = CapsulePreviewCanvas(size_mode="medium")
        preview.set_size_mode("large")
        self.assertEqual(preview.size_mode, "large")

    def test_settings_window(self):
        cfg = AppConfig()
        mgr = GlobalHotkeyManager()
        win = SettingsWindow(cfg, mgr)
        self.assertIsNotNone(win)

        # Test autostart elements exist
        self.assertTrue(hasattr(win, "chk_autostart"))
        self.assertTrue(hasattr(win, "btn_shortcuts"))

        # Test theme combo removed (dark theme exclusively)
        self.assertFalse(hasattr(win, "combo_theme"))

        # Test HUD size controls and live preview canvas exist
        self.assertTrue(hasattr(win, "combo_size"))
        self.assertTrue(hasattr(win, "preview_canvas"))
        self.assertTrue(hasattr(win, "btn_test_hud"))

        # Test size change updates preview canvas
        win.combo_size.setCurrentIndex(win.combo_size.findData("large"))
        self.assertEqual(win.preview_canvas.size_mode, "large")

        # Test test HUD button signal emission
        emitted_sizes = []
        win.preview_hud_requested.connect(lambda s: emitted_sizes.append(s))
        win.btn_test_hud.click()
        self.assertEqual(emitted_sizes, ["large"])

        # Test productivity controls exist
        self.assertTrue(hasattr(win, "combo_rec_mode"))
        self.assertTrue(hasattr(win, "chk_sound"))
        self.assertTrue(hasattr(win, "chk_smart_punct"))
        self.assertTrue(hasattr(win, "combo_silence"))
        self.assertTrue(hasattr(win, "txt_vocab"))
        self.assertEqual(win.txt_vocab.toPlainText(), "")
        self.assertIn("GitHub", win.txt_vocab.placeholderText())

        # Test Live Mic VU-meter
        self.assertTrue(hasattr(win, "meter_mic"))
        self.assertTrue(hasattr(win, "lbl_mic_test"))
        win.meter_mic.set_level(0.8)
        win.meter_mic.reset()

        # Test restart button state flow
        restart_emitted = []
        win.restart_service_requested.connect(lambda: restart_emitted.append(True))
        win.btn_restart.click()
        self.assertTrue(restart_emitted)
        self.assertFalse(win.btn_restart.isEnabled())

        # Test notification update
        win.notify_service_restarted(True)
        self.assertIn("✓", win.btn_restart.text())

    def test_history_window(self):
        cfg = AppConfig()
        db = HistoryDatabase()
        db.add_entry("Тестовая запись для проверки виджета продуктивности", duration=2.0, source="test")
        win = QuickHistoryWindow(db, cfg)
        win.refresh_list()
        self.assertIsNotNone(win)
        self.assertTrue(hasattr(win, "lbl_stats"))
        self.assertIn("⚡", win.lbl_stats.text())

        # Test drop zone methods (must not throw AttributeError)
        self.assertTrue(hasattr(win.drop_zone, "set_text"))
        self.assertTrue(hasattr(win.drop_zone, "setText"))
        win.drop_zone.set_text("Обработка файлов...", "Пожалуйста, подождите")
        self.assertEqual(win.drop_zone.lbl_icon.text(), "Обработка файлов...")
        win.drop_zone.setText("Новый статус")
        self.assertEqual(win.drop_zone.lbl_icon.text(), "Новый статус")

    def test_onboarding_dialog(self):
        cfg = AppConfig()
        dlg = OnboardingDialog(cfg)
        self.assertIsNotNone(dlg)
        self.assertTrue(dlg.chk_autostart.isChecked())
        self.assertTrue(dlg.chk_shortcuts.isChecked())

    def test_tray_manager(self):
        cfg = AppConfig()
        tray = SystemTrayManager(cfg)
        self.assertTrue(hasattr(tray, "act_pause"))
        self.assertFalse(tray.act_pause.isChecked())

        # Test toggling pause
        emitted_pause = []
        tray.toggle_pause_requested.connect(lambda p: emitted_pause.append(p))
        tray.act_pause.setChecked(True)
        self.assertEqual(emitted_pause, [True])

        tray.set_paused(False)
        self.assertFalse(tray.act_pause.isChecked())

if __name__ == "__main__":
    unittest.main()
