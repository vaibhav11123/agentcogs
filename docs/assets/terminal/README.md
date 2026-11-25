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
| `patternstack-customers.png` | Sample book: blended margin and Vellum Research |
| `vellum-research.png` | Vellum Research, the fee, and the call that posts the cost |

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

# priced usage, no provider key
printf '$ python3 examples/priced_from_usage.py\n\n' > docs/assets/terminal/priced-from-usage.txt
python3 examples/priced_from_usage.py >> docs/assets/terminal/priced-from-usage.txt 2>&1
python3 scripts/render_terminal_png.py docs/assets/terminal/priced-from-usage.txt docs/assets/screenshots/terminal-priced-from-usage.png

# prototype/shekel_smoke.py and scripts/smoke/ are not in this tree.
# The older terminal captures that name them are historical.

# PNGs (all .txt in docs/assets/terminal/)
for f in docs/assets/terminal/*.txt; do
  base=$(basename "$f" .txt)
  python3 scripts/render_terminal_png.py "$f" "docs/assets/screenshots/terminal-${base}.png"
done
```
