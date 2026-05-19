-- SDK customer journey: TTFVE tracking
ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS sdk_first_seen_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS first_cost_event_at TIMESTAMPTZ;
