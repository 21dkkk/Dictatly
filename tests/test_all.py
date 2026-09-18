"""
Self-test suite for Dictatly Windows components.
"""

import os
import sys
import unittest
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import AppConfig, DEFAULT_CONFIG
from src.localization import t
from src.core.database import HistoryDatabase
from src.core.security import encrypt_secret, decrypt_secret
from src.core.caret import get_caret_screen_position
from src.core.hotkey import key_combo_to_display, normalize_key_string, GlobalHotkeyManager
from src.core.audio import AudioRecorder
from src.core.autostart import get_launch_command, get_pythonw_executable, is_autostart_enabled
from src.core.sound import play_audio_cue
from src.core.text_postprocess import apply_vocabulary, format_smart_punctuation

class TestDictatly(unittest.TestCase):
    def test_config(self):
        cfg = AppConfig()
        self.assertIsNotNone(cfg["hotkey_main"])
        self.assertIn(cfg.get("interface_language"), ("ru", "en"))
        self.assertIn(cfg.get("recording_mode"), ("toggle", "push_to_talk"))
        self.assertIn("custom_replacements", cfg)

    def test_localization(self):
        ru_text = t("service_running", "ru")
        en_text = t("service_running", "en")
        self.assertEqual(ru_text, "Работает")
        self.assertEqual(en_text, "Running")

    def test_security_dpapi(self):
        sample_key = "gsk_test_api_key_1234567890"
        encrypted = encrypt_secret(sample_key)
        self.assertTrue(len(encrypted) > 0)
        decrypted = decrypt_secret(encrypted)
        self.assertEqual(sample_key, decrypted)

    def test_database(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            db = HistoryDatabase(db_path=tmp_path)
            entry_id = db.add_entry("Тестовая транскрипция Dictatly", duration=2.5, source="test")
            self.assertTrue(entry_id > 0)
            entries = db.get_entries(page=1, page_size=5)
            self.assertTrue(len(entries) > 0)
            self.assertEqual(entries[0]["text"], "Тестовая транскрипция Dictatly")

            # Test rich analytics methods
            summary = db.get_analytics_summary()
            self.assertIn("today_words", summary)
            self.assertIn("today_minutes_saved", summary)
            self.assertIn("avg_wpm", summary)
            self.assertIn("speed_multiplier", summary)
            self.assertGreaterEqual(summary["today_words"], 3)

            daily = db.get_daily_activity(7)
            self.assertEqual(len(daily), 7)
            self.assertTrue(daily[-1]["is_today"])
            self.assertIn("day_ru", daily[0])
            self.assertIn("day_en", daily[0])

            hourly = db.get_hourly_activity()
            self.assertEqual(len(hourly), 24)
            self.assertEqual(hourly[0]["hour"], 0)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def test_caret_tracker(self):
        x, y = get_caret_screen_position()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)

    def test_hotkey_formatting(self):
        combo = "VK_RSHIFT+VK_RCONTROL"
        disp = key_combo_to_display(combo)
        self.assertIn("Right", disp)

    def test_hotkey_handlers_registration(self):
        mgr = GlobalHotkeyManager()
        called = []
        mgr.register_hotkey_handlers("VK_RCONTROL", on_press=lambda: called.append("press"), on_release=lambda: called.append("release"))
        self.assertIn("VK_RCONTROL", mgr._hotkey_press_callbacks)
        self.assertIn("VK_RCONTROL", mgr._hotkey_release_callbacks)
        mgr.clear_hotkeys()
        self.assertEqual(len(mgr._hotkey_press_callbacks), 0)

    def test_audio_devices(self):
        devs = AudioRecorder.get_input_devices()
        self.assertIsInstance(devs, list)
        names = [d["name"].strip().lower() for d in devs]
        self.assertEqual(len(names), len(set(names)), "Input devices list must not contain duplicates")
        for name in names:
            self.assertNotIn("sound mapper", name)
            self.assertNotIn("переназначение звуковых", name)
            self.assertNotIn("primary sound capture", name)
            self.assertNotIn("первичный драйвер записи", name)

    def test_audio_extra_settings(self):
        # Should execute safely for default and specific devices
        settings_none = AudioRecorder.get_extra_settings(None)
        settings_invalid = AudioRecorder.get_extra_settings(-999)
        self.assertIsNone(settings_invalid)

    def test_audio_silence_timeout_config(self):
        rec = AudioRecorder(silence_timeout_seconds=10.0)
        self.assertEqual(rec.silence_timeout_seconds, 10.0)
        self.assertFalse(rec.is_recording)

    def test_autostart_module(self):
        pythonw = get_pythonw_executable()
        self.assertTrue(pythonw.name.lower().startswith("python"))
        cmd = get_launch_command()
        self.assertTrue("Dictatly.exe" in cmd or "main.py" in cmd)
        status = is_autostart_enabled()
        self.assertIsInstance(status, bool)

    def test_text_postprocess_vocabulary(self):
        replacements = {
            "гитхаб": "GitHub",
            "пайтон": "Python",
            "вс код": "VS Code"
        }
        res = apply_vocabulary("Я написал код на пайтон и залил на гитхаб через вс код.", replacements)
        self.assertEqual(res, "Я написал код на Python и залил на GitHub через VS Code.")

        # Non-destructive test
        res_empty = apply_vocabulary("Простой текст", {})
        self.assertEqual(res_empty, "Простой текст")

    def test_text_postprocess_smart_punctuation(self):
        raw = "   привет ,   мир !  как дела ? "
        res = format_smart_punctuation(raw, enabled=True)
        self.assertEqual(res, "Привет, мир! Как дела?")

        res_disabled = format_smart_punctuation("  привет  мир  ", enabled=False)
        self.assertEqual(res_disabled, "привет мир")

        # Decimal numbers, times, and domains must be preserved intact without spaces
        technical_raw = "версия 3.14 в 12:30, вес 1,5 кг, сайт google.com.конец.новое"
        res_tech = format_smart_punctuation(technical_raw, enabled=True)
        self.assertIn("3.14", res_tech)
        self.assertIn("12:30", res_tech)
        self.assertIn("1,5", res_tech)
        self.assertIn("google.com", res_tech)
        self.assertIn("Конец. Новое", res_tech)

    def test_database_concurrent_access(self):
        """Stress test SQLite database thread safety with concurrent readers and writers."""
        import threading
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = HistoryDatabase(tmp_path)
            errors = []

            def writer(worker_id: int):
                try:
                    for i in range(10):
                        db.add_entry(f"Concurrent transcript worker {worker_id} iter {i}", duration=1.0)
                except Exception as e:
                    errors.append(f"Writer error: {e}")

            def reader():
                try:
                    for _ in range(10):
                        db.get_entries(page=1, page_size=5)
                        db.get_today_stats()
                        db.get_total_count()
                except Exception as e:
                    errors.append(f"Reader error: {e}")

            threads = []
            for i in range(4):
                threads.append(threading.Thread(target=writer, args=(i,)))
                threads.append(threading.Thread(target=reader))

            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(len(errors), 0, f"Concurrent database access caused errors: {errors}")
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def test_audio_cue(self):
        # Disabled cue should return False immediately
        res_disabled = play_audio_cue("start", enabled=False)
        self.assertFalse(res_disabled)

        # Enabled cue should queue and return True
        res_start = play_audio_cue("start", enabled=True)
        res_stop = play_audio_cue("stop", enabled=True)
        self.assertTrue(res_start)
        self.assertTrue(res_stop)

    def test_database_today_stats(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            db = HistoryDatabase(db_path=tmp_path)
            db.add_entry("Тестирование подсчета слов и продуктивности в быстрой истории", duration=3.0, source="test")
            stats = db.get_today_stats()
            self.assertIsInstance(stats, dict)
            self.assertIn("words", stats)
            self.assertIn("minutes_saved", stats)
            self.assertGreaterEqual(stats["words"], 7)
            self.assertGreaterEqual(stats["count"], 1)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def test_hotkey_pause_and_escape(self):
        mgr = GlobalHotkeyManager()
        self.assertFalse(mgr.is_paused)
        mgr.set_paused(True)
        self.assertTrue(mgr.is_paused)
        mgr.set_paused(False)
        self.assertFalse(mgr.is_paused)

        escaped = []
        mgr.on_escape_pressed = lambda: escaped.append(True)
        self.assertIsNotNone(mgr.on_escape_pressed)
        mgr.on_escape_pressed()
        self.assertEqual(escaped, [True])

if __name__ == "__main__":
    unittest.main()
