"""Local SQLite storage for activity samples, wins and unlocked achievements."""

import sqlite3
import time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    duration REAL NOT NULL,
    app TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);

CREATE TABLE IF NOT EXISTS wins (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    text TEXT NOT NULL,
    impact TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_wins_ts ON wins(ts);

CREATE TABLE IF NOT EXISTS unlocks (
    key TEXT PRIMARY KEY,
    achievement_id TEXT NOT NULL,
    period_key TEXT NOT NULL,
    day TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    unlocked_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class DB:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(str(path), timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    # --- activity -----------------------------------------------------------

    def add_sample(self, ts: float, duration: float, app: str, title: str):
        self.add_samples([(ts, duration, app, title)])

    def add_samples(self, rows: Iterable[Tuple[float, float, str, str]]):
        with self.conn:
            self.conn.executemany(
                "INSERT INTO samples (ts, duration, app, title) VALUES (?, ?, ?, ?)", rows)

    def samples_between(self, start: float, end: float) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT ts, duration, app, title FROM samples WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start, end)).fetchall()

    def total_seconds(self) -> float:
        return self.conn.execute("SELECT COALESCE(SUM(duration), 0) FROM samples").fetchone()[0]

    def first_sample_ts(self) -> Optional[float]:
        return self.conn.execute("SELECT MIN(ts) FROM samples").fetchone()[0]

    def last_sample_ts(self) -> Optional[float]:
        return self.conn.execute("SELECT MAX(ts) FROM samples").fetchone()[0]

    def delete_samples_since(self, ts: float) -> int:
        with self.conn:
            return self.conn.execute("DELETE FROM samples WHERE ts >= ?", (ts,)).rowcount

    # --- wins ---------------------------------------------------------------

    def add_win(self, text: str, impact: str = "", tags: str = "", ts: Optional[float] = None) -> int:
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO wins (ts, text, impact, tags) VALUES (?, ?, ?, ?)",
                (ts if ts is not None else time.time(), text, impact, tags))
            return cur.lastrowid

    def wins_between(self, start: float, end: float) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id, ts, text, impact, tags FROM wins WHERE ts >= ? AND ts < ? ORDER BY ts",
            (start, end)).fetchall()

    def win_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM wins").fetchone()[0]

    def delete_win(self, win_id: int) -> bool:
        with self.conn:
            return self.conn.execute("DELETE FROM wins WHERE id = ?", (win_id,)).rowcount > 0

    # --- achievements -------------------------------------------------------

    def add_unlock(self, achievement_id: str, period_key: str, day: str, detail: str) -> bool:
        """Record an unlock. Returns True only the first time this one is earned."""
        with self.conn:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO unlocks (key, achievement_id, period_key, day, detail, unlocked_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (f"{achievement_id}:{period_key}", achievement_id, period_key, day, detail, time.time()))
            return cur.rowcount > 0

    def unlocks_between(self, first_day: str, last_day: str) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT achievement_id, period_key, day, detail FROM unlocks"
            " WHERE day >= ? AND day <= ? ORDER BY day",
            (first_day, last_day)).fetchall()

    def all_unlocks(self) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT achievement_id, period_key, day, detail FROM unlocks ORDER BY day").fetchall()

    # --- meta ---------------------------------------------------------------

    def get_meta(self, key: str) -> Optional[str]:
        row = self.conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
