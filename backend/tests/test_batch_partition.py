"""A batch keeps one copy of a run id before it touches the ledger."""

from types import SimpleNamespace

from app.routes.ingest import _partition_batch


def _item(run_id: str, total: float, price_error=None):
    event = SimpleNamespace(run_id=run_id, total_usd=total, calls=None, segments=None)
    return {"event": event, "price_error": price_error}


def test_identical_conflict_and_unrelated_rows_share_one_request():
    same = _item("same", 0.40)
    prepared = [
        same,
        _item("same", 0.40),
        _item("conflict", 0.10),
        _item("conflict", 0.20),
        _item("other", 0.30),
    ]
    _partition_batch(prepared)
    roles = [item["batch_role"] for item in prepared]
    assert roles == ["insert", "duplicate", "insert", "conflict", "insert"]
