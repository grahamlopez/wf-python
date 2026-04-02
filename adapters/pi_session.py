"""Parser for pi session .jsonl files.

Parses pi session files (same message format as pi's SessionManager)
into the standardized results dict.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _default_usage() -> dict:
    return {
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
        "cost": 0.0,
        "turns": 0,
    }


def _error_result(reason: str) -> dict:
    return {
        "exitCode": 1,
        "messages": [],
        "usage": _default_usage(),
        "model": None,
        "provider": None,
        "error": reason,
    }


def _accumulate_usage(total: dict, usage: dict) -> None:
    total["input"] += int(usage.get("input", 0) or 0)
    total["output"] += int(usage.get("output", 0) or 0)
    total["cacheRead"] += int(usage.get("cacheRead", 0) or 0)
    total["cacheWrite"] += int(usage.get("cacheWrite", 0) or 0)
    total["turns"] += int(usage.get("turns", 0) or 0)

    cost = usage.get("cost")
    if isinstance(cost, dict):
        total["cost"] += float(cost.get("total", 0) or 0)
    elif isinstance(cost, (int, float)):
        total["cost"] += float(cost)


def _read_results_file(results_file: str) -> dict | None:
    if not results_file or not os.path.exists(results_file):
        return None
    try:
        with open(results_file, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        return None
    return None


def _latest_session_file(session_dir: str) -> Path | None:
    session_path = Path(session_dir)
    if not session_path.is_dir():
        return None
    session_files = list(session_path.glob("*.jsonl"))
    if not session_files:
        return None
    return max(session_files, key=lambda path: path.stat().st_mtime)


def parse(session_dir: str, results_file: str | None = None) -> dict:
    """Parse pi session files into a results dict."""
    results = _read_results_file(results_file) if results_file else None
    if results is not None:
        return results

    session_file = _latest_session_file(session_dir)
    if session_file is None:
        return _error_result(f"Session directory not found: {session_dir}")

    messages: list[dict[str, Any]] = []
    usage_totals = _default_usage()
    model: str | None = None
    provider: str | None = None

    try:
        with open(session_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if not isinstance(entry, dict) or entry.get("type") != "message":
                    continue

                message = entry.get("message")
                if not isinstance(message, dict):
                    continue

                role = message.get("role")
                if role not in {"user", "assistant"}:
                    continue

                content = message.get("content")
                if content is None:
                    content = []

                messages.append({"role": role, "content": content})

                if role == "assistant":
                    usage = message.get("usage")
                    if isinstance(usage, dict):
                        _accumulate_usage(usage_totals, usage)
                    if message.get("model"):
                        model = message["model"]
                    if message.get("provider"):
                        provider = message["provider"]
    except OSError as exc:
        return _error_result(f"Failed to read session file: {exc}")

    return {
        "exitCode": 0,
        "messages": messages,
        "usage": usage_totals,
        "model": model,
        "provider": provider,
    }
