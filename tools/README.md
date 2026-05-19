# AgentCOGS demo & mock data tools

Three integration paths — do not conflate them:

| Path | Tool | Use case |
|------|------|----------|
| **Production SDK** | `examples/hello_agentcogs.py` | Real workspace → first dashboard row |
| **Sales mock (no backend)** | `prototype/demo.py` | Week 0 calls — prints JSON only |
| **Product fixtures** | `seed_demo.sh`, `generate_events.py` | Local dev, CI, screenshots |
| **Live SDK on demo API** | `scripts/run_live_pipeline.py` | Claude → ingest → seeded dashboard |

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

# Live drift during a call (synthetic events)
source tools/.demo_env   # optional — vars printed by seed_demo.sh
python3 tools/live_drift.py \
  --workspace-id "$DEMO_WORKSPACE_ID" \
  --api-key "$DEMO_API_KEY" \
  --interactive

# Real SDK + Claude against demo workspace
export ANTHROPIC_API_KEY='...'
python3 scripts/run_live_pipeline.py
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
| `../scripts/run_live_pipeline.py` | Live `agentcogs.run()` + Anthropic on demo stack |
| `../examples/hello_agentcogs.py` | Canonical quickstart (any API endpoint) |

## Persona editor

```bash
pip install -r tools/persona_editor/requirements.txt
streamlit run tools/persona_editor/app.py
```

## Decision matrix

| You're about to… | Use |
|------------------|-----|
| First event in **your** production workspace | `examples/hello_agentcogs.py` + [docs/quickstart.md](../docs/quickstart.md) |
| Week 0 validation call (no backend) | `python3 prototype/demo.py` |
| Local dev / demo call with dashboard | `./tools/seed_demo.sh` |
| Prove real SDK ingest on local demo | `scripts/run_live_pipeline.py` |
| CI / unit tests | `pytest` (mocked Shekel) |
| E2E | `./test_e2e.sh` |
| Launch screenshots | `./tools/gen_screenshots.sh` |
| Public demo on site | `/demo` → `POST /v1/demo/session` |
| Load test | `generate_events.py --mode post --rate 500 --days 1` |
| LLM cost only (no AgentCOGS) | `python3 prototype.py` |

**Never use real company names in mock data.** Personas use fictional names only (Acme, TechFlow, Globex, etc.).
