# Demo personas — Patternstack mock tenant roster

**Operator:** Alex Chen @ Patternstack (`demo@agentcogs.dev`)  
**Customers:** 40 fictional B2B tenants (7 hero + 33 filler)  
**Source of truth:** `tools/personas.py` + `tools/personas_filler.py`

## Hero customers (demo script)

| Persona | Role | Revenue | Target margin | Live moment |
|---------|------|---------|---------------|-------------|
| Acme Corp | Healthy hero | $12,400 | ~75% | “This is what good looks like” |
| TechFlow Inc | Unprofitable | $8,200 | ~29% | Row click → node breakdown |
| Globex Industries | Whale | $28,500 | ~65% | High volume, still green |
| Initech | Anomaly bait | $2,100 | ~35% | `live_drift.py` key **`a`** |
| Hooli | Churning | $499 | — | No runs in last 14 days |
| Pied Piper | New | $99 | — | Small usage ramp |
| Dunder Mifflin | Zero revenue | $0 | — | “Add revenue” in table |

## Before every demo / recording

```bash
./tools/seed_demo.sh
./tools/verify_demo.sh
cd dashboard && npm run dev
# open http://localhost:5173/demo
```

## Live drift hotkeys

```bash
source tools/.demo_env
python3 tools/live_drift.py \
  --workspace-id "$DEMO_WORKSPACE_ID" \
  --api-key "$DEMO_API_KEY" \
  --interactive
```

| Key | Action |
|-----|--------|
| `a` | Inject Initech anomaly |
| `b` | Burst from Globex |
| `q` | Quit |

## Do not change before a call

- `seed=42` in `generate_events.py` / `seed_demo.sh`
- Hero `target_margin_pct` bands without re-running `verify_demo.sh`
- Real company names (fictional only)

MTD margins are **calibrated to calendar month** (same math as the dashboard): `monthly_revenue_usd` vs cost since the 1st of the month UTC. Prior-month events exist only for chart history.

## Tuning personas

```bash
streamlit run tools/persona_editor/app.py
./tools/seed_demo.sh
./tools/verify_demo.sh
```
