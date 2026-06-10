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
import os
import sqlite3
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("hhanalyst.cache")

# Default location; can be overridden with HHANALYST_DB_PATH (useful when the
# repo lives in a read-only / cloud-synced folder where SQLite cannot create
# the file — e.g. some OneDrive setups).
_DEFAULT_DB = Path(__file__).parent.parent / "data" / "vacancies.db"
DB_PATH = Path(os.environ["HHANALYST_DB_PATH"]) if os.environ.get("HHANALYST_DB_PATH") else _DEFAULT_DB

# How long cached data is served directly (without re-querying hh.ru) and how
# long it is kept at all. Both are configurable via environment variables.
# Long defaults mean fewer requests to hh.ru (less chance of being rate-limited)
# and multi-day retention. SQLite imposes no practical row limit, so the cache
# can hold a very large number of distinct queries.
FRESH_TTL = int(os.environ.get("CACHE_FRESH_TTL", 3 * 24 * 3600))   # 3 days
STALE_TTL = int(os.environ.get("CACHE_STALE_TTL", 30 * 24 * 3600))  # 30 days

_SCHEMA = """
    CREATE TABLE IF NOT EXISTS vacancy_cache (
        key        TEXT PRIMARY KEY,
        query      TEXT NOT NULL,
        area       TEXT NOT NULL DEFAULT '',
        max_pages  INTEGER NOT NULL DEFAULT 3,
        data       TEXT NOT NULL,
        fetched_at REAL NOT NULL,
        count      INTEGER NOT NULL DEFAULT 0
    )
"""


class VacancyCache:
    def __init__(self, db_path: Path = DB_PATH):
        # Try the configured path first; if the file cannot be opened or
        # created (permissions, read-only / cloud-synced folder), fall back
        # to a writable temp directory. If even that fails, the L2 cache is
        # disabled and the app keeps working without persistent caching.
        self.enabled = False
        self._db_path = str(db_path)

        if self._try_init(db_path):
            self.enabled = True
            return

        fallback = Path(tempfile.gettempdir()) / "hhanalyst" / "vacancies.db"
        if self._try_init(fallback):
            self._db_path = str(fallback)
            self.enabled = True
            logger.warning(
                "Primary cache path unavailable; using fallback DB at %s", fallback)
        else:
            logger.warning(
                "L2 SQLite cache disabled: could not open a database file. "
                "App will run without persistent caching. "
                "Set HHANALYST_DB_PATH to a writable location to re-enable it.")

    def _try_init(self, db_path: Path) -> bool:
        """Attempt to create the directory, file and schema. Returns success."""
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(db_path), timeout=5) as conn:
                conn.execute(_SCHEMA)
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_fetched ON vacancy_cache(fetched_at)")
                conn.commit()
            self._db_path = str(db_path)
            return True
        except (sqlite3.Error, OSError) as e:
            logger.warning("Cache init failed at %s: %s", db_path, e)
            return False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

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
        if not self.enabled:
            return
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
        if not self.enabled:
            return {"total_entries": 0, "entries": [], "enabled": False}
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
        if not self.enabled:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM vacancy_cache")
            conn.commit()

    # ── Internal ──────────────────────────────────────────────────

    def _fetch_row(self, key: str) -> Optional[sqlite3.Row]:
        if not self.enabled:
            return None
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
