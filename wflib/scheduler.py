"""DAG scheduler. Pure scheduling logic.

Manages task readiness, concurrency pool, dependency tracking.
Delegates per-task execution to task_executor.py.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

from wflib._util import utc_now_iso
from wflib.types import (
    ImplementationEvent,
    ImplementationEventType,
    ImplementationRecord,
    Plan,
    ReviewRecord,
    Task,
    TaskResult,
    TaskStatus,
    WorkflowConfig,
    WorkflowRecord,
)
# Cross-module import is spec-intentional — ExecutionSummary requires UsageRow per spec
from wflib.render import UsageRow

Callback = Callable | None


@dataclass
class ExecutionSummary:
    counts: dict[str, int] = field(default_factory=dict)  # {done: N, failed: N, skipped: N, pending: N}
    duration_seconds: int = 0
    usage_rows: list[UsageRow] = field(default_factory=list)
    base_commit: str | None = None


def get_ready_tasks(plan: Plan, statuses: dict[str, TaskStatus]) -> list[Task]:
    """Tasks that are pending with all deps done.

    Returns tasks sorted lexicographically by task.id for deterministic
    tie-breaking when multiple tasks become ready simultaneously.
    """
    ready = []
    for task in plan.tasks:
        status = statuses.get(task.id, TaskStatus.PENDING)
        if status != TaskStatus.PENDING:
            continue
        # All deps must be done
        deps_met = all(
            statuses.get(dep_id) == TaskStatus.DONE
            for dep_id in task.depends_on
        )
        if deps_met:
            ready.append(task)
    # Lexicographic order by task.id for deterministic tie-breaking
    ready.sort(key=lambda t: t.id)
    return ready


def skip_dependents(plan: Plan, statuses: dict[str, TaskStatus], failed_id: str) -> list[str]:
    """Mark transitive dependents of a failed task as skipped. Returns skipped IDs.

    Walks the dependency graph transitively: if task A failed and task B
    depends on A, and task C depends on B, both B and C are skipped.
    Only skips tasks that are still pending.
    """
    # Build a forward dependency map: task_id -> set of tasks that depend on it
    dependents: dict[str, list[str]] = {}
    for task in plan.tasks:
        for dep_id in task.depends_on:
            dependents.setdefault(dep_id, []).append(task.id)

    # BFS to find all transitive dependents
    skipped: list[str] = []
    queue = [failed_id]
    visited: set[str] = {failed_id}

    while queue:
        current = queue.pop(0)
        for dep_task_id in dependents.get(current, []):
            if dep_task_id in visited:
                continue
            visited.add(dep_task_id)
            if statuses.get(dep_task_id) == TaskStatus.PENDING:
                statuses[dep_task_id] = TaskStatus.SKIPPED
                skipped.append(dep_task_id)
            # Continue traversal even if already skipped/failed, to reach deeper dependents
            queue.append(dep_task_id)

    return skipped


def reset_ready_skipped(plan: Plan, statuses: dict[str, TaskStatus]) -> list[str]:
    """After success, reset skipped tasks whose deps are now all done. Returns reset IDs.

    When a previously-failed task is re-run and succeeds, its dependents
    may have been skipped. This function resets those skipped tasks back
    to pending if all their dependencies are now done.
    """
    reset_ids: list[str] = []
    changed = True
    # Iterate until no more changes (handles chains of skipped tasks)
    while changed:
        changed = False
        for task in plan.tasks:
            if statuses.get(task.id) != TaskStatus.SKIPPED:
                continue
            deps_met = all(
                statuses.get(dep_id) == TaskStatus.DONE
                for dep_id in task.depends_on
            )
            if deps_met:
                statuses[task.id] = TaskStatus.PENDING
                reset_ids.append(task.id)
                changed = True
    return reset_ids


def resolve_task_model(
    task: Task,
    plan: Plan,
    config: WorkflowConfig,
    cli_model: str | None = None,
) -> tuple[str | None, str]:
    """Returns (model_name, source). Precedence chain:
    cli_model > task.model > plan.defaultModel > config.model.implement > None.

    The returned model_name is a wf canonical name or user-written string.
    It has NOT been through profile.resolve_model yet — that happens inside
    build_headless_cmd / build_tmux_wrapper.
    """
    if cli_model is not None:
        return (cli_model, "cli")
    if task.model is not None:
        return (task.model, "task")
    if plan.default_model is not None:
        return (plan.default_model, "plan")
    if config.model.implement is not None:
        return (config.model.implement, "config")
    return (None, "default")


def recover_running_tasks(
    record: WorkflowRecord,
    cwd: str,
) -> dict:
    """Recover from a crashed execution.

    Iterates tasks in RUNNING state and:
    - Checks for orphaned results.json files and incorporates results (best-effort)
    - Deletes orphaned results.json files after incorporation
    - Cleans up orphaned worktrees
    - Resets RUNNING tasks to PENDING
    - Records CRASH_RECOVERY events

    Returns a summary dict::

        {'cleaned_worktrees': [...], 'reset_tasks': [...], 'incorporated_results': [...]}
    """
    import os as _os
    from wflib import record as record_mod
    from wflib.runner import _read_agent_results
    from wflib.worktree import cleanup_worktree, WorktreeInfo

    if record.implementation is None:
        return {"cleaned_worktrees": [], "reset_tasks": [], "incorporated_results": []}

    impl = record.implementation
    cleaned_worktrees: list[str] = []
    reset_tasks: list[str] = []
    incorporated_results: list[str] = []

    sessions_dir = _os.path.join(
        _os.path.abspath(cwd), record_mod.WORKFLOWS_DIR,
        ".sessions", record.workflow.name,
    )

    for task_id, result in impl.tasks.items():
        if result.status != TaskStatus.RUNNING:
            continue

        # Check for orphaned results.json and incorporate if present
        if _os.path.isdir(sessions_dir):
            orphaned_results_path = _os.path.join(
                sessions_dir, f"{task_id}.results.json"
            )
            if _os.path.isfile(orphaned_results_path):
                try:
                    agent_result = _read_agent_results(orphaned_results_path)
                    if agent_result.summary:
                        result.summary = agent_result.summary
                    if agent_result.notes:
                        result.notes = agent_result.notes
                    if agent_result.usage:
                        result.usage = agent_result.usage
                    incorporated_results.append(task_id)
                    _os.remove(orphaned_results_path)
                except Exception:
                    pass  # Best-effort incorporation

        # Clean up orphaned worktree if recorded
        wt_path = impl.active_resources.get(task_id)
        if wt_path:
            try:
                branch = f"wf-{record.workflow.id}-{task_id}"
                from wflib.git import get_current_branch
                try:
                    main_branch = get_current_branch(cwd)
                except RuntimeError:
                    main_branch = "main"
                wt = WorktreeInfo(path=wt_path, branch=branch, main_branch=main_branch)
                cleanup_worktree(cwd, wt)
                cleaned_worktrees.append(wt_path)
            except Exception:
                pass  # Best-effort cleanup
            record_mod.clear_active_resource(record, task_id)

        # Reset to pending
        result.status = TaskStatus.PENDING
        result.started_at = None
        reset_tasks.append(task_id)

        record_mod.record_event(
            record,
            ImplementationEventType.CRASH_RECOVERY,
            task=task_id,
            detail="Reset running task to pending after crash recovery",
        )

    return {
        "cleaned_worktrees": cleaned_worktrees,
        "reset_tasks": reset_tasks,
        "incorporated_results": incorporated_results,
    }


def _build_statuses(impl: ImplementationRecord) -> dict[str, TaskStatus]:
    """Extract current task statuses from an implementation record."""
    return {
        task_id: result.status
        for task_id, result in impl.tasks.items()
    }


def _build_summary(
    plan: Plan,
    impl: ImplementationRecord,
    duration_seconds: int,
    base_commit: str | None,
) -> ExecutionSummary:
    """Build an ExecutionSummary from the final state of an implementation."""
    counts = {"done": 0, "failed": 0, "skipped": 0, "pending": 0}
    usage_rows: list[UsageRow] = []

    for task in plan.tasks:
        result = impl.tasks.get(task.id)
        if result is None:
            counts["pending"] += 1
            continue
        status_key = result.status.value
        counts[status_key] = counts.get(status_key, 0) + 1

        usage_rows.append(UsageRow(
            label=task.id,
            input=result.usage.input,
            output=result.usage.output,
            cache_read=result.usage.cache_read,
            cache_write=result.usage.cache_write,
            cost=result.usage.cost,
            turns=result.usage.turns,
            model=result.usage.model,
        ))

    return ExecutionSummary(
        counts=counts,
        duration_seconds=duration_seconds,
        usage_rows=usage_rows,
        base_commit=base_commit,
    )


async def execute_plan(
    record: WorkflowRecord,
    cwd: str,
    cli_overrides: dict | None = None,
    on_task_start: Callback = None,
    on_task_complete: Callback = None,
    on_state_change: Callback = None,
) -> ExecutionSummary:
    """Execute all pending tasks via DAG scheduling.

    Reads all settings from record.workflow.config (the init-time snapshot).
    cli_overrides (from command-line flags) are applied on top for this
    invocation only via config.apply_cli_overrides().

    Pool-based: tasks start as soon as deps complete, up to concurrency limit.
    When multiple tasks become ready simultaneously, they are started in
    lexicographic order by task.id (deterministic tie-breaking).
    """
    from wflib import record as record_mod
    from wflib.config import apply_cli_overrides
    from wflib.git import get_head_full
    from wflib.worktree import commit_or_amend_workflow_files
    from wflib.task_executor import run_task

    # Apply CLI overrides to get effective config
    config = record.workflow.config
    if cli_overrides:
        config = apply_cli_overrides(config, **cli_overrides)

    # Get the plan
    plan = record_mod.get_plan(record)
    if plan is None:
        raise RuntimeError("No plan found in record")

    # Ensure implementation record exists
    if record.implementation is None:
        record.implementation = ImplementationRecord(
            tasks={
                task.id: TaskResult(status=TaskStatus.PENDING)
                for task in plan.tasks
            }
        )

    impl = record.implementation

    # --- Crash recovery ---
    # Reset any RUNNING tasks from a previous crashed execution.
    recover_running_tasks(record, cwd)

    # Auto-commit record before starting
    record_mod.save_record(record, cwd)
    try:
        commit_or_amend_workflow_files(cwd, record.workflow.name)
    except Exception:
        pass  # Best-effort commit

    # Record base commit and start time
    base_commit = get_head_full(cwd)
    record_mod.record_implementation_start(record, base_commit or "")
    record_mod.save_record(record, cwd)

    start_time = time.monotonic()

    # Resolve cli_model from overrides
    cli_model = (cli_overrides or {}).get("model_implement")

    concurrency = config.execute.concurrency
    merge_lock = asyncio.Lock()

    # --- DAG scheduling loop ---
    running_tasks: dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task

    statuses = _build_statuses(impl)

    while True:
        # Get ready tasks (pending with all deps done)
        ready = get_ready_tasks(plan, statuses)

        # Launch tasks up to concurrency limit
        for task in ready:
            if len(running_tasks) >= concurrency:
                break
            if task.id in running_tasks:
                continue

            # Mark as running in statuses so we don't re-launch
            statuses[task.id] = TaskStatus.RUNNING

            # Record task start
            record_mod.record_task_start(record, task.id)
            record_mod.save_record(record, cwd)

            if on_task_start:
                on_task_start(task.id)
            if on_state_change:
                on_state_change(task.id, "running")

            # Launch the task
            async_task = asyncio.create_task(
                run_task(
                    task=task,
                    plan=plan,
                    record=record,
                    cwd=cwd,
                    merge_lock=merge_lock,
                    config=config,
                    cli_model=cli_model,
                )
            )
            running_tasks[task.id] = async_task

        # If nothing is running and nothing is ready, we're done
        if not running_tasks:
            break

        # Wait for at least one task to complete
        done_asyncio, _ = await asyncio.wait(
            running_tasks.values(),
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Process completed tasks
        for completed_task in done_asyncio:
            # Find the task_id for this asyncio.Task
            completed_id = None
            for tid, atask in running_tasks.items():
                if atask is completed_task:
                    completed_id = tid
                    break

            if completed_id is None:
                continue

            del running_tasks[completed_id]

            # Get the result
            try:
                result = completed_task.result()
            except Exception as exc:
                # Unexpected error — mark task as failed
                result = TaskResult(
                    status=TaskStatus.FAILED,
                    completed_at=utc_now_iso(),
                    error=str(exc),
                )

            # Record task completion
            record_mod.record_task_complete(record, completed_id, result)
            statuses[completed_id] = result.status
            record_mod.save_record(record, cwd)

            if on_task_complete:
                on_task_complete(completed_id, result)
            if on_state_change:
                on_state_change(completed_id, result.status.value)

            # Handle failure: skip dependents
            if result.status == TaskStatus.FAILED:
                skipped_ids = skip_dependents(plan, statuses, completed_id)
                if skipped_ids:
                    # Update the implementation record for skipped tasks
                    for sid in skipped_ids:
                        impl.tasks[sid] = TaskResult(status=TaskStatus.SKIPPED)
                    record_mod.record_event(
                        record,
                        ImplementationEventType.SKIP_DEPENDENTS,
                        task=completed_id,
                        detail=f"Skipped: {', '.join(skipped_ids)}",
                    )
                    record_mod.save_record(record, cwd)

            # Handle success: reset previously-skipped tasks
            if result.status == TaskStatus.DONE:
                reset_ids = reset_ready_skipped(plan, statuses)
                if reset_ids:
                    for rid in reset_ids:
                        impl.tasks[rid] = TaskResult(status=TaskStatus.PENDING)
                    record_mod.save_record(record, cwd)

    # Mark implementation complete
    record_mod.record_implementation_complete(record)
    record_mod.save_record(record, cwd)

    # Commit the final record
    try:
        commit_or_amend_workflow_files(cwd, record.workflow.name)
    except Exception:
        pass  # Best-effort commit

    duration = int(time.monotonic() - start_time)
    return _build_summary(plan, impl, duration, base_commit)


async def execute_single_task(
    record: WorkflowRecord,
    task_id: str,
    cwd: str,
    cli_overrides: dict | None = None,
) -> TaskResult:
    """Execute (or re-run) a single task.

    Reads settings from record.workflow.config, applies cli_overrides.
    Validates deps are met (all deps must be 'done'), then delegates
    to task_executor.run_task.
    """
    from wflib import record as record_mod
    from wflib.config import apply_cli_overrides
    from wflib.task_executor import run_task

    # Apply CLI overrides to get effective config
    config = record.workflow.config
    if cli_overrides:
        config = apply_cli_overrides(config, **cli_overrides)

    # Get the plan
    plan = record_mod.get_plan(record)
    if plan is None:
        raise RuntimeError("No plan found in record")

    # Find the task
    task = None
    for t in plan.tasks:
        if t.id == task_id:
            task = t
            break
    if task is None:
        raise ValueError(f"Task '{task_id}' not found in plan")

    # Ensure implementation record exists
    if record.implementation is None:
        record.implementation = ImplementationRecord(
            tasks={
                t.id: TaskResult(status=TaskStatus.PENDING)
                for t in plan.tasks
            }
        )

    # Validate dependencies are met
    for dep_id in task.depends_on:
        dep_result = record.implementation.tasks.get(dep_id)
        if dep_result is None or dep_result.status != TaskStatus.DONE:
            raise RuntimeError(
                f"Dependency '{dep_id}' is not done "
                f"(status: {dep_result.status.value if dep_result else 'missing'})"
            )

    # Resolve cli_model from overrides
    cli_model = (cli_overrides or {}).get("model_implement")

    merge_lock = asyncio.Lock()

    # Record task start
    record_mod.record_task_start(record, task_id)
    record_mod.save_record(record, cwd)

    # Run the task
    try:
        result = await run_task(
            task=task,
            plan=plan,
            record=record,
            cwd=cwd,
            merge_lock=merge_lock,
            config=config,
            cli_model=cli_model,
        )
    except Exception as exc:
        result = TaskResult(
            status=TaskStatus.FAILED,
            completed_at=utc_now_iso(),
            error=str(exc),
        )

    # Record task completion
    record_mod.record_task_complete(record, task_id, result)
    record_mod.save_record(record, cwd)

    return result


async def execute_fixup(
    review: ReviewRecord,
    record: WorkflowRecord,
    cwd: str,
    cli_overrides: dict | None = None,
) -> ExecutionSummary:
    """Execute a fixup plan from a review.

    Same DAG scheduler and same run_task pipeline, but results are stored
    in review.fixup_implementation instead of record.implementation.

    Fixup model precedence:
      1. cli_overrides["fixup_model"] (from --fixup-model CLI flag)
      2. config.model.fixup (from the init-time config snapshot)
      3. Falls through to resolve_task_model's normal chain
    """
    from wflib import record as record_mod
    from wflib.config import apply_cli_overrides
    from wflib.git import get_head_full
    from wflib.worktree import commit_or_amend_workflow_files
    from wflib.task_executor import run_task

    if review.fixup_plan is None:
        raise RuntimeError("No fixup plan found in review")

    plan = review.fixup_plan

    # Apply CLI overrides to get effective config
    config = record.workflow.config
    if cli_overrides:
        config = apply_cli_overrides(config, **cli_overrides)

    # Resolve fixup model: cli_overrides["fixup_model"] > config.model.fixup
    fixup_model = (cli_overrides or {}).get("fixup_model")
    if fixup_model is None:
        fixup_model = config.model.fixup
    # fixup_model acts as the cli_model parameter to the scheduler/run_task,
    # overriding the normal model resolution chain

    # Create a fresh fixup implementation record
    fixup_impl = ImplementationRecord(
        tasks={
            task.id: TaskResult(status=TaskStatus.PENDING)
            for task in plan.tasks
        }
    )
    review.fixup_implementation = fixup_impl

    # Record base commit and start time
    base_commit = get_head_full(cwd)
    fixup_impl.started_at = utc_now_iso()
    fixup_impl.base_commit = base_commit
    record_mod.save_record(record, cwd)

    start_time = time.monotonic()

    concurrency = config.execute.concurrency
    merge_lock = asyncio.Lock()

    # --- DAG scheduling loop (same as execute_plan) ---
    running_tasks: dict[str, asyncio.Task] = {}
    statuses = _build_statuses(fixup_impl)

    while True:
        ready = get_ready_tasks(plan, statuses)

        for task in ready:
            if len(running_tasks) >= concurrency:
                break
            if task.id in running_tasks:
                continue

            statuses[task.id] = TaskStatus.RUNNING

            # Record task start in the fixup implementation
            task_result = fixup_impl.tasks.get(task.id, TaskResult(status=TaskStatus.PENDING))
            task_result.status = TaskStatus.RUNNING
            task_result.started_at = utc_now_iso()
            fixup_impl.tasks[task.id] = task_result
            fixup_impl.events.append(ImplementationEvent(
                t=utc_now_iso(),
                event=ImplementationEventType.TASK_START,
                task=task.id,
            ))
            record_mod.save_record(record, cwd)

            async_task = asyncio.create_task(
                run_task(
                    task=task,
                    plan=plan,
                    record=record,
                    cwd=cwd,
                    merge_lock=merge_lock,
                    config=config,
                    cli_model=fixup_model,
                )
            )
            running_tasks[task.id] = async_task

        if not running_tasks:
            break

        done_asyncio, _ = await asyncio.wait(
            running_tasks.values(),
            return_when=asyncio.FIRST_COMPLETED,
        )

        for completed_task in done_asyncio:
            completed_id = None
            for tid, atask in running_tasks.items():
                if atask is completed_task:
                    completed_id = tid
                    break

            if completed_id is None:
                continue

            del running_tasks[completed_id]

            try:
                result = completed_task.result()
            except Exception as exc:
                result = TaskResult(
                    status=TaskStatus.FAILED,
                    completed_at=utc_now_iso(),
                    error=str(exc),
                )

            # Store result in fixup implementation
            fixup_impl.tasks[completed_id] = result
            statuses[completed_id] = result.status
            fixup_impl.events.append(ImplementationEvent(
                t=utc_now_iso(),
                event=ImplementationEventType.TASK_COMPLETE,
                task=completed_id,
            ))
            record_mod.save_record(record, cwd)

            if result.status == TaskStatus.FAILED:
                skipped_ids = skip_dependents(plan, statuses, completed_id)
                if skipped_ids:
                    for sid in skipped_ids:
                        fixup_impl.tasks[sid] = TaskResult(status=TaskStatus.SKIPPED)
                    record_mod.save_record(record, cwd)

            if result.status == TaskStatus.DONE:
                reset_ids = reset_ready_skipped(plan, statuses)
                if reset_ids:
                    for rid in reset_ids:
                        fixup_impl.tasks[rid] = TaskResult(status=TaskStatus.PENDING)
                    record_mod.save_record(record, cwd)

    # Mark fixup implementation complete
    fixup_impl.completed_at = utc_now_iso()
    record_mod.save_record(record, cwd)

    # Commit the final record
    try:
        commit_or_amend_workflow_files(cwd, record.workflow.name)
    except Exception:
        pass  # Best-effort commit

    duration = int(time.monotonic() - start_time)
    return _build_summary(plan, fixup_impl, duration, base_commit)
