# README assets

## UI screenshots (`../screenshots/`)

Captured from `http://localhost:5173/demo` after `./tools/seed_demo.sh && ./tools/start_demo.sh`.

### README sizing (GitHub best practice)

| Use | Source file | Display in README (`width=`) |
|-----|-------------|------------------------------|
| Hero dashboard | Crop above-the-fold, **960px** wide | **680** |
| Step screenshots | **960px** wide, &lt;150 KB | **640** |
| Terminal captures | Rendered PNG | **480–560** |

Do **not** use full-page `fullPage: true` browser shots (too tall/color-heavy). Crop to KPI + one table section. GitHub’s doc style guide targets **750–1000px** source width; README column renders best at **640–720px** display width ([GitHub docs](https://docs.github.com/en/contributing/writing-for-github-docs/configuring-vision-in-your-articles), common OSS practice).

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

# shekel (needs ANTHROPIC_API_KEY)
printf '$ python3 prototype/shekel_smoke.py\n\n' > docs/assets/terminal/shekel-smoke.txt
python3 prototype/shekel_smoke.py >> docs/assets/terminal/shekel-smoke.txt 2>&1

# run_live_pipeline (needs ANTHROPIC_API_KEY + seed)
printf '$ python3 scripts/run_live_pipeline.py\n\n' > docs/assets/terminal/run-live-pipeline.txt
python3 scripts/run_live_pipeline.py >> docs/assets/terminal/run-live-pipeline.txt 2>&1

# smoke/manual — offline
printf '$ python3 scripts/smoke/manual_test.py\n\n' > docs/assets/terminal/smoke-manual.txt
python3 scripts/smoke/manual_test.py >> docs/assets/terminal/smoke-manual.txt 2>&1

# smoke/integration — demo API key, zero-cost
set -a && source tools/.demo_env && set +a
export API_KEY="$DEMO_API_KEY" API_URL=http://localhost:8000 SKIP_OPENAI=1
printf '$ python3 scripts/smoke/integration_test.py\n\n' > docs/assets/terminal/smoke-integration.txt
python3 scripts/smoke/integration_test.py >> docs/assets/terminal/smoke-integration.txt 2>&1

# PNGs (all .txt in docs/assets/terminal/)
for f in docs/assets/terminal/*.txt; do
  base=$(basename "$f" .txt)
  python3 scripts/render_terminal_png.py "$f" "docs/assets/screenshots/terminal-${base}.png"
done
```
