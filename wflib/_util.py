"""Tiny shared helpers — no wflib imports allowed (dependency root)."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Current UTC time as ISO-8601 with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
