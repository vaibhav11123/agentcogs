from app.services.budget_hold import budget_decision, next_run_hold


def test_hold_needs_three_runs():
    assert next_run_hold([1.0, 2.0]) == 0.0


def test_hold_is_the_median_of_the_recent_runs():
    assert next_run_hold([1.0, 3.0, 5.0, 0.0]) == 3.0


def test_decision_stops_when_the_next_typical_run_would_cross():
    assert budget_decision(spent=9.0, budget=10.0, hold=2.0) == "exceeded"
    assert budget_decision(spent=8.5, budget=10.0, hold=0.5) == "warn"
    assert budget_decision(spent=5.0, budget=10.0, hold=2.0) == "ok"


def test_decision_without_a_hold_matches_the_cap():
    assert budget_decision(spent=10.0, budget=10.0, hold=0.0) == "exceeded"
    assert budget_decision(spent=9.9, budget=10.0, hold=0.0) == "warn"
