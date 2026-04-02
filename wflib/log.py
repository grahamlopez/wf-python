"""Debug logging - append-only JSONL file."""

from __future__ import annotations

import json
import os

from wflib._util import utc_now_iso
from wflib.types import TaskStatus

LOG_PATH = "~/.wf/debug.log"


def log(event: str, **data) -> None:
    """Append a JSON line to the debug log. Non-fatal."""
    try:
        log_path = os.path.expanduser(LOG_PATH)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        payload = {
            "at": utc_now_iso(),
            "event": event,
            **data,
        }
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
    except Exception:
        return


def status_snap(statuses: dict[str, TaskStatus]) -> str:
    """Compact status string: 'task-1:done task-2:running ...'"""
    parts = []
    for task_id in sorted(statuses.keys()):
        status = statuses[task_id]
        parts.append(f"{task_id}:{status.value}")
    return " ".join(parts)
