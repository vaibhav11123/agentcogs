-- Oldest-fact lookup for the CUSUM precheck.
-- Idempotent. A second apply is a no-op.

CREATE INDEX IF NOT EXISTS idx_ledger_facts_ws_cust_time
    ON ledger_facts (workspace_id, customer_id, event_time);
