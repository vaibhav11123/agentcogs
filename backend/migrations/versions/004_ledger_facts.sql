-- Ledger facts, allocation lines, and the audit tables around them.
-- Idempotent. A second apply is a no-op. Price rows are inserts, never updates.

CREATE TABLE IF NOT EXISTS price_books (
    book_id          TEXT PRIMARY KEY,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usd_per_million  JSONB NOT NULL,
    lanes            JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_facts (
    workspace_id     UUID NOT NULL REFERENCES workspaces(id),
    run_id           UUID NOT NULL,
    customer_id      UUID REFERENCES customers(id),
    event_time       TIMESTAMPTZ NOT NULL,
    record_time      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    book_id          TEXT NOT NULL REFERENCES price_books(book_id),
    incurred_micro   BIGINT NOT NULL,
    allocation_mode  TEXT,
    lanes            JSONB NOT NULL DEFAULT '{}'::jsonb,
    calls            JSONB NOT NULL DEFAULT '[]'::jsonb,
    segments         JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (workspace_id, run_id)
);

CREATE TABLE IF NOT EXISTS allocation_lines (
    workspace_id  UUID NOT NULL,
    pane_id       TEXT NOT NULL,
    run_id        UUID NOT NULL,
    segment_id    TEXT NOT NULL,
    call_id       TEXT NOT NULL,
    micro         BIGINT NOT NULL,
    event_time    TIMESTAMPTZ NOT NULL,
    record_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, pane_id, run_id, segment_id, call_id)
);

CREATE TABLE IF NOT EXISTS cache_segments (
    workspace_id   UUID NOT NULL,
    segment_key    TEXT NOT NULL,
    event_time     TIMESTAMPTZ NOT NULL,
    ttl_seconds    INTEGER NOT NULL,
    write_micro    BIGINT NOT NULL,
    prefix_key     TEXT NOT NULL,
    closed_at      TIMESTAMPTZ,
    PRIMARY KEY (workspace_id, segment_key)
);

CREATE TABLE IF NOT EXISTS ledger_residuals (
    workspace_id   UUID NOT NULL,
    provider       TEXT NOT NULL,
    event_date     DATE NOT NULL,
    ledger_micro   BIGINT NOT NULL,
    provider_micro BIGINT,
    residual_micro BIGINT,
    record_time    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, provider, event_date, record_time)
);

CREATE TABLE IF NOT EXISTS workspace_heartbeats (
    workspace_id            UUID PRIMARY KEY REFERENCES workspaces(id),
    oldest_outbox_age_sec   INTEGER NOT NULL,
    watermark_event_time    TIMESTAMPTZ,
    recorded_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ledger_drift (
    workspace_id    UUID NOT NULL,
    month           DATE NOT NULL,
    ledger_micro    BIGINT NOT NULL,
    redis_micro     BIGINT NOT NULL,
    record_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, month, record_time)
);

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS budget_enforce BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE anomalies ADD COLUMN IF NOT EXISTS detector TEXT NOT NULL DEFAULT 'zscore';

CREATE TABLE IF NOT EXISTS settlement_receipts (
    workspace_id   UUID NOT NULL,
    run_id         UUID NOT NULL,
    customer_id    UUID NOT NULL,
    month          DATE NOT NULL,
    actual_micro   BIGINT NOT NULL,
    record_time    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, run_id)
);

CREATE TABLE IF NOT EXISTS budget_audit (
    workspace_id      UUID NOT NULL,
    customer_id       UUID NOT NULL,
    record_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    legacy_status     TEXT NOT NULL,
    reserve_decision  TEXT NOT NULL,
    spent_micro       BIGINT NOT NULL,
    held_micro        BIGINT NOT NULL,
    estimate_micro    BIGINT NOT NULL,
    budget_micro      BIGINT,
    PRIMARY KEY (workspace_id, customer_id, record_time)
);

INSERT INTO price_books (book_id, usd_per_million, lanes)
VALUES (
    'fixture-v1',
    '{"input": 3, "output": 15}'::jsonb,
    '{"uncached_input": {"base": "input", "num": 1, "den": 1}, "cache_read": {"base": "input", "num": 1, "den": 10}, "cache_write_5m": {"base": "input", "num": 5, "den": 4}, "cache_write_1h": {"base": "input", "num": 2, "den": 1}, "cache_write_30m": {"base": "input", "num": 5, "den": 4}, "cache_write_12h": {"base": "input", "num": 5, "den": 2}, "output": {"base": "output", "num": 1, "den": 1}}'::jsonb
)
ON CONFLICT (book_id) DO NOTHING;
