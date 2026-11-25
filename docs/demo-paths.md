# Demo paths

Pick the script that matches your goal. The README shows the two most common paths; everything else is here.

| Goal | Command | What you get |
|------|---------|----------------|
| **One machine, no Docker** | `agentcogs init`, then `python3 examples/own_customer.py`, then `agentcogs status` | The sample plus your customer `acme` in the same ledger |
| **Price a call with no provider** | `python3 examples/priced_from_usage.py` | OpenAI and Anthropic usage priced on this machine |
| **Prove SDK → API** | `python3 examples/hello_agentcogs.py` | Real ingest; row in dashboard |
| **Sales call (no backend)** | `python3 prototype/demo.py` | Mock cost JSON; press Enter twice |
| **Check failed ingests** | `python3 -m agentcogs outbox status` | Local outbox queue |
| **Full local stack** | `./tools/seed_demo.sh && ./tools/start_demo.sh` | Docker + seeded UI at `/demo` |

`prototype/shekel_smoke.py` and `scripts/smoke/` are not in this tree. Do not follow an old capture that names them.

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
python3 scripts/run_live_pipeline.py --customer kindred_notes
```

<img src="assets/screenshots/terminal-run-live-pipeline.png" width="560" alt="Terminal: run_live_pipeline ingest sent" />

## Terminal — priced usage, no provider (`examples/priced_from_usage.py`)

```bash
python3 examples/priced_from_usage.py
```

The clients talk to a stand-in in this repository. The printed total is the fixture book.

<img src="assets/screenshots/terminal-priced-from-usage.png" width="560" alt="Terminal: two calls priced from usage, total_usd 0.03288" />

## Terminal — outbox

<img src="assets/screenshots/terminal-outbox-status.png" width="480" alt="outbox status" />

## Dashboard UI

After `./tools/seed_demo.sh && ./tools/start_demo.sh` → http://localhost:5173/demo

| View | Screenshot |
|------|------------|
| **Customers** | <img src="assets/screenshots/patternstack-customers.png" width="720" alt="Patternstack customers, Vellum Research at 29%" /> |
| **Vellum Research** | <img src="assets/screenshots/vellum-research.png" width="720" alt="Vellum Research customer page" /> |

Regenerate assets: [assets/terminal/README.md](assets/terminal/README.md).
