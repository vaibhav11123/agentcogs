# Test Results

## Quick validation

```bash
./test_e2e.sh              # 14 tests (needs Docker + jq)
./test_e2e.sh --teardown   # cleanup containers
```

Monorepo defaults: SDK at repo root, backend at `./backend`.

Legacy script: `scripts/test_e2e.sh` (subset, port 5433) still works for quick checks.

## Last automated run

| Test | Result |
|------|--------|
| SDK pytest (7) | PASS |
| Backend pytest (3) | PASS |
| Dashboard build | PASS |
| scripts/test_e2e.sh (7 backend tests) | PASS |
| test_e2e.sh (14 tests) | Run locally with `./test_e2e.sh` |

Test 4 (real OpenAI) skipped when key has insufficient quota.
