"""DAG scheduler. Pure scheduling logic.

Manages task readiness, concurrency pool, dependency tracking.
Delegates per-task execution to task_executor.py.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable

from wflib.types import Plan, Task, TaskResult, TaskStatus, WorkflowConfig, WorkflowRecord
from wflib.render import UsageRow

Callback = Callable | None


@dataclass
class ExecutionSummary:
    counts: dict[str, int] = field(default_factory=dict)  # {done: N, failed: N, skipped: N, pending: N}
    duration_seconds: int = 0
    usage_rows: list[UsageRow] = field(default_factory=list)
    base_commit: str | None = None


async def execute_plan(
    record: WorkflowRecord,
    cwd: str,
    cli_overrides: dict | None = None,
    on_task_start: Callback = None,
    on_task_complete: Callback = None,
    on_state_change: Callback = None,
) -> ExecutionSummary:
    """Execute all pending tasks via DAG scheduling."""
    raise NotImplementedError("execute_plan: not yet implemented")


async def execute_single_task(
    record: WorkflowRecord,
    task_id: str,
    cwd: str,
    cli_overrides: dict | None = None,
) -> TaskResult:
    """Execute (or re-run) a single task."""
    raise NotImplementedError("execute_single_task: not yet implemented")


async def execute_fixup(
    review: 'ReviewRecord',
    record: WorkflowRecord,
    cwd: str,
    cli_overrides: dict | None = None,
) -> ExecutionSummary:
    """Execute a fixup plan from a review."""
    raise NotImplementedError("execute_fixup: not yet implemented")


def get_ready_tasks(plan: Plan, statuses: dict[str, TaskStatus]) -> list[Task]:
    """Tasks that are pending with all deps done."""
    raise NotImplementedError("get_ready_tasks: not yet implemented")


def skip_dependents(plan: Plan, statuses: dict[str, TaskStatus], failed_id: str) -> list[str]:
    """Mark transitive dependents of a failed task as skipped. Returns skipped IDs."""
    raise NotImplementedError("skip_dependents: not yet implemented")


def reset_ready_skipped(plan: Plan, statuses: dict[str, TaskStatus]) -> list[str]:
    """After success, reset skipped tasks whose deps are now all done. Returns reset IDs."""
    raise NotImplementedError("reset_ready_skipped: not yet implemented")


def resolve_task_model(
    task: Task,
    plan: Plan,
    config: WorkflowConfig,
    cli_model: str | None = None,
) -> tuple[str | None, str]:
    """Returns (model_name, source). Precedence chain:
    cli_model > task.model > plan.defaultModel > config.model.implement > None.
    """
    raise NotImplementedError("resolve_task_model: not yet implemented")
