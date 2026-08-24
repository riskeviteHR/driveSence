"""SQLite manifest of file hashes, enabling incremental scans: a file's
SHA-256 is only recomputed when its size or modified-time has changed since
the last scan. This is what makes repeat duplicate-detection passes fast."""

import sqlite3
import time

from app_paths import DATA_DIR

DB_PATH = DATA_DIR / "scan_manifest.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime REAL NOT NULL,
            sha256 TEXT NOT NULL,
            last_seen REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def get_cached_hash(conn, path, size, mtime):
    row = conn.execute(
        "SELECT sha256, size, mtime FROM file_hashes WHERE path = ?", (path,)
    ).fetchone()
    if not row:
        return None
    sha256, cached_size, cached_mtime = row
    # mtime comparison tolerant of tiny float drift from filesystem rounding
    if cached_size == size and abs(cached_mtime - mtime) < 1.0:
        return sha256
    return None


def store_hash(conn, path, size, mtime, sha256):
    conn.execute(
        "INSERT OR REPLACE INTO file_hashes (path, size, mtime, sha256, last_seen) VALUES (?, ?, ?, ?, ?)",
        (path, size, mtime, sha256, time.time()),
    )


def commit(conn):
    conn.commit()


def prune_stale(conn, seen_paths, older_than_days=30):
    """Remove manifest rows for files not seen in the most recent scan and
    not touched in a while, so deleted/moved files don't accumulate forever."""
    cutoff = time.time() - older_than_days * 86400
    all_paths = [r[0] for r in conn.execute("SELECT path FROM file_hashes").fetchall()]
    stale = [p for p in all_paths if p not in seen_paths]
    if not stale:
        return 0
    conn.executemany(
        "DELETE FROM file_hashes WHERE path = ? AND last_seen < ?",
        [(p, cutoff) for p in stale],
    )
    conn.commit()
    return len(stale)


def stats(conn):
    row = conn.execute("SELECT COUNT(*), COALESCE(SUM(size), 0) FROM file_hashes").fetchone()
    return {"cached_files": row[0], "cached_bytes": row[1]}
