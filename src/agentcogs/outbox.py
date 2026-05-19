"""Local SQLite outbox for offline-safe cost event delivery.

Pattern: write locally first, retry on next run().
Mirrors Stripe's recommended meter-event delivery pattern.
"""
import json
import pathlib
import sqlite3
import threading
import time
from typing import Any, Callable, Dict, List, Tuple

_DB_PATH = pathlib.Path.home() / ".agentcogs" / "outbox.db"
_LOCK = threading.Lock()
_MAX_ATTEMPTS = 8


def _ensure_db() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS outbox (
            run_id      TEXT PRIMARY KEY,
            payload     TEXT NOT NULL,
            attempts    INTEGER NOT NULL DEFAULT 0,
            next_retry  INTEGER NOT NULL DEFAULT 0,
            created_at  INTEGER NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending'
        )
        """
    )
    # Migrate older DBs without status column
    cols = {row[1] for row in conn.execute("PRAGMA table_info(outbox)").fetchall()}
    if "status" not in cols:
        conn.execute("ALTER TABLE outbox ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
    return conn


def enqueue(event: dict) -> None:
    with _LOCK:
        conn = _ensure_db()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO outbox (run_id, payload, created_at, status) "
                "VALUES (?,?,?, 'pending')",
                (event["run_id"], json.dumps(event), int(time.time())),
            )
        finally:
            conn.close()


def drain(post_fn: Callable[[dict], None], max_items: int = 50) -> Tuple[int, int]:
    """Try to deliver queued events. Returns (succeeded, failed)."""
    now = int(time.time())
    sent = failed = 0
    with _LOCK:
        conn = _ensure_db()
        try:
            rows: List[Tuple[str, str, int]] = conn.execute(
                "SELECT run_id, payload, attempts FROM outbox "
                "WHERE status = 'pending' AND attempts < ? AND next_retry <= ? "
                "ORDER BY created_at LIMIT ?",
                (_MAX_ATTEMPTS, now, max_items),
            ).fetchall()

            for run_id, payload, attempts in rows:
                try:
                    post_fn(json.loads(payload))
                    conn.execute("DELETE FROM outbox WHERE run_id=?", (run_id,))
                    sent += 1
                except Exception:
                    new_attempts = attempts + 1
                    if new_attempts >= _MAX_ATTEMPTS:
                        conn.execute(
                            "UPDATE outbox SET attempts=?, status='dead' WHERE run_id=?",
                            (new_attempts, run_id),
                        )
                    else:
                        backoff = min(2**new_attempts, 3600)
                        conn.execute(
                            "UPDATE outbox SET attempts=?, next_retry=? WHERE run_id=?",
                            (new_attempts, now + backoff, run_id),
                        )
                    failed += 1
        finally:
            conn.close()
    return sent, failed


def get_status() -> Dict[str, Any]:
    with _LOCK:
        conn = _ensure_db()
        try:
            pending = conn.execute(
                "SELECT COUNT(*) FROM outbox WHERE status='pending'"
            ).fetchone()[0]
            dead = conn.execute(
                "SELECT COUNT(*) FROM outbox WHERE status='dead'"
            ).fetchone()[0]
            oldest = conn.execute(
                "SELECT MIN(created_at) FROM outbox WHERE status='pending'"
            ).fetchone()[0]
        finally:
            conn.close()
    age = int(time.time()) - oldest if oldest else 0
    return {"pending": pending, "dead": dead, "oldest_pending_age_sec": age}
