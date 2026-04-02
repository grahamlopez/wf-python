"""Workflow record file I/O. The central state manager.

Every phase reads and writes through this module.
"""

from __future__ import annotations

from wflib.types import (
    DesignDecision,
    ImplementationRecord,
    Plan,
    ReviewRecord,
    TaskResult,
    Usage,
    WorkflowConfig,
    WorkflowRecord,
)

WORKFLOWS_DIR = "docs/workflows"


def record_path(name: str, cwd: str) -> str:
    """Absolute path to docs/workflows/<name>.json."""
    raise NotImplementedError("record_path: not yet implemented")


def ensure_workflows_dir(cwd: str) -> str:
    """Create docs/workflows/ if needed. Returns absolute path."""
    raise NotImplementedError("ensure_workflows_dir: not yet implemented")


# --- CRUD ---

def create_record(
    name: str,
    cwd: str,
    source_branch: str,
    source_commit: str,
    worktree: str | None = None,
    config: WorkflowConfig | None = None,
) -> WorkflowRecord:
    """Create a new record file. Generates workflow ID.
    Writes to docs/workflows/<name>.json. Raises if name already exists.
    """
    raise NotImplementedError("create_record: not yet implemented")


def load_record(name: str, cwd: str) -> WorkflowRecord:
    """Load a record from disk. Raises FileNotFoundError if missing, ValueError if malformed."""
    raise NotImplementedError("load_record: not yet implemented")


def save_record(record: WorkflowRecord, cwd: str) -> None:
    """Write record to disk. Atomic write (write tmp + rename)."""
    raise NotImplementedError("save_record: not yet implemented")


def list_records(cwd: str) -> list[WorkflowRecord]:
    """Scan docs/workflows/ for all record files. Returns loaded records.
    Skips malformed files with a warning.
    """
    raise NotImplementedError("list_records: not yet implemented")


# --- Phase transitions ---

def record_brainstorm(
    record: WorkflowRecord,
    motivation: str,
    solution: str,
    design_decisions: list[DesignDecision],
    usage: Usage,
) -> None:
    """Write brainstorm data into the record. Sets status to 'planning'."""
    raise NotImplementedError("record_brainstorm: not yet implemented")


def record_plan(
    record: WorkflowRecord,
    plan: Plan,
    usage: Usage,
) -> None:
    """Write plan data into the record. Sets status to 'implementing'."""
    raise NotImplementedError("record_plan: not yet implemented")


def record_implementation_start(
    record: WorkflowRecord,
    base_commit: str,
) -> None:
    """Mark implementation as started. Sets base_commit."""
    raise NotImplementedError("record_implementation_start: not yet implemented")


def record_task_start(record: WorkflowRecord, task_id: str, worktree_path: str | None = None) -> None:
    """Mark a task as running with startedAt timestamp."""
    raise NotImplementedError("record_task_start: not yet implemented")


def record_task_complete(record: WorkflowRecord, task_id: str, result: TaskResult) -> None:
    """Record a task's result."""
    raise NotImplementedError("record_task_complete: not yet implemented")


def record_event(record: WorkflowRecord, event: str, task: str | None = None, detail: str | None = None) -> None:
    """Append an operational event to implementation.events."""
    raise NotImplementedError("record_event: not yet implemented")


def clear_active_resource(record: WorkflowRecord, task_id: str) -> None:
    """Remove a worktree from activeResources after cleanup."""
    raise NotImplementedError("clear_active_resource: not yet implemented")


def record_implementation_complete(record: WorkflowRecord) -> None:
    """Mark implementation as done. Sets completed_at. Sets status to 'reviewing'."""
    raise NotImplementedError("record_implementation_complete: not yet implemented")


def record_review(
    record: WorkflowRecord,
    review_text: str,
    findings_actionable: bool,
    usage: Usage,
    base_commit: str | None = None,
    fixup_plan: Plan | None = None,
) -> ReviewRecord:
    """Append a review entry to reviews[]. Returns the new ReviewRecord."""
    raise NotImplementedError("record_review: not yet implemented")


def record_fixup_complete(
    review: ReviewRecord,
    implementation: ImplementationRecord,
) -> None:
    """Attach fixup implementation results to a review entry."""
    raise NotImplementedError("record_fixup_complete: not yet implemented")


def record_close(
    record: WorkflowRecord,
    merge_result: str,
    final_commit: str | None,
    diff_stat: str,
) -> None:
    """Write close data into the record. Sets status to 'done'."""
    raise NotImplementedError("record_close: not yet implemented")


# --- Query helpers ---

def get_plan(record: WorkflowRecord) -> Plan | None:
    """Extract a Plan object from the record's plan phase."""
    raise NotImplementedError("get_plan: not yet implemented")


def get_implementation_state(record: WorkflowRecord) -> dict[str, TaskResult]:
    """Get current task statuses/results from the implementation phase."""
    raise NotImplementedError("get_implementation_state: not yet implemented")


def get_total_usage(record: WorkflowRecord) -> Usage:
    """Aggregate usage across all phases."""
    raise NotImplementedError("get_total_usage: not yet implemented")
