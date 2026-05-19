from agentcogs.tokens import normalize_summary


def test_openai_passthrough():
    out = normalize_summary({
        "gpt-4o-mini": {"input_tokens": 100, "output_tokens": 50, "cost": 0.001}
    })
    assert out["gpt-4o-mini"]["input_tokens"] == 100


def test_anthropic_cache_tokens_summed():
    out = normalize_summary({
        "claude-3-5-sonnet": {
            "input_tokens": 500,
            "cache_read_input_tokens": 8000,
            "cache_creation_input_tokens": 200,
            "output_tokens": 100,
            "cost": 0.025,
        }
    })
    assert out["claude-3-5-sonnet"]["input_tokens"] == 8700
    assert out["claude-3-5-sonnet"]["output_tokens"] == 100


def test_missing_fields_default_zero():
    out = normalize_summary({"claude-3-haiku": {"output_tokens": 10}})
    assert out["claude-3-haiku"]["input_tokens"] == 0
