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
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent, QHideEvent

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import tempfile

from src.config import AppConfig
from src.core.database import HistoryDatabase
from src.core.hotkey import GlobalHotkeyManager
from src.ui.hud import RecordingHUD, HUDState, CapsulePreviewCanvas
from src.ui.settings_window import SettingsWindow
from src.ui.history_window import QuickHistoryWindow, AppleNavButton
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
        from src.localization import t
        self.assertIn(t("service_restarted", win.config["interface_language"]), win.btn_restart.text())

    def test_history_window(self):
        cfg = AppConfig()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = HistoryDatabase(db_path=tmp_path)
            db.add_entry("Тестовая запись для проверки виджета продуктивности", duration=2.0, source="test")
            win = QuickHistoryWindow(db, cfg)
            win.refresh_list()
            self.assertIsNotNone(win)
            self.assertTrue(hasattr(win, "lbl_stats"))
            self.assertTrue(len(win.lbl_stats.text()) > 0)
            self.assertTrue("слов" in win.lbl_stats.text() or "words" in win.lbl_stats.text())

            # Test 3-tab Segmented Control structure and Stack
            self.assertTrue(hasattr(win, "segmented_ctrl"))
            self.assertEqual(len(win.segmented_ctrl.items), 3)
            self.assertEqual(win.stack.count(), 3)

            # Test Apple Navigation Buttons
            self.assertTrue(hasattr(win, "btn_prev"))
            self.assertTrue(hasattr(win, "btn_next"))
            self.assertIsInstance(win.btn_prev, AppleNavButton)
            self.assertIsInstance(win.btn_next, AppleNavButton)

            # Test dedicated Import Page (Page index 2)
            self.assertTrue(hasattr(win, "page_import"))
            self.assertTrue(hasattr(win, "btn_browse"))
            win.segmented_ctrl.set_current_index(2)
            self.assertEqual(win.stack.currentIndex(), 2)

            # Test drop zone methods in dedicated import page
            self.assertTrue(hasattr(win.drop_zone, "set_text"))
            self.assertTrue(hasattr(win.drop_zone, "setText"))
            win.drop_zone.set_text("Обработка файлов...", "Пожалуйста, подождите")
            self.assertEqual(win.drop_zone.lbl_icon.text(), "Обработка файлов...")
            win.drop_zone.setText("Новый статус")
            self.assertEqual(win.drop_zone.lbl_icon.text(), "Новый статус")

            # Test Segmented Tab Switch to Analytics (Page index 1)
            win.segmented_ctrl.set_current_index(1)
            self.assertEqual(win.stack.currentIndex(), 1)

            # Test Bento Metrics Cards exist and are populated with vector icons
            self.assertTrue(hasattr(win, "card_today"))
            self.assertTrue(hasattr(win, "card_saved"))
            self.assertTrue(hasattr(win, "card_speed"))
            self.assertTrue(hasattr(win, "card_total"))
            self.assertEqual(win.card_today.icon_name, "bolt")
            self.assertFalse(win.card_today.lbl_icon.pixmap().isNull())

            # Test Interactive Multi-Chart Hub (Volume, Speed, Sources)
            self.assertTrue(hasattr(win, "chart"))
            self.assertTrue(hasattr(win.chart, "start_animation"))
            self.assertEqual(win._active_chart_type, "volume")
            self.assertEqual(win.chart.mode, "volume")
            self.assertGreater(len(win.chart.volume_data), 0)

            # Test switching to Speed Spline Chart
            win.btn_chart_speed.click()
            self.assertEqual(win._active_chart_type, "speed")
            self.assertEqual(win.chart.mode, "speed")

            # Test switching to Sources Activity Rings Donut Chart
            win.btn_chart_sources.click()
            self.assertEqual(win._active_chart_type, "sources")
            self.assertEqual(win.chart.mode, "sources")

            # Switch back to Volume and test timeframe pills
            win.btn_chart_volume.click()
            self.assertEqual(win._active_chart_type, "volume")
            win.btn_chart_hourly.click()
            self.assertEqual(win._active_chart_range, "hourly")
            self.assertEqual(len(win.chart.volume_data), 24)
            win.btn_chart_7d.click()
            self.assertEqual(win._active_chart_range, "7d")
            self.assertEqual(len(win.chart.volume_data), 7)
            win.btn_chart_14d.click()
            self.assertEqual(win._active_chart_range, "14d")
            self.assertEqual(len(win.chart.volume_data), 14)

            # Switch back to Transcripts
            win.segmented_ctrl.set_current_index(0)
            self.assertEqual(win.stack.currentIndex(), 0)

            # Test Escape key dismissal
            win.show()
            self.assertTrue(win.isVisible())
            esc_ev = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
            win.keyPressEvent(esc_ev)
            self.assertFalse(win.isVisible())

            # Test hideEvent stops physics timers (0.0% CPU)
            win.hideEvent(QHideEvent())
            self.assertFalse(win.chart._anim_timer.isActive())
            self.assertFalse(win.segmented_ctrl._anim_timer.isActive())

            # Test db.close()
            db.close()
            self.assertIsNone(db.conn)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def test_svg_icon_manager(self):
        from src.ui.icons import SvgIconManager, get_svg_pixmap, get_svg_icon
        pix = get_svg_pixmap("bolt", 24, "#0A84FF")
        self.assertFalse(pix.isNull())
        self.assertEqual(pix.width() / pix.devicePixelRatio(), 24)
        self.assertEqual(pix.devicePixelRatio(), 2.0)
        icon = get_svg_icon("mic", 16)
        self.assertFalse(icon.isNull())

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

    def test_app_restart_contract(self):
        from src.app import DictatlyApp
        self.assertTrue(hasattr(DictatlyApp, "restart_app"))
        self.assertTrue(hasattr(DictatlyApp, "_restart_services"))
        self.assertTrue(hasattr(DictatlyApp, "_on_restart_app_requested"))

if __name__ == "__main__":
    unittest.main()
