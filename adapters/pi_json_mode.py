"""Parser for pi --mode json stdout.

Parses NDJSON event stream (message_end, tool_result_end events) into
the standardized results dict with messages, usage, model, provider.
"""

from __future__ import annotations

import json
import logging


def _default_error_result() -> dict:
    return {
        "exitCode": 1,
        "messages": [],
        "usage": {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0,
            "cost": 0,
            "turns": 0,
        },
        "model": None,
        "provider": None,
    }


def parse(stdout: str) -> dict:
    """Parse pi --mode json stdout into a results dict."""
    if not stdout.strip():
        return _default_error_result()

    logger = logging.getLogger(__name__)
    messages: list[dict] = []
    usage = {
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
        "cost": 0,
        "turns": 0,
    }
    model: str | None = None
    provider: str | None = None
    exit_code = 0

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed JSON line in pi output")
            continue

        event_type = event.get("type")
        if event_type == "message_end":
            message = event.get("message") or {}
            message_usage = message.get("usage") or event.get("usage") or {}
            usage["input"] += message_usage.get("input", 0) or 0
            usage["output"] += message_usage.get("output", 0) or 0
            usage["cacheRead"] += message_usage.get("cacheRead", 0) or 0
            usage["cacheWrite"] += message_usage.get("cacheWrite", 0) or 0
            cost = message_usage.get("cost") or message.get("cost") or {}
            usage["cost"] += cost.get("total", 0) or 0

            if message.get("role") == "assistant":
                usage["turns"] += 1
                if model is None:
                    model = message.get("model")
                    provider = message.get("provider")
        elif event_type == "agent_end":
            messages = event.get("messages") or []
            if "exitCode" in event:
                exit_code = event.get("exitCode", exit_code)

    return {
        "exitCode": exit_code,
        "messages": messages,
        "usage": usage,
        "model": model,
        "provider": provider,
    }
