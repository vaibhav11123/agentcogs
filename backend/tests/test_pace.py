from datetime import datetime, timezone

from app.services.pace import project_month


def test_withholds_pace_on_the_first_two_days():
    early = datetime(2026, 11, 2, tzinfo=timezone.utc)
    assert project_month(100, 1000, early) == (None, None)


def test_projects_cost_and_margin_from_the_third_day():
    # 14th of a 30-day month. $1,400 so far -> $3,000 if the rate holds.
    now = datetime(2026, 11, 14, tzinfo=timezone.utc)
    cost, margin = project_month(1400, 3000, now)
    assert cost == 3000
    assert margin == 0


def test_no_margin_without_revenue():
    now = datetime(2026, 11, 14, tzinfo=timezone.utc)
    cost, margin = project_month(1400, 0, now)
    assert cost == 3000
    assert margin is None
