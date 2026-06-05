"""Persistent SQLite cache for vacancy data.

Hierarchy:
  L1 — in-memory dict (app.py, TTL=300s, lost on restart)
  L2 — SQLite file    (this module, survives restarts)

Usage:
  cache = VacancyCache()
  cache.get(key)           → list | None  (only if fresh, TTL=300s)
  cache.get_stale(key)     → list | None  (any age — fallback when offline)
  cache.set(key, data)     → None
  cache.info()             → dict         (stats)
"""

import json
import sqlite3
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("hhanalyst.cache")

DB_PATH = Path(__file__).parent.parent / "data" / "vacancies.db"
FRESH_TTL = 300      # seconds — treat as "current" data
STALE_TTL = 7 * 24 * 3600  # 7 days — keep for offline fallback


class VacancyCache:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vacancy_cache (
                    key        TEXT PRIMARY KEY,
                    query      TEXT NOT NULL,
                    area       TEXT NOT NULL DEFAULT '',
                    max_pages  INTEGER NOT NULL DEFAULT 3,
                    data       TEXT NOT NULL,
                    fetched_at REAL NOT NULL,
                    count      INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_fetched ON vacancy_cache(fetched_at)"
            )
            conn.commit()

    # ── Public API ────────────────────────────────────────────────

    def get(self, key: str) -> Optional[list]:
        """Return cached data only if fresh (within FRESH_TTL)."""
        row = self._fetch_row(key)
        if row is None:
            return None
        age = time.time() - row["fetched_at"]
        if age > FRESH_TTL:
            logger.debug("Cache stale (%.0fs old): %s", age, key)
            return None
        logger.debug("Cache hit (%.0fs old): %s", age, key)
        return json.loads(row["data"])

    def get_stale(self, key: str) -> Optional[list]:
        """Return cached data regardless of age (offline fallback)."""
        row = self._fetch_row(key)
        if row is None:
            return None
        age = time.time() - row["fetched_at"]
        if age > STALE_TTL:
            return None
        logger.info("Using stale cache (%.0fh old) for offline fallback: %s",
                    age / 3600, key)
        return json.loads(row["data"])

    def set(self, key: str, query: str, area: str, max_pages: int, data: list):
        """Save or update cached data."""
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT INTO vacancy_cache (key, query, area, max_pages, data, fetched_at, count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        data       = excluded.data,
                        fetched_at = excluded.fetched_at,
                        count      = excluded.count
                """, (key, query, area, max_pages,
                      json.dumps(data, ensure_ascii=False),
                      time.time(), len(data)))
                conn.commit()
            logger.debug("Cached %d vacancies for key: %s", len(data), key)
        except sqlite3.Error as e:
            logger.warning("Cache write failed: %s", e)

    def info(self) -> dict:
        """Return cache statistics."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT key, query, area, count, fetched_at FROM vacancy_cache "
                    "ORDER BY fetched_at DESC"
                ).fetchall()
            now = time.time()
            return {
                "total_entries": len(rows),
                "entries": [
                    {
                        "key": r["key"],
                        "query": r["query"],
                        "area": r["area"],
                        "count": r["count"],
                        "age_seconds": int(now - r["fetched_at"]),
                        "fresh": (now - r["fetched_at"]) < FRESH_TTL,
                    }
                    for r in rows
                ],
            }
        except sqlite3.Error:
            return {"total_entries": 0, "entries": []}

    def clear(self):
        """Delete all cached entries."""
        with self._connect() as conn:
            conn.execute("DELETE FROM vacancy_cache")
            conn.commit()

    # ── Internal ──────────────────────────────────────────────────

    def _fetch_row(self, key: str) -> Optional[sqlite3.Row]:
        try:
            with self._connect() as conn:
                return conn.execute(
                    "SELECT * FROM vacancy_cache WHERE key = ?", (key,)
                ).fetchone()
        except sqlite3.Error as e:
            logger.warning("Cache read failed: %s", e)
            return None


# Module-level singleton
_cache: Optional[VacancyCache] = None


def get_cache() -> VacancyCache:
    global _cache
    if _cache is None:
        _cache = VacancyCache()
    return _cache
