"""Official provider usage objects become priced lanes."""

from decimal import ROUND_HALF_UP, Decimal

from agentcogs._shekel_compat import lanes_from_usage
from agentcogs.kernel.attribute import price_call
from agentcogs.localstore import price_book
from agentcogs.provider_watch import micro_as_usd, priced_calls


def _server_micro(value) -> int:
    quant = Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return int(quant * Decimal(1_000_000))


def test_chat_completions_usage_is_not_dropped():
    lanes = lanes_from_usage(
        "openai",
        {
            "prompt_tokens": 12000,
            "completion_tokens": 20,
            "prompt_tokens_details": {"cached_tokens": 4000, "cache_write_tokens": 3000},
            "completion_tokens_details": {"reasoning_tokens": 5},
        },
    )
    assert lanes["uncached_input"] == 5000
    assert lanes["cache_read"] == 4000
    assert lanes["cache_write_30m"] == 3000
    assert lanes["output"] == 20
    assert lanes["reasoning"] == 5
    _priced, total = price_call(lanes, price_book())
    assert total == 27750


def test_responses_usage_still_prices_the_split_write():
    lanes = lanes_from_usage(
        "openai",
        {
            "input_tokens": 12000,
            "input_tokens_details": {"cached_tokens": 4000},
            "cache_write_tokens_details": {"ttl_30m_tokens": 3000, "ttl_12h_tokens": 4000},
            "output_tokens": 0,
            "output_tokens_details": {"reasoning_tokens": 50},
        },
    )
    book = price_book()
    book["usd_per_million"] = {"input": 1, "output": 15}
    _priced, total = price_call(lanes, book)
    assert total == 15150


def test_priced_calls_round_trip_to_server_micros():
    priced = priced_calls(
        [
            {
                "provider": "anthropic",
                "model": "claude-3-5-haiku",
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 20,
                    "cache_read_input_tokens": 8000,
                    "cache_creation": {
                        "ephemeral_5m_input_tokens": 120,
                        "ephemeral_1h_input_tokens": 80,
                    },
                },
            }
        ]
    )
    assert priced is not None
    assert priced["calls"][0]["lanes"]["cache_write_5m"] == 120
    assert priced["calls"][0]["lanes"]["cache_write_1h"] == 80
    assert _server_micro(priced["total_usd"]) == priced["total_micro"]
    assert micro_as_usd(1) == 0.000001
    assert _server_micro(micro_as_usd(1)) == 1
