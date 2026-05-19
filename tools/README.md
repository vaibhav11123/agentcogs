# AgentCOGS demo & mock data tools

Two kinds of mock data — do not conflate them:

| Purpose | Tool | Use case |
|---------|------|----------|
| **Prototype demo** | `prototype/demo.py` | Week 0 calls — no infra |
| **Product fixtures** | `generate_events.py`, `seed_demo.sh` | Local dev, CI, screenshots |

## Quick start

```bash
# Full demo environment (~60s seed, ~10s restart)
chmod +x tools/seed_demo.sh tools/start_demo.sh tools/stop_demo.sh tools/gen_screenshots.sh
./tools/seed_demo.sh          # first time or reset data

# Start API + dashboard (detached — survives terminal close)
./tools/start_demo.sh
# Open http://localhost:5173/demo

# Stop when done
./tools/stop_demo.sh

# Live drift during a call
source tools/.demo_env   # optional — vars printed by seed_demo.sh
python3 tools/live_drift.py \
  --workspace-id "$DEMO_WORKSPACE_ID" \
  --api-key "$DEMO_API_KEY" \
  --interactive
```

## Files

| File | Role |
|------|------|
| `personas.py` | Source of truth — 7 fictional customers |
| `generate_events.py` | JSONL or POST to `/v1/ingest` |
| `seed_from_file.py` | Replay JSONL |
| `live_drift.py` | Real-time events + hotkey anomalies |
| `seed_demo.sh` | One-command Docker + seed |
| `gen_screenshots.sh` | Deterministic `marketing/fixtures/` |
| `persona_editor/` | Streamlit GUI |

## Persona editor

```bash
pip install -r tools/persona_editor/requirements.txt
streamlit run tools/persona_editor/app.py
```

## Decision matrix

| You're about to… | Use |
|------------------|-----|
| Week 0 validation call (no backend) | `python prototype/demo.py` |
| Local dev / demo call with dashboard | `./tools/seed_demo.sh` |
| CI / unit tests | `pytest` (mocked Shekel) |
| E2E | `./test_e2e.sh` |
| Launch screenshots | `./tools/gen_screenshots.sh` |
| Public demo on site | `/demo` → `POST /v1/demo/session` |
| Load test | `generate_events.py --mode post --rate 500 --days 1` |

**Never use real company names in mock data.** Personas use fictional names only (Acme, TechFlow, Globex, etc.).
