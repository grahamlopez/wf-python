"""Parser for Claude Code --output-format stream-json stdout.

Parses NDJSON (text, tool_use, tool_result events) into the
standardized results dict.
"""

from __future__ import annotations

import json


def _empty_result(exit_code: int = 1) -> dict:
    return {
        "exitCode": exit_code,
        "messages": [],
        "usage": {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0,
            "cost": 0.0,
            "turns": 0,
        },
        "model": None,
        "provider": "anthropic",
    }


def parse(stdout: str) -> dict:
    """Parse Claude Code stream-json stdout into a results dict."""
    if not stdout or not stdout.strip():
        return _empty_result()

    messages: list[dict] = []
    usage_data: dict | None = None
    model: str | None = None
    provider: str | None = "anthropic"
    current_message: dict | None = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        event_type = event.get("type")
        if event_type == "assistant":
            message = None
            if isinstance(event.get("message"), dict):
                message = dict(event["message"])
                if "role" not in message:
                    message["role"] = "assistant"
                if not isinstance(message.get("content"), list):
                    message["content"] = []
            else:
                message = {"role": "assistant", "content": []}
            messages.append(message)
            current_message = message
            continue

        if event_type == "text":
            text = event.get("text")
            if text is None and isinstance(event.get("delta"), dict):
                text = event["delta"].get("text")
            if text is None and isinstance(event.get("content"), dict):
                text = event["content"].get("text")
            if text is None:
                continue
            if current_message is None:
                current_message = {"role": "assistant", "content": []}
                messages.append(current_message)
            if not isinstance(current_message.get("content"), list):
                current_message["content"] = []
            current_message["content"].append({"type": "text", "text": text})
            continue

        if event_type == "tool_use":
            name = event.get("name") or event.get("tool_name")
            if not name:
                continue
            arguments = event.get("input")
            if arguments is None:
                arguments = event.get("arguments")
            if arguments is None:
                arguments = event.get("params")
            if arguments is None:
                arguments = {}
            if current_message is None:
                current_message = {"role": "assistant", "content": []}
                messages.append(current_message)
            if not isinstance(current_message.get("content"), list):
                current_message["content"] = []
            current_message["content"].append(
                {"type": "toolCall", "name": name, "arguments": arguments}
            )
            continue

        if event_type == "result":
            if isinstance(event.get("usage"), dict):
                usage_data = event["usage"]
            if isinstance(event.get("model"), str):
                model = event["model"]
            if isinstance(event.get("provider"), str):
                provider = event["provider"]
            continue

    if not messages and usage_data is None and model is None:
        return _empty_result()

    usage = {
        "input": int((usage_data or {}).get("input_tokens", 0) or 0),
        "output": int((usage_data or {}).get("output_tokens", 0) or 0),
        "cacheRead": int((usage_data or {}).get("cache_read_input_tokens", 0) or 0),
        "cacheWrite": int((usage_data or {}).get("cache_creation_input_tokens", 0) or 0),
        "cost": float((usage_data or {}).get("cost", 0) or 0),
        "turns": int((usage_data or {}).get("turns", 0) or 0),
    }

    if usage["turns"] == 0:
        usage["turns"] = sum(1 for msg in messages if msg.get("role") == "assistant")

    return {
        "exitCode": 0,
        "messages": messages,
        "usage": usage,
        "model": model,
        "provider": provider,
    }
