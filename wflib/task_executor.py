"""Per-task execution lifecycle.

Owns the full pipeline for running a single task: worktree setup,
brief assembly, agent spawning, result processing, merge-back, and cleanup.
Called by the scheduler for each task.
"""

from __future__ import annotations

import asyncio

from wflib.types import Plan, Task, TaskResult, WorkflowConfig, WorkflowRecord
from wflib.worktree import MergeResult, WorktreeInfo
from profiles import RunnerProfile


async def run_task(
    task: Task,
    plan: Plan,
    record: WorkflowRecord,
    cwd: str,
    merge_lock: asyncio.Lock,
    config: WorkflowConfig,
    cli_model: str | None = None,
) -> TaskResult:
    """Execute a single task through the full lifecycle."""
    raise NotImplementedError("run_task: not yet implemented")


def _setup_worktree(
    task: Task,
    cwd: str,
    workflow_id: str,
) -> WorktreeInfo:
    """Create and setup a task worktree. Records active_resource."""
    raise NotImplementedError("_setup_worktree: not yet implemented")


def _capture_diff_stat(
    worktree_path: str,
    main_branch: str,
) -> tuple[list[str], str | None]:
    """Get files_changed and diff_stat from the worktree branch."""
    raise NotImplementedError("_capture_diff_stat: not yet implemented")


async def _merge_and_cleanup(
    cwd: str,
    wt: WorktreeInfo,
    task: Task,
    record: WorkflowRecord,
    merge_lock: asyncio.Lock,
    profile: RunnerProfile,
    model: str | None,
    config: WorkflowConfig,
) -> MergeResult:
    """Acquire merge lock, commit, rebase, merge, cleanup."""
    raise NotImplementedError("_merge_and_cleanup: not yet implemented")


def _preserve_results(
    results_path: str,
    workflow_name: str,
    task_id: str,
    cwd: str,
    session_dir: str | None = None,
    preserve_session: bool = False,
) -> None:
    """Copy results.json (always) and session file (on failure) to
    docs/workflows/.sessions/<workflow>/ for crash recovery.
    """
    raise NotImplementedError("_preserve_results: not yet implemented")
