# Persona Editor

Non-technical UI for tuning AgentCOGS demo personas.

## Install

```bash
pip install -r tools/persona_editor/requirements.txt
```

## Run

```bash
streamlit run tools/persona_editor/app.py
```

Opens at http://localhost:8501

## Workflow

1. Pick a persona from the sidebar
2. Edit revenue, usage, workflow mix, model mix
3. Preview the projected monthly profile
4. Click **Save in place** — overwrites `tools/personas.py`
5. Re-run `./tools/seed_demo.sh` to regenerate demo data
