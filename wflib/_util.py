"""Tiny shared helpers — no wflib imports allowed (dependency root)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

# Project root: _util.py lives in wflib/, so parent.parent is the repo root.
_WF_ROOT = Path(__file__).resolve().parent.parent


def utc_now_iso() -> str:
    """Current UTC time as ISO-8601 with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts/ directory.

    Raises FileNotFoundError if the file does not exist.  Callers that
    want a silent fallback should catch the exception explicitly.
    """
    path = os.path.join(_WF_ROOT, "prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
