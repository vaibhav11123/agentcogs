"""SQLite ledger for one machine. Enforcement stays off unless this workspace turns it on."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from .kernel.attribute import allocate_case
from .reports import concentration, margin_story, plan_margin, unattributed_share

SCHEMA_VERSION = 1
KNOWN_MODELS = frozenset(
    {
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "claude-3-5-haiku",
        "claude-3-5-sonnet",
        "claude-sonnet-4",
        "claude-haiku-4",
    }
)
FIXTURE_RUN = "fixture-document-analysis"
FIXTURE_CUSTOMER = "customer_001"
FIXTURE_TOKENS = 8200


def price_book() -> dict:
    path = Path(__file__).resolve().parent / "data" / "price_book_fixture_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_case() -> dict:
    zeros = {
        "uncached_input": FIXTURE_TOKENS,
        "cache_read": 0,
        "cache_write_5m": 0,
        "cache_write_1h": 0,
        "cache_write_30m": 0,
        "cache_write_12h": 0,
        "output": 0,
        "reasoning": 0,
    }
    return {
        "calls": [{"call_id": "document-analysis", "lanes": zeros}],
        "segments": [],
    }


def ledger_home() -> Path | None:
    """The ledger from `agentcogs init`, if this process can see it."""
    raw = os.environ.get("AGENTCOGS_HOME")
    home = Path(raw) if raw else Path.cwd() / ".agentcogs"
    if (home / "ledger.sqlite").is_file():
        return home
    return None


def connect(home: Path) -> sqlite3.Connection:
    home.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(home / "ledger.sqlite", isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    return str(row["value"])


def _set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def init_home(home: Path, *, exist_ok: bool = False) -> dict:
    """Create local storage. An existing ledger is left untouched unless exist_ok is set."""
    db_path = home / "ledger.sqlite"
    if db_path.exists() and not exist_ok:
        raise FileExistsError(str(db_path))
    if db_path.exists() and exist_ok:
        conn = connect(home)
        try:
            return status(conn)
        finally:
            conn.close()
    home.mkdir(parents=True, exist_ok=True)
    conn = connect(home)
    try:
        conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE events (
                run_id TEXT PRIMARY KEY,
                customer_id TEXT,
                provider TEXT NOT NULL,
                workflow TEXT NOT NULL,
                model TEXT NOT NULL,
                incurred_micro INTEGER NOT NULL,
                book_id TEXT NOT NULL,
                event_day TEXT NOT NULL
            );
            CREATE TABLE audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE TABLE model_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE TABLE residuals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                provider_micro INTEGER NOT NULL,
                ledger_micro INTEGER NOT NULL
            );
            CREATE TABLE subscriptions (
                customer_id TEXT PRIMARY KEY,
                plan TEXT,
                fee_micro INTEGER,
                stripe_customer_id TEXT
            );
            CREATE TABLE credits (
                customer_id TEXT PRIMARY KEY,
                allowance INTEGER NOT NULL,
                categories TEXT NOT NULL
            );
            CREATE TABLE months (
                month TEXT PRIMARY KEY,
                revenue_micro INTEGER NOT NULL,
                ai_micro INTEGER NOT NULL,
                retry_micro INTEGER NOT NULL DEFAULT 0,
                pro_usage_micro INTEGER NOT NULL DEFAULT 0,
                model_change_micro INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        _set_meta(conn, "schema_version", str(SCHEMA_VERSION))
        _set_meta(conn, "workspace_id", "ws_local")
        _set_meta(conn, "api_key", "acg_local_" + secrets.token_hex(16))
        _set_meta(conn, "budget_enforce", "false")
        _set_meta(conn, "book_id", price_book()["book_id"])
        (home / "price_book.json").write_text(json.dumps(price_book()), encoding="utf-8")
        return status(conn)
    finally:
        conn.close()


def status(conn: sqlite3.Connection) -> dict:
    count = conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"]
    spent = conn.execute("SELECT COALESCE(SUM(incurred_micro), 0) AS n FROM events").fetchone()["n"]
    return {
        "workspace_id": _meta(conn, "workspace_id"),
        "schema_version": int(_meta(conn, "schema_version", "0") or 0),
        "budget_enforce": _meta(conn, "budget_enforce") == "true",
        "events": int(count),
        "incurred_micro": int(spent),
        "book_id": _meta(conn, "book_id"),
    }


def doctor(home: Path) -> list[str]:
    """Empty list means healthy. Each string is a problem a person can act on."""
    problems: list[str] = []
    db_path = home / "ledger.sqlite"
    if not db_path.exists():
        return ["ledger.sqlite is missing. Run agentcogs init."]
    book = home / "price_book.json"
    if not book.exists():
        problems.append("price_book.json is missing.")
    conn = connect(home)
    try:
        if int(_meta(conn, "schema_version", "0") or 0) != SCHEMA_VERSION:
            problems.append("schema_version does not match this package.")
        if _meta(conn, "budget_enforce") not in {"true", "false"}:
            problems.append("budget_enforce is not a boolean.")
        if conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"] < 1:
            problems.append("no usage event has been recorded.")
    finally:
        conn.close()
    return problems


def record_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    customer_id: str | None,
    provider: str,
    workflow: str,
    model: str,
    case: dict,
    budget_micro: int | None = None,
    event_day: str | None = None,
) -> dict:
    if model not in KNOWN_MODELS:
        conn.execute(
            "INSERT INTO model_flags(model, recorded_at) VALUES(?, ?)",
            (model, _now()),
        )
        raise ValueError("UNKNOWN_MODEL")
    if not customer_id:
        raise ValueError("MISSING_CUSTOMER")
    existing = conn.execute("SELECT incurred_micro FROM events WHERE run_id=?", (run_id,)).fetchone()
    priced = allocate_case(case, price_book())
    incurred = sum(priced["incurred_micro"].values())
    if existing is not None:
        if int(existing["incurred_micro"]) != incurred:
            raise ValueError("PAYLOAD_MISMATCH")
        return {"duplicate": True, "incurred_micro": incurred}
    spent = conn.execute(
        "SELECT COALESCE(SUM(incurred_micro), 0) AS n FROM events WHERE customer_id=?",
        (customer_id,),
    ).fetchone()["n"]
    enforce = _meta(conn, "budget_enforce") == "true"
    if budget_micro is not None and int(spent) + incurred > budget_micro:
        decision = "exceeded"
        conn.execute(
            "INSERT INTO audits(customer_id, decision, recorded_at) VALUES(?, ?, ?)",
            (customer_id, decision, _now()),
        )
        if enforce:
            raise ValueError("BUDGET_EXCEEDED")
    day = event_day or datetime.now(timezone.utc).date().isoformat()
    conn.execute(
        """
        INSERT INTO events(run_id, customer_id, provider, workflow, model, incurred_micro, book_id, event_day)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, customer_id, provider, workflow, model, incurred, price_book()["book_id"], day),
    )
    return {"duplicate": False, "incurred_micro": incurred, "enforce": enforce}


def record_calls(
    home: Path,
    *,
    run_id: str,
    customer_id: str,
    workflow: str,
    calls: list[dict],
) -> list[dict]:
    """Store priced calls from this process. One row per call. No prompt is read."""
    if not calls:
        return []
    conn = connect(home)
    try:
        written: list[dict] = []
        many = len(calls) > 1
        for call in calls:
            model = str(call.get("model") or "")
            call_id = str(call.get("call_id") or "c0")
            provider = "Anthropic" if model.startswith("claude") else "OpenAI"
            result = record_event(
                conn,
                run_id=f"{run_id}:{call_id}" if many else run_id,
                customer_id=customer_id,
                provider=provider,
                workflow=workflow,
                model=model,
                case={"calls": [{"call_id": call_id, "lanes": call.get("lanes") or {}}], "segments": []},
            )
            written.append(result)
        return written
    finally:
        conn.close()


def verify_fixture(home: Path) -> dict:
    """Price the documented sample call locally. No provider request."""
    conn = connect(home)
    try:
        result = record_event(
            conn,
            run_id=FIXTURE_RUN,
            customer_id=FIXTURE_CUSTOMER,
            provider="OpenAI",
            workflow="Document analysis",
            model="gpt-4o-mini",
            case=fixture_case(),
        )
        result["customer_id"] = FIXTURE_CUSTOMER
        return result
    finally:
        conn.close()


def customer_totals(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT customer_id, SUM(incurred_micro) AS micro
        FROM events
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
        """
    ).fetchall()
    return {str(row["customer_id"]): int(row["micro"]) for row in rows}


def health(conn: sqlite3.Connection, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    residual_rows = [
        {"day": row["day"], "provider_micro": row["provider_micro"], "ledger_micro": row["ledger_micro"]}
        for row in conn.execute("SELECT day, provider_micro, ledger_micro FROM residuals")
    ]
    return {
        "concentration": concentration(customer_totals(conn)),
        "unattributed_share": unattributed_share(residual_rows, today),
    }


def set_subscription(
    conn: sqlite3.Connection,
    customer_id: str,
    *,
    plan: str | None,
    fee_micro: int | None,
    stripe_customer_id: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO subscriptions(customer_id, plan, fee_micro, stripe_customer_id)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(customer_id) DO UPDATE SET
            plan=excluded.plan,
            fee_micro=excluded.fee_micro,
            stripe_customer_id=excluded.stripe_customer_id
        """,
        (customer_id, plan, fee_micro, stripe_customer_id),
    )


def subscription_margin(conn: sqlite3.Connection, customer_id: str) -> dict:
    sub = conn.execute("SELECT * FROM subscriptions WHERE customer_id=?", (customer_id,)).fetchone()
    spent = conn.execute(
        "SELECT COALESCE(SUM(incurred_micro), 0) AS n FROM events WHERE customer_id=?",
        (customer_id,),
    ).fetchone()["n"]
    fee = None if sub is None or sub["fee_micro"] is None else int(sub["fee_micro"])
    mapped = sub is not None and sub["stripe_customer_id"] not in (None, "")
    return {
        "customer_id": customer_id,
        "fee_micro": fee,
        "ai_micro": int(spent),
        "margin": plan_margin(fee, int(spent)),
        "mapped": mapped,
        "needs_mapping": sub is None or not mapped,
    }


def set_enforce(conn: sqlite3.Connection, enabled: bool) -> None:
    _set_meta(conn, "budget_enforce", "true" if enabled else "false")


def add_residual(conn: sqlite3.Connection, day: str, provider_micro: int, ledger_micro: int) -> None:
    conn.execute(
        "INSERT INTO residuals(day, provider_micro, ledger_micro) VALUES(?, ?, ?)",
        (day, provider_micro, ledger_micro),
    )


def set_credits(conn: sqlite3.Connection, customer_id: str, allowance: int, categories: dict[str, int]) -> None:
    from .reports import credit_balance

    credit_balance(allowance, categories)
    conn.execute(
        """
        INSERT INTO credits(customer_id, allowance, categories) VALUES(?, ?, ?)
        ON CONFLICT(customer_id) DO UPDATE SET allowance=excluded.allowance, categories=excluded.categories
        """,
        (customer_id, allowance, json.dumps(categories)),
    )


def read_credits(conn: sqlite3.Connection, customer_id: str) -> dict | None:
    from .reports import credit_balance

    row = conn.execute("SELECT allowance, categories FROM credits WHERE customer_id=?", (customer_id,)).fetchone()
    if row is None:
        return None
    return credit_balance(int(row["allowance"]), json.loads(row["categories"]))


def add_month(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        """
        INSERT INTO months(month, revenue_micro, ai_micro, retry_micro, pro_usage_micro, model_change_micro)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
            revenue_micro=excluded.revenue_micro,
            ai_micro=excluded.ai_micro,
            retry_micro=excluded.retry_micro,
            pro_usage_micro=excluded.pro_usage_micro,
            model_change_micro=excluded.model_change_micro
        """,
        (
            row["month"],
            int(row["revenue_micro"]),
            int(row["ai_micro"]),
            int(row.get("retry_micro") or 0),
            int(row.get("pro_usage_micro") or 0),
            int(row.get("model_change_micro") or 0),
        ),
    )


def assistant_story(conn: sqlite3.Connection) -> dict | None:
    rows = [dict(row) for row in conn.execute("SELECT * FROM months ORDER BY month")]
    return margin_story(rows)


def export_json(home: Path) -> dict:
    conn = connect(home)
    try:
        events = [dict(row) for row in conn.execute("SELECT * FROM events ORDER BY run_id")]
        return {"status": status(conn), "events": events}
    finally:
        conn.close()


def backup_database(home: Path, dest: Path) -> Path:
    """Copy the ledger before a schema change or an explicit backup."""
    source = home / "ledger.sqlite"
    if not source.exists():
        raise FileNotFoundError(str(source))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return dest


def prepare_migration(home: Path) -> Path:
    dest = home / "backups" / f"ledger-before-{SCHEMA_VERSION + 1}.sqlite"
    if dest.exists():
        raise FileExistsError(str(dest))
    return backup_database(home, dest)


def restore_database(home: Path, source: Path, *, replace: bool = False) -> None:
    target = home / "ledger.sqlite"
    if target.exists() and not replace:
        raise FileExistsError(str(target))
    if not source.exists():
        raise FileNotFoundError(str(source))
    home.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def render_dashboard(home: Path) -> str:
    conn = connect(home)
    try:
        rows = conn.execute(
            "SELECT customer_id, provider, workflow, incurred_micro, model FROM events ORDER BY run_id"
        ).fetchall()
        body = []
        for row in rows:
            dollars = int(row["incurred_micro"]) / 1_000_000
            body.append(
                "<tr>"
                f"<td>{_esc(row['customer_id'])}</td>"
                f"<td>{_esc(row['provider'])}</td>"
                f"<td>{_esc(row['workflow'])}</td>"
                f"<td>{_esc(row['model'])}</td>"
                f"<td>${dollars:.4f}</td>"
                "</tr>"
            )
        table = "\n".join(body) or "<tr><td colspan='5'>No events yet.</td></tr>"
        enforce = _meta(conn, "budget_enforce")
        report = health(conn)
        story = assistant_story(conn)
    finally:
        conn.close()
    extra = []
    if report["concentration"] is not None:
        share = report["concentration"]["share"] * 100
        extra.append(f"<p>Top customers account for {share:.1f}% of expenditure.</p>")
    if report["unattributed_share"] is not None:
        extra.append(f"<p>Unattributed share {report['unattributed_share'] * 100:.1f}%.</p>")
    if story is not None:
        extra.append(
            f"<p>Margin moved from {story['before'] * 100:.0f}% to {story['after'] * 100:.0f}%.</p>"
        )
    notes = "\n".join(extra)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>AgentCOGS local</title></head>
<body>
<h1>Your application is connected</h1>
<p>Monitor only. Budget enforcement is { _esc(enforce) }.</p>
{notes}
<table>
<thead><tr><th>Customer</th><th>Provider</th><th>Workflow</th><th>Model</th><th>Cost</th></tr></thead>
<tbody>
{table}
</tbody>
</table>
</body>
</html>
"""


def render_balance_html(balance: dict) -> str:
    items = "".join(
        f"<li>{_esc(name)}: {int(amount)}</li>" for name, amount in balance["categories"].items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Usage balance</title></head>
<body>
<p>Active</p>
<h1>{int(balance['used'])} / {int(balance['allowance'])} credits</h1>
<p>Remaining credits {int(balance['remaining'])}</p>
<ul>{items}</ul>
</body>
</html>
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _esc(value: object) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
