"""Local SQLite outbox for offline-safe cost event delivery.

Pattern: write locally first, retry on next run().
The lock covers the SQLite claim only. The HTTP call runs after it is released.
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
_LEASE_SECONDS = 2
_CONN: sqlite3.Connection | None = None
_CONN_PATH: pathlib.Path | None = None


def _connect() -> sqlite3.Connection:
    global _CONN, _CONN_PATH
    if _CONN is not None and _CONN_PATH == _DB_PATH:
        return _CONN
    if _CONN is not None:
        _CONN.close()
        _CONN = None
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=5.0, isolation_level=None, check_same_thread=False)
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
    cols = {row[1] for row in conn.execute("PRAGMA table_info(outbox)").fetchall()}
    if "status" not in cols:
        conn.execute("ALTER TABLE outbox ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
    _CONN = conn
    _CONN_PATH = _DB_PATH
    return conn


def enqueue(event: dict) -> None:
    with _LOCK:
        conn = _connect()
        conn.execute(
            "INSERT OR IGNORE INTO outbox (run_id, payload, created_at, status) "
            "VALUES (?,?,?, 'pending')",
            (event["run_id"], json.dumps(event), int(time.time())),
        )


def drain(post_fn: Callable[[dict], None], max_items: int = 50) -> Tuple[int, int]:
    """Try to deliver queued events. Returns (succeeded, failed)."""
    now = int(time.time())
    claimed: List[Tuple[str, str, int]] = []
    with _LOCK:
        conn = _connect()
        conn.execute(
            "UPDATE outbox SET status='pending' WHERE status='inflight' AND next_retry <= ?",
            (now,),
        )
        rows: List[Tuple[str, str, int]] = conn.execute(
            "SELECT run_id, payload, attempts FROM outbox "
            "WHERE status = 'pending' AND attempts < ? AND next_retry <= ? "
            "ORDER BY created_at LIMIT ?",
            (_MAX_ATTEMPTS, now, max_items),
        ).fetchall()
        lease = now + _LEASE_SECONDS
        for run_id, payload, attempts in rows:
            updated = conn.execute(
                "UPDATE outbox SET status='inflight', next_retry=? WHERE run_id=? AND status='pending'",
                (lease, run_id),
            )
            if updated.rowcount:
                claimed.append((run_id, payload, attempts))

    sent = failed = 0
    finished: List[Tuple[str, bool, int]] = []
    for run_id, payload, attempts in claimed:
        try:
            post_fn(json.loads(payload))
            finished.append((run_id, True, attempts))
            sent += 1
        except Exception:
            finished.append((run_id, False, attempts))
            failed += 1

    if finished:
        with _LOCK:
            conn = _connect()
            for run_id, ok, attempts in finished:
                if ok:
                    conn.execute("DELETE FROM outbox WHERE run_id=? AND status='inflight'", (run_id,))
                    continue
                new_attempts = attempts + 1
                if new_attempts >= _MAX_ATTEMPTS:
                    conn.execute(
                        "UPDATE outbox SET attempts=?, status='dead' WHERE run_id=? AND status='inflight'",
                        (new_attempts, run_id),
                    )
                else:
                    backoff = min(2**new_attempts, 3600)
                    conn.execute(
                        "UPDATE outbox SET attempts=?, status='pending', next_retry=? "
                        "WHERE run_id=? AND status='inflight'",
                        (new_attempts, now + backoff, run_id),
                    )
    return sent, failed


def outbox_size() -> int:
    return int(get_status()["pending"])


def backlog() -> Dict[str, int]:
    with _LOCK:
        conn = _connect()
        rows = conn.execute("SELECT status, COUNT(*) FROM outbox GROUP BY status").fetchall()
    counts = {status: int(count) for status, count in rows}
    pending = counts.get("pending", 0)
    inflight = counts.get("inflight", 0)
    return {"pending": pending, "inflight": inflight, "queued": pending + inflight}


def clear_outbox() -> None:
    with _LOCK:
        conn = _connect()
        conn.execute("DELETE FROM outbox")


def get_status() -> Dict[str, Any]:
    with _LOCK:
        conn = _connect()
        pending = conn.execute(
            "SELECT COUNT(*) FROM outbox WHERE status='pending'"
        ).fetchone()[0]
        dead = conn.execute(
            "SELECT COUNT(*) FROM outbox WHERE status='dead'"
        ).fetchone()[0]
        oldest = conn.execute(
            "SELECT MIN(created_at) FROM outbox WHERE status='pending'"
        ).fetchone()[0]
    age = int(time.time()) - oldest if oldest else 0
    return {"pending": pending, "dead": dead, "oldest_pending_age_sec": age}
