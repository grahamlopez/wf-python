"""Parser for pi --mode json stdout.

Parses NDJSON event stream (message_end, tool_result_end events) into
the standardized results dict with messages, usage, model, provider.
"""

from __future__ import annotations


def parse(stdout: str) -> dict:
    """Parse pi --mode json stdout into a results dict."""
    raise NotImplementedError("pi_json_mode.parse: not yet implemented")
