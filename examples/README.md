# Examples

## `hello_agentcogs.py`

Canonical quickstart: `ping()` → `set_customer()` → one `run()` → optional LLM call → `wait_for_ingest()`.

```bash
export AGENTCOGS_API_KEY='acg_live_...'
export AGENTCOGS_WORKSPACE_ID='your-uuid'
export AGENTCOGS_ENDPOINT='http://localhost:8000'   # omit for production

# optional
export OPENAI_API_KEY='...'   # or ANTHROPIC_API_KEY
export AGENTCOGS_TEST_TENANT='my_tenant'   # default: hello_tenant

pip install -e "..[dev]"   # from repo root
python3 examples/hello_agentcogs.py
```

Then open **Customers** in the dashboard (or complete `/onboarding`).

See [docs/quickstart.md](../docs/quickstart.md).
