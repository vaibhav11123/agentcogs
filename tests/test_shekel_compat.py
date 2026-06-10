import importlib.util
import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("shekel") is None,
    reason="shekel not installed",
)


def test_shekel_budget_summary_shape():
    from agentcogs._shekel_compat import budget, normalize_summary_data

    try:
        with budget(name="compat_test", max_usd=0.01) as ctx:
            raw = ctx.summary_data()
            summary = normalize_summary_data(raw)
    except AttributeError as exc:
        pytest.skip(f"shekel provider stack unavailable: {exc}")

    assert "by_model" in summary
    assert isinstance(summary["by_model"], dict)
    assert "total_cost" in summary
    assert summary["total_cost"] >= 0

    # by_model entries use the fields we consume when populated
    for _model, stats in summary["by_model"].items():
        assert "input_tokens" in stats or "cost" in stats
        assert "output_tokens" in stats or "cost" in stats
        assert "cost" in stats
