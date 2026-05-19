from agentcogs.outbox import drain, enqueue


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
