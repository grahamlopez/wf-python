"""Parser for Claude Code --output-format stream-json stdout.

Parses NDJSON (text, tool_use, tool_result events) into the
standardized results dict.
"""

from __future__ import annotations


def parse(stdout: str) -> dict:
    """Parse Claude Code stream-json stdout into a results dict."""
    raise NotImplementedError("claude_stream_json.parse: not yet implemented")
