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

MAX_HISTORY_ENTRIES = 500
PAGE_SIZE = 5

class HistoryDatabase:
    def __init__(self, db_path: Optional[Any] = None):
        self._lock = threading.Lock()
        if db_path is None:
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
            if not self.conn:
                return -1
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
            if not self.conn:
                return []
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
            if not self.conn:
                return 0
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

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Compute comprehensive dictation productivity metrics."""
        today_prefix = datetime.date.today().isoformat()
        with self._lock:
            # Today stats
            cur_today = self.conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(word_count), 0), COALESCE(SUM(duration), 0.0)
                FROM transcripts
                WHERE created_at LIKE ?
            """, (f"{today_prefix}%",))
            row_today = cur_today.fetchone()
            today_count = row_today[0] if row_today else 0
            today_words = row_today[1] if row_today else 0
            today_duration = row_today[2] if row_today else 0.0

            # All-time stats
            cur_all = self.conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(word_count), 0), COALESCE(SUM(duration), 0.0)
                FROM transcripts
            """)
            row_all = cur_all.fetchone()
            total_count = row_all[0] if row_all else 0
            total_words = row_all[1] if row_all else 0
            total_duration = row_all[2] if row_all else 0.0

        today_minutes_saved = round(today_words / 40.0, 1)
        total_minutes_saved = round(total_words / 40.0, 1)

        # Average words per minute (WPM)
        if total_duration >= 5.0 and total_words > 0:
            avg_wpm = int(round((total_words / total_duration) * 60.0))
        elif today_duration >= 3.0 and today_words > 0:
            avg_wpm = int(round((today_words / today_duration) * 60.0))
        else:
            avg_wpm = 145  # Standard baseline speaking rate

        # Multiplier vs average typing speed (40 wpm)
        speed_multiplier = round(max(1.0, avg_wpm / 40.0), 1)

        return {
            "today_words": today_words,
            "today_count": today_count,
            "today_minutes_saved": today_minutes_saved,
            "today_duration": round(today_duration, 1),
            "total_words": total_words,
            "total_count": total_count,
            "total_duration": round(total_duration, 1),
            "total_minutes_saved": total_minutes_saved,
            "avg_wpm": avg_wpm,
            "speed_multiplier": speed_multiplier,
        }

    def get_daily_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """Return daily activity for the last N days up to today, filling gaps with zeros."""
        today = datetime.date.today()
        dates = [today - datetime.timedelta(days=i) for i in range(days - 1, -1, -1)]
        start_date_str = dates[0].isoformat()

        daily_map: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            cur = self.conn.execute("""
                SELECT 
                    substr(created_at, 1, 10) as day_date,
                    COUNT(*) as cnt,
                    COALESCE(SUM(word_count), 0) as total_words,
                    COALESCE(SUM(duration), 0.0) as total_duration
                FROM transcripts
                WHERE substr(created_at, 1, 10) >= ?
                GROUP BY day_date
            """, (start_date_str,))
            for row in cur.fetchall():
                daily_map[row["day_date"]] = {
                    "count": row["cnt"],
                    "words": row["total_words"],
                    "duration": row["total_duration"]
                }

        ru_day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        en_day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        result = []
        for d in dates:
            d_str = d.isoformat()
            weekday_idx = d.weekday()
            data = daily_map.get(d_str, {"count": 0, "words": 0, "duration": 0.0})
            words = data["words"]
            result.append({
                "date": d_str,
                "short_date": d.strftime("%d.%m"),
                "day_ru": ru_day_names[weekday_idx],
                "day_en": en_day_names[weekday_idx],
                "words": words,
                "count": data["count"],
                "duration": round(data["duration"], 1),
                "minutes_saved": round(words / 40.0, 1),
                "is_today": (d == today)
            })
        return result

    def get_hourly_activity(self) -> List[Dict[str, Any]]:
        """Return hourly activity distribution for today (24 hours: 00..23)."""
        today_prefix = datetime.date.today().isoformat()
        hourly_map: Dict[int, Dict[str, Any]] = {}

        with self._lock:
            cur = self.conn.execute("""
                SELECT 
                    CAST(substr(created_at, 12, 2) AS INTEGER) as hr,
                    COUNT(*) as cnt,
                    COALESCE(SUM(word_count), 0) as total_words
                FROM transcripts
                WHERE created_at LIKE ?
                GROUP BY hr
            """, (f"{today_prefix}%",))
            for row in cur.fetchall():
                hourly_map[row["hr"]] = {
                    "count": row["cnt"],
                    "words": row["total_words"]
                }

        result = []
        for hr in range(24):
            data = hourly_map.get(hr, {"count": 0, "words": 0})
            result.append({
                "hour": hr,
                "hour_label": f"{hr:02d}:00",
                "words": data["words"],
                "count": data["count"]
            })
        return result

    def get_source_distribution(self) -> Dict[str, Any]:
        """Return proportion of microphone vs file imports."""
        with self._lock:
            cur = self.conn.execute("""
                SELECT source, COUNT(*) as cnt, COALESCE(SUM(word_count), 0) as total_words
                FROM transcripts
                GROUP BY source
            """)
            rows = cur.fetchall()

        mic_count = 0
        mic_words = 0
        file_count = 0
        file_words = 0

        for r in rows:
            src = str(r["source"]).lower()
            if src == "file":
                file_count += r["cnt"]
                file_words += r["total_words"]
            else:
                mic_count += r["cnt"]
                mic_words += r["total_words"]

        total_cnt = max(1, mic_count + file_count)
        total_w = max(1, mic_words + file_words)
        return {
            "mic_count": mic_count,
            "mic_words": mic_words,
            "mic_percent": round((mic_count / total_cnt) * 100.0, 1),
            "mic_words_percent": round((mic_words / total_w) * 100.0, 1),
            "file_count": file_count,
            "file_words": file_words,
            "file_percent": round((file_count / total_cnt) * 100.0, 1),
            "file_words_percent": round((file_words / total_w) * 100.0, 1),
        }

    def get_speed_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Return speaking pace (WPM) trend across the last N days."""
        today = datetime.date.today()
        dates = [today - datetime.timedelta(days=i) for i in range(days - 1, -1, -1)]
        start_date_str = dates[0].isoformat()

        daily_map: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            cur = self.conn.execute("""
                SELECT 
                    substr(created_at, 1, 10) as day_date,
                    COALESCE(SUM(word_count), 0) as total_words,
                    COALESCE(SUM(duration), 0.0) as total_duration
                FROM transcripts
                WHERE substr(created_at, 1, 10) >= ?
                GROUP BY day_date
            """, (start_date_str,))
            for row in cur.fetchall():
                words = row["total_words"]
                dur = row["total_duration"]
                wpm = int(round((words / dur) * 60.0)) if dur >= 3.0 and words > 0 else 145
                daily_map[row["day_date"]] = {"wpm": wpm, "words": words}

        ru_day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        en_day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        result = []
        for d in dates:
            d_str = d.isoformat()
            weekday_idx = d.weekday()
            data = daily_map.get(d_str, {"wpm": 0, "words": 0})
            result.append({
                "date": d_str,
                "short_date": d.strftime("%d.%m"),
                "day_ru": ru_day_names[weekday_idx],
                "day_en": en_day_names[weekday_idx],
                "wpm": data["wpm"],
                "words": data["words"],
                "is_today": (d == today)
            })
        return result

    def close(self):
        """Cleanly close SQLite connection and release WAL locks."""
        with self._lock:
            if hasattr(self, "conn") and self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None



