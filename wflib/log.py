"""Debug logging - append-only JSONL file."""

from __future__ import annotations

from wflib.types import TaskStatus

LOG_PATH = "~/.wf/debug.log"


def log(event: str, **data) -> None:
    """Append a JSON line to the debug log. Non-fatal."""
    raise NotImplementedError("log: not yet implemented")


def status_snap(statuses: dict[str, TaskStatus]) -> str:
    """Compact status string: 'task-1:done task-2:running ...'"""
    raise NotImplementedError("status_snap: not yet implemented")
