"""Tests for synthetic event generation (reproducible fixtures)."""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TOOLS))

from generate_events import generate_run, iter_all_events  # noqa: E402
from personas import PERSONAS  # noqa: E402


def test_persona_count():
    from personas import ALL_PERSONAS, HERO_PERSONAS  # noqa: E402

    assert len(HERO_PERSONAS) == 7
    assert len(ALL_PERSONAS) == 40
    ids = {p.external_id for p in HERO_PERSONAS}
    assert "acme_corp" in ids
    assert "techflow_inc" in ids


def test_generate_run_shape():
    p = PERSONAS[0]
    ts = datetime.now(timezone.utc)
    ev = generate_run(p, ts)
    assert ev["customer_id"] == p.external_id
    assert ev["status"] == "completed"
    assert ev["total_usd"] > 0
    assert ev["models"]
    assert ev["node_costs"]


def test_reproducible_seed():
    random.seed(42)
    end = datetime(2026, 5, 16, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    events_a = list(iter_all_events(start, end))

    random.seed(42)
    events_b = list(iter_all_events(start, end))

    assert len(events_a) == len(events_b)
    assert sum(e["total_usd"] for e in events_a) == sum(e["total_usd"] for e in events_b)
    assert events_a[0]["customer_id"] == events_b[0]["customer_id"]


def test_anomaly_multiplier():
    random.seed(0)
    p = next(x for x in PERSONAS if x.external_id == "initech")
    ev = generate_run(p, datetime.now(timezone.utc), is_anomaly=True)
    assert ev["total_usd"] >= p.cost_per_run_mean * 4
    assert ev["metadata"]["anomaly"] is True
