-- Hashed API keys with rotation support (plaintext workspaces.api_key retained until 004).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS workspace_api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  key_hash TEXT NOT NULL UNIQUE,
  key_last4 TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_wak_workspace ON workspace_api_keys(workspace_id);

INSERT INTO workspace_api_keys (workspace_id, key_hash, key_last4)
SELECT id, encode(digest(api_key, 'sha256'), 'hex'), right(api_key, 4)
FROM workspaces
WHERE api_key IS NOT NULL
ON CONFLICT (key_hash) DO NOTHING;
