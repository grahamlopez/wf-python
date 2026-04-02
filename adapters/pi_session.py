"""Parser for pi session .jsonl files.

Parses pi session files (same message format as pi's SessionManager)
into the standardized results dict.
"""

from __future__ import annotations


def parse(session_dir: str, results_file: str) -> dict:
    """Parse pi session files into a results dict."""
    raise NotImplementedError("pi_session.parse: not yet implemented")
