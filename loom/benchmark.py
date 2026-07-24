"""Benchmark — measures latency, tokens, price, tool calls, context.

Commands:
  /bench — run a quick benchmark
"""

from __future__ import annotations

import time
from .config import Config
from .provider import build_chat_model


def run_benchmark(config: Config) -> dict:
    results = {
        "latency": 0,
        "tokens": {"input": 0, "output": 0},
        "tool_calls": 0,
        "model": config.model,
        "provider": config.provider,
    }

    llm = build_chat_model(config=config)
    test_prompt = "Say hello in one word."

    start = time.time()
    try:
        response = llm.invoke([{"role": "user", "content": test_prompt}])
        results["latency"] = round(time.time() - start, 2)
        if hasattr(response, "usage_metadata"):
            meta = response.usage_metadata
            results["tokens"]["input"] = getattr(meta, "input_tokens", 0)
            results["tokens"]["output"] = getattr(meta, "output_tokens", 0)
        elif hasattr(response, "response_metadata"):
            meta = response.response_metadata
            usage = meta.get("token_usage", meta.get("usage", {}))
            if isinstance(usage, dict):
                results["tokens"]["input"] = usage.get("input_tokens", usage.get("prompt_tokens", 0))
                results["tokens"]["output"] = usage.get("output_tokens", usage.get("completion_tokens", 0))
        results["response"] = str(response.content)[:200]
    except Exception as exc:
        results["error"] = str(exc)

    return results