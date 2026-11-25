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

A consumed OpenAI or Anthropic response is priced from its usage object. Cached tokens and cache writes are part of that total. `priced_from_usage.py` runs the same path against a stand-in in this repository, so no provider key is required.

## `own_customer.py`

After `agentcogs init`, this stores customer `acme` in the same local ledger. No API key. `agentcogs status` then lists the sample and `acme`.

```bash
agentcogs init
python3 examples/own_customer.py
agentcogs status
```

```bash
python3 examples/priced_from_usage.py
```

## `one_run.py`

Posts one recorded cost for `vellum_research` / `research_agent` through the same ingest the SDK uses. It does not call a model. Open that customer and the new run is the top row.

See [docs/quickstart.md](../docs/quickstart.md).
