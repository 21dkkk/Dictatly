"""
Self-test suite for SuperDictate Windows components.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import AppConfig, DEFAULT_CONFIG
from src.localization import t
from src.core.database import HistoryDatabase
from src.core.security import encrypt_secret, decrypt_secret
from src.core.caret import get_caret_screen_position
from src.core.hotkey import key_combo_to_display, normalize_key_string
from src.core.audio import AudioRecorder

class TestSuperDictate(unittest.TestCase):
    def test_config(self):
        cfg = AppConfig()
        self.assertIsNotNone(cfg["hotkey_main"])
        self.assertIn(cfg.get("interface_language"), ("ru", "en"))

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
        db = HistoryDatabase()
        entry_id = db.add_entry("Тестовая транскрипция SuperDictate", duration=2.5, source="test")
        self.assertTrue(entry_id > 0)
        entries = db.get_entries(page=1, page_size=5)
        self.assertTrue(len(entries) > 0)
        self.assertEqual(entries[0]["text"], "Тестовая транскрипция SuperDictate")
        db.delete_entry(entry_id)

    def test_caret_tracker(self):
        x, y = get_caret_screen_position()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)

    def test_hotkey_formatting(self):
        combo = "VK_RSHIFT+VK_RCONTROL"
        disp = key_combo_to_display(combo)
        self.assertIn("Right", disp)

    def test_audio_devices(self):
        devs = AudioRecorder.get_input_devices()
        self.assertIsInstance(devs, list)

if __name__ == "__main__":
    unittest.main()
