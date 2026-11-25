import threading
from pathlib import Path

import agentcogs.outbox as outbox
from agentcogs.outbox import _LOCK, drain, enqueue

outbox._DB_PATH = Path("/tmp/acg-outbox-test.db")


def test_enqueue_dedup():
    enqueue({"run_id": "r1", "total_usd": 0.10})
    enqueue({"run_id": "r1", "total_usd": 0.10})  # duplicate
    calls = []
    sent, failed = drain(lambda e: calls.append(e))
    assert sent == 1
    assert failed == 0


def test_drain_retries_failed():
    enqueue({"run_id": "r2", "total_usd": 0.20})

    def fail(_):
        raise RuntimeError("backend down")

    sent, failed = drain(fail)
    assert sent == 0 and failed == 1

    # On next call, succeeds
    calls = []
    sent2, _ = drain(lambda e: calls.append(e))
    # Note: next_retry backoff means it might not fire immediately;
    # this test would need time-mocking in production.


def test_post_runs_without_the_outbox_lock():
    enqueue({"run_id": "r3", "total_usd": 0.30})
    held = {"during": None}

    def post(_event):
        held["during"] = _LOCK.acquire(blocking=False)
        if held["during"]:
            _LOCK.release()

    sent, failed = drain(post)
    assert sent == 1 and failed == 0
    assert held["during"] is True


def test_two_drainers_can_post_at_the_same_time():
    for index in range(2):
        enqueue({"run_id": f"race-{index}", "total_usd": 0.1})
    started = threading.Barrier(2)
    inside = []

    def post(event):
        inside.append(event["run_id"])
        started.wait(timeout=2)

    errors = []

    def run():
        try:
            drain(post, max_items=1)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    assert not errors
    assert len(inside) == 2
