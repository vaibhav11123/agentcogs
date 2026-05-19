# Demo paths

Pick the script that matches your goal. The README shows the two most common paths; everything else is here.

| Goal | Command | What you get |
|------|---------|----------------|
| **Prove SDK → API** | `python3 examples/hello_agentcogs.py` | Real ingest; row in dashboard |
| **Live LLM + ingest (demo stack)** | `python3 scripts/run_live_pipeline.py` | Claude → `agentcogs.run()` → dashboard |
| **Sales call (no backend)** | `python3 prototype/demo.py` | Mock cost JSON; press Enter twice |
| **Shekel only (no AgentCOGS)** | `python3 prototype/shekel_smoke.py` | Live LLM + cost JSON; no ingest |
| **SDK smoke (offline)** | `python3 scripts/smoke/manual_test.py` | `run()` + outbox; no API |
| **SDK smoke (local API)** | `python3 scripts/smoke/integration_test.py` | Ingest to Postgres on `:8000` |
| **Check failed ingests** | `python3 -m agentcogs outbox status` | Local outbox queue |
| **Full local stack** | `./tools/seed_demo.sh && ./tools/start_demo.sh` | Docker + seeded UI at `/demo` |

See [prototype/README.md](../prototype/README.md) and [scripts/smoke/README.md](../scripts/smoke/README.md).

## Terminal — SDK proof (`hello_agentcogs.py`)

```bash
pip install agentcogs
set -a && source tools/.demo_env && set +a   # after seed_demo.sh
export AGENTCOGS_ENDPOINT=http://localhost:8000
python3 examples/hello_agentcogs.py
```

<img src="assets/screenshots/terminal-hello-agentcogs.png" width="560" alt="Terminal: PingResult ok, ingest_accepted=True" />

## Terminal — sales mock (`prototype/demo.py`)

No API keys. Interactive walkthrough; prints mock JSON (not real ingest).

<img src="assets/screenshots/terminal-prototype-demo.png" width="560" alt="Terminal: prototype demo mock cost event" />

## Terminal — live pipeline (`scripts/run_live_pipeline.py`)

```bash
export ANTHROPIC_API_KEY='...'
python3 scripts/run_live_pipeline.py --customer pied_piper
```

<img src="assets/screenshots/terminal-run-live-pipeline.png" width="560" alt="Terminal: run_live_pipeline ingest sent" />

## Terminal — Shekel prototype (`prototype/shekel_smoke.py`)

```bash
export ANTHROPIC_API_KEY='...'
python3 prototype/shekel_smoke.py
```

<img src="assets/screenshots/terminal-shekel-smoke.png" width="560" alt="Terminal: shekel_smoke COST EVENT JSON" />

## Terminal — smoke scripts

| Script | Screenshot |
|--------|------------|
| `manual_test.py` | <img src="assets/screenshots/terminal-smoke-manual.png" width="560" alt="smoke manual" /> |
| `integration_test.py` | <img src="assets/screenshots/terminal-smoke-integration.png" width="560" alt="smoke integration" /> |

## Terminal — outbox

<img src="assets/screenshots/terminal-outbox-status.png" width="480" alt="outbox status" />

## Dashboard UI

After `./tools/seed_demo.sh && ./tools/start_demo.sh` → http://localhost:5173/demo

| View | Screenshot |
|------|------------|
| **Leaderboard** | <img src="assets/screenshots/leaderboard.png" width="640" alt="Leaderboard" /> |
| **Settings** | <img src="assets/screenshots/settings.png" width="640" alt="Settings" /> |
| **Customer drill-down** | <img src="assets/screenshots/customer-detail.png" width="640" alt="Customer detail" /> |
| **Alerts** | <img src="assets/screenshots/alerts.png" width="640" alt="Alerts" /> |

Regenerate assets: [assets/terminal/README.md](assets/terminal/README.md).
