"""Workflow record file I/O. The central state manager.

Every phase reads and writes through this module.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile

from wflib._util import utc_now_iso
from wflib.types import (
    BrainstormRecord,
    CloseRecord,
    DesignDecision,
    ImplementationEvent,
    ImplementationEventType,
    ImplementationRecord,
    Plan,
    PlanRecord,
    ReviewRecord,
    TaskResult,
    TaskStatus,
    Usage,
    WorkflowConfig,
    WorkflowMeta,
    WorkflowRecord,
    WorkflowStatus,
    record_from_json,
    record_to_json,
)

WORKFLOWS_DIR = "docs/workflows"


def record_path(name: str, cwd: str) -> str:
    """Absolute path to docs/workflows/<name>.json."""
    return os.path.join(os.path.abspath(cwd), WORKFLOWS_DIR, f"{name}.json")


def ensure_workflows_dir(cwd: str) -> str:
    """Create docs/workflows/ if needed. Returns absolute path."""
    path = os.path.join(os.path.abspath(cwd), WORKFLOWS_DIR)
    os.makedirs(path, exist_ok=True)
    return path


# Timestamp helper re-exported from _util for backward compat
_now_iso = utc_now_iso


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
    ensure_workflows_dir(cwd)
    path = record_path(name, cwd)
    if os.path.exists(path):
        raise FileExistsError(f"Record '{name}' already exists")

    workflow_id = secrets.token_hex(2)
    created_at = _now_iso()
    meta = WorkflowMeta(
        id=workflow_id,
        name=name,
        created_at=created_at,
        status=WorkflowStatus.INIT,
        project=os.path.abspath(cwd),
        source_branch=source_branch,
        source_commit=source_commit,
        worktree=worktree,
        config=config or WorkflowConfig(),
    )
    record = WorkflowRecord(workflow=meta)

    save_record(record, cwd)
    return record


def load_record(name: str, cwd: str) -> WorkflowRecord:
    """Load a record from disk. Raises FileNotFoundError if missing, ValueError if malformed."""
    path = record_path(name, cwd)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed record JSON: {path}") from exc

    try:
        return record_from_json(data)
    except ValueError as exc:
        raise ValueError(f"Malformed record data: {path}") from exc


def save_record(record: WorkflowRecord, cwd: str) -> None:
    """Write record to disk. Atomic write (write tmp + rename)."""
    workflows_dir = ensure_workflows_dir(cwd)
    path = record_path(record.workflow.name, cwd)
    payload = record_to_json(record)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=workflows_dir,
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp_name = handle.name

    os.replace(temp_name, path)


def list_records(cwd: str) -> list[WorkflowRecord]:
    """Scan docs/workflows/ for all record files. Returns loaded records.
    Skips malformed files with a warning.
    """
    workflows_dir = os.path.join(os.path.abspath(cwd), WORKFLOWS_DIR)
    if not os.path.isdir(workflows_dir):
        return []

    records: list[WorkflowRecord] = []
    for filename in sorted(os.listdir(workflows_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(workflows_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            records.append(record_from_json(data))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            sys.stderr.write(f"Warning: failed to load record '{path}': {exc}\n")
            continue

    return records


# --- Phase transitions ---

def record_brainstorm(
    record: WorkflowRecord,
    motivation: str,
    solution: str,
    design_decisions: list[DesignDecision],
    usage: Usage,
) -> None:
    """Write brainstorm data into the record. Sets status to 'planning'."""
    record.brainstorm = BrainstormRecord(
        recorded_at=_now_iso(),
        motivation=motivation,
        solution=solution,
        design_decisions=design_decisions,
        usage=usage,
    )
    record.workflow.status = WorkflowStatus.PLANNING


def record_plan(
    record: WorkflowRecord,
    plan: Plan,
    usage: Usage,
) -> None:
    """Write plan data into the record. Sets status to 'implementing'."""
    record.plan = PlanRecord(
        recorded_at=_now_iso(),
        goal=plan.goal,
        context=plan.context,
        default_model=plan.default_model,
        tasks=plan.tasks,
        usage=usage,
    )
    record.implementation = ImplementationRecord(
        tasks={
            task.id: TaskResult(status=TaskStatus.PENDING)
            for task in plan.tasks
        }
    )
    record.workflow.status = WorkflowStatus.IMPLEMENTING


def record_implementation_start(
    record: WorkflowRecord,
    base_commit: str,
) -> None:
    """Mark implementation as started. Sets base_commit."""
    if record.implementation is None:
        record.implementation = ImplementationRecord()
    record.implementation.started_at = _now_iso()
    record.implementation.base_commit = base_commit


def record_task_start(record: WorkflowRecord, task_id: str, worktree_path: str | None = None) -> None:
    """Mark a task as running with startedAt timestamp."""
    if record.implementation is None:
        record.implementation = ImplementationRecord()
    result = record.implementation.tasks.get(task_id, TaskResult(status=TaskStatus.PENDING))
    result.status = TaskStatus.RUNNING
    result.started_at = _now_iso()
    if worktree_path is not None:
        result.worktree_path = worktree_path
        record.implementation.active_resources[task_id] = worktree_path
    record.implementation.tasks[task_id] = result
    record.implementation.events.append(
        ImplementationEvent(
            t=_now_iso(),
            event=ImplementationEventType.TASK_START,
            task=task_id,
        )
    )


def record_task_complete(record: WorkflowRecord, task_id: str, result: TaskResult) -> None:
    """Record a task's result."""
    if record.implementation is None:
        record.implementation = ImplementationRecord()
    record.implementation.tasks[task_id] = result
    record.implementation.events.append(
        ImplementationEvent(
            t=_now_iso(),
            event=ImplementationEventType.TASK_COMPLETE,
            task=task_id,
        )
    )


def record_event(record: WorkflowRecord, event: ImplementationEventType, task: str | None = None, detail: str | None = None) -> None:
    """Append an operational event to implementation.events.

    Args:
        record: The workflow record to update.
        event: The event type (must be an ImplementationEventType enum member).
        task: Optional task ID associated with the event.
        detail: Optional detail string.
    """
    if record.implementation is None:
        record.implementation = ImplementationRecord()
    record.implementation.events.append(
        ImplementationEvent(
            t=_now_iso(),
            event=event,
            task=task,
            detail=detail,
        )
    )


def clear_active_resource(record: WorkflowRecord, task_id: str) -> None:
    """Remove a worktree from activeResources after cleanup."""
    if record.implementation is None:
        return
    record.implementation.active_resources.pop(task_id, None)


def record_implementation_complete(record: WorkflowRecord) -> None:
    """Mark implementation as done. Sets completed_at. Sets status to 'reviewing'."""
    if record.implementation is None:
        record.implementation = ImplementationRecord()
    record.implementation.completed_at = _now_iso()
    record.workflow.status = WorkflowStatus.REVIEWING


def record_review(
    record: WorkflowRecord,
    review_text: str,
    findings_actionable: bool,
    usage: Usage,
    base_commit: str | None = None,
    fixup_plan: Plan | None = None,
) -> ReviewRecord:
    """Append a review entry to reviews[]. Returns the new ReviewRecord."""
    review = ReviewRecord(
        recorded_at=_now_iso(),
        base_commit=base_commit,
        review_text=review_text,
        findings_actionable=findings_actionable,
        usage=usage,
        fixup_plan=fixup_plan,
    )
    record.reviews.append(review)
    return review


def record_fixup_complete(
    review: ReviewRecord,
    implementation: ImplementationRecord,
) -> None:
    """Attach fixup implementation results to a review entry."""
    review.fixup_implementation = implementation


def record_close(
    record: WorkflowRecord,
    merge_result: str,
    final_commit: str | None,
    diff_stat: str,
) -> None:
    """Write close data into the record. Sets status to 'done'."""
    record.close = CloseRecord(
        recorded_at=_now_iso(),
        merge_result=merge_result,
        final_commit=final_commit,
        diff_stat=diff_stat,
    )
    record.workflow.status = WorkflowStatus.DONE


# --- Query helpers ---

def get_plan(record: WorkflowRecord) -> Plan | None:
    """Extract a Plan object from the record's plan phase."""
    if record.plan is None:
        return None
    plan = record.plan
    return Plan(
        goal=plan.goal,
        context=plan.context,
        tasks=plan.tasks,
        default_model=plan.default_model,
    )


def get_implementation_state(record: WorkflowRecord) -> dict[str, TaskResult]:
    """Get current task statuses/results from the implementation phase."""
    if record.implementation is None:
        return {}
    return record.implementation.tasks


def get_total_usage(record: WorkflowRecord) -> Usage:
    """Aggregate usage across all phases."""
    total = Usage()

    def add_usage(usage: Usage | None) -> None:
        if usage is None:
            return
        total.input += usage.input
        total.output += usage.output
        total.cache_read += usage.cache_read
        total.cache_write += usage.cache_write
        total.cost += usage.cost
        total.turns += usage.turns

    if record.brainstorm is not None:
        add_usage(record.brainstorm.usage)
    if record.plan is not None:
        add_usage(record.plan.usage)
    if record.implementation is not None:
        for result in record.implementation.tasks.values():
            add_usage(result.usage)
    for review in record.reviews:
        add_usage(review.usage)

    total.cost = round(total.cost, 6)
    return total
