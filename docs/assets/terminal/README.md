# README assets

## UI screenshots (`../screenshots/`)

Captured from `http://localhost:5173/demo` after `./tools/seed_demo.sh && ./tools/start_demo.sh`.

| File | Page |
|------|------|
| `leaderboard.png` | Customers leaderboard |
| `settings.png` | Settings / SDK snippet |
| `customer-detail.png` | Single customer drill-down |
| `alerts.png` | Cost anomaly alerts |

## Terminal captures (`.txt` → `terminal-*.png`)

Regenerate:

```bash
# hello (zero-cost ingest; needs API + tools/.demo_env)
set -a && source tools/.demo_env && set +a
unset OPENAI_API_KEY ANTHROPIC_API_KEY
export AGENTCOGS_ENDPOINT=http://localhost:8000 AGENTCOGS_TEST_TENANT=readme_demo
printf '$ python3 examples/hello_agentcogs.py\n\n' > docs/assets/terminal/hello-agentcogs.txt
python3 examples/hello_agentcogs.py >> docs/assets/terminal/hello-agentcogs.txt 2>&1

# sales mock (pipe Enter twice)
printf '$ python3 prototype/demo.py\n\n' > docs/assets/terminal/prototype-demo.txt
printf '\n\n' | python3 prototype/demo.py >> docs/assets/terminal/prototype-demo.txt 2>&1

# PNGs
python3 scripts/render_terminal_png.py docs/assets/terminal/hello-agentcogs.txt docs/assets/screenshots/terminal-hello-agentcogs.png
# use prototype-demo-excerpt.txt for shorter README image
```
