from typing import Any


def empty_token_meta() -> dict[str, int]:
    return {"tokens_input": 0, "tokens_output": 0, "tokens_total": 0}


def _usage_value(usage: Any, *names: str) -> int:
    for name in names:
        if isinstance(usage, dict):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    return 0


def add_usage_to_meta(meta: dict[str, int], usage: Any) -> dict[str, int]:
    if not usage:
        return meta

    input_tokens = _usage_value(usage, "prompt_tokens", "input_tokens")
    output_tokens = _usage_value(usage, "completion_tokens", "output_tokens")
    total_tokens = _usage_value(usage, "total_tokens")

    if total_tokens and not (input_tokens or output_tokens):
        input_tokens = total_tokens
        output_tokens = 0

    meta["tokens_input"] += input_tokens
    meta["tokens_output"] += output_tokens
    meta["tokens_total"] = meta["tokens_input"] + meta["tokens_output"]
    return meta
