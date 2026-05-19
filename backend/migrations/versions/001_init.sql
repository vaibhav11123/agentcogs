-- AgentCOGS initial schema
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE workspaces (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    api_key             TEXT UNIQUE NOT NULL,
    plan                TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id  TEXT,   -- AgentCOGS billing them
    stripe_account_id   TEXT,   -- their connected account (for sync)
    slack_webhook_url   TEXT,
    alert_email         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customers (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id          UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    external_id           TEXT NOT NULL,
    display_name          TEXT,
    monthly_budget_usd    NUMERIC(10,4),
    monthly_revenue_usd   NUMERIC(10,2),
    stripe_customer_id    TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, external_id)
);
CREATE INDEX idx_customers_workspace ON customers(workspace_id);

CREATE TABLE cost_events (
    id                  UUID PRIMARY KEY,
    workspace_id        UUID NOT NULL REFERENCES workspaces(id),
    customer_id         UUID NOT NULL REFERENCES customers(id),
    workflow_id         TEXT NOT NULL DEFAULT 'default',
    ts                  TIMESTAMPTZ NOT NULL,
    status              TEXT NOT NULL,
    total_usd           NUMERIC(12,6) NOT NULL,
    model_breakdown     JSONB NOT NULL DEFAULT '{}'::jsonb,
    node_breakdown      JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    error               TEXT,
    stripe_synced_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_events_ws_cust_ts ON cost_events(workspace_id, customer_id, ts DESC);
CREATE INDEX idx_events_workflow ON cost_events(customer_id, workflow_id, ts DESC);
CREATE INDEX idx_events_sync_pending ON cost_events(ts)
    WHERE stripe_synced_at IS NULL;

CREATE TABLE anomalies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    cost_event_id   UUID NOT NULL REFERENCES cost_events(id),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    z_score         NUMERIC(8,2),
    multiplier      NUMERIC(8,2),
    mean_usd        NUMERIC(12,6),
    alerted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_anomalies_ws ON anomalies(workspace_id, created_at DESC);

-- Suppression: don't re-alert same customer+workflow within 6 hours
CREATE TABLE alert_suppressions (
    workspace_id  UUID NOT NULL,
    customer_id   UUID NOT NULL,
    workflow_id   TEXT NOT NULL,
    suppress_until TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id, customer_id, workflow_id)
);
