"""Provider-specific token normalisation.

Critical: Anthropic prompt caching splits input tokens across THREE fields.
Reading only `input_tokens` undercounts by up to 90% on cache-hit calls.
"""
from typing import Any, Dict


def normalize_summary(by_model: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Convert Shekel's by_model summary into a uniform schema.

    Output schema per model:
        {
            "input_tokens":  int,   # already includes cache tokens for Claude
            "output_tokens": int,
            "usd":           float,
        }
    """
    out: Dict[str, Dict[str, Any]] = {}
    for model, stats in by_model.items():
        model_lower = model.lower()
        if "claude" in model_lower or "anthropic" in model_lower:
            input_total = (
                int(stats.get("input_tokens", 0) or 0)
                + int(stats.get("cache_read_input_tokens", 0) or 0)
                + int(stats.get("cache_creation_input_tokens", 0) or 0)
            )
        else:
            input_total = int(stats.get("input_tokens", 0) or 0)

        out[model] = {
            "input_tokens": input_total,
            "output_tokens": int(stats.get("output_tokens", 0) or 0),
            "usd": float(stats.get("cost", 0) or 0),
        }
    return out
