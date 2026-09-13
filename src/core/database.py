"""
SQLite history storage for Dictatly Windows.
Stores up to 100 recent transcriptions with pagination (5 items per page).
"""

import sqlite3
import datetime
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..config import get_app_data_dir

MAX_HISTORY_ENTRIES = 100
PAGE_SIZE = 5

class HistoryDatabase:
    def __init__(self):
        self._lock = threading.Lock()
        db_path = get_app_data_dir() / "history.db"
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            with self.conn:
                self.conn.execute("PRAGMA journal_mode = WAL;")
                self.conn.execute("PRAGMA synchronous = NORMAL;")
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS transcripts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        text TEXT NOT NULL,
                        duration REAL DEFAULT 0.0,
                        word_count INTEGER DEFAULT 0,
                        source TEXT DEFAULT 'mic'
                    )
                """)
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_created ON transcripts(created_at DESC)")

    def add_entry(self, text: str, duration: float = 0.0, source: str = "mic") -> int:
        """Add new transcript entry and prune older entries beyond MAX_HISTORY_ENTRIES."""
        text = text.strip()
        if not text:
            return -1
        words = len(text.split())
        with self._lock:
            with self.conn:
                cur = self.conn.execute("""
                    INSERT INTO transcripts (created_at, text, duration, word_count, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (datetime.datetime.now().isoformat(), text, duration, words, source))
                new_id = cur.lastrowid

                # Prune beyond MAX_HISTORY_ENTRIES
                self.conn.execute("""
                    DELETE FROM transcripts WHERE id NOT IN (
                        SELECT id FROM transcripts ORDER BY id DESC LIMIT ?
                    )
                """, (MAX_HISTORY_ENTRIES,))
                return new_id

    def get_entries(self, page: int = 1, page_size: int = PAGE_SIZE, search_query: str = "") -> List[Dict[str, Any]]:
        """Fetch paginated entries."""
        offset = max(0, (page - 1) * page_size)
        with self._lock:
            if search_query.strip():
                query = """
                    SELECT * FROM transcripts 
                    WHERE text LIKE ? 
                    ORDER BY id DESC 
                    LIMIT ? OFFSET ?
                """
                params = (f"%{search_query.strip()}%", page_size, offset)
            else:
                query = """
                    SELECT * FROM transcripts 
                    ORDER BY id DESC 
                    LIMIT ? OFFSET ?
                """
                params = (page_size, offset)
                
            cur = self.conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_total_count(self, search_query: str = "") -> int:
        """Return total count of transcripts."""
        with self._lock:
            if search_query.strip():
                cur = self.conn.execute("SELECT COUNT(*) FROM transcripts WHERE text LIKE ?", (f"%{search_query.strip()}%",))
            else:
                cur = self.conn.execute("SELECT COUNT(*) FROM transcripts")
            return cur.fetchone()[0]

    def delete_entry(self, entry_id: int):
        with self._lock:
            with self.conn:
                self.conn.execute("DELETE FROM transcripts WHERE id = ?", (entry_id,))

    def clear_all(self):
        with self._lock:
            with self.conn:
                self.conn.execute("DELETE FROM transcripts")

    def get_today_stats(self) -> Dict[str, Any]:
        """Compute total dictation count, words and estimated typing minutes saved for today."""
        today_prefix = datetime.date.today().isoformat()
        with self._lock:
            cur = self.conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(word_count), 0)
                FROM transcripts
                WHERE created_at LIKE ?
            """, (f"{today_prefix}%",))
            row = cur.fetchone()
            count = row[0] if row else 0
            words = row[1] if row else 0
            minutes_saved = round(words / 40.0, 1)
            return {
                "count": count,
                "words": words,
                "minutes_saved": minutes_saved
            }
