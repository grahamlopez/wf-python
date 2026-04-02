"""Git worktree lifecycle - create, setup deps, merge back, cleanup."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorktreeInfo:
    path: str
    branch: str
    main_branch: str


@dataclass
class MergeResult:
    success: bool
    conflicts: str | None = None
    conflict_files: list[str] | None = None
    resolution_attempted: bool = False
    resolution_succeeded: bool = False


@dataclass
class WorkflowCloseResult:
    merge_state: str             # "clean" | "conflicted" | "failed"
    conflict_files: list[str] = field(default_factory=list)
    conflicts: str = ""
    diff_stat: str = ""


# --- Task worktrees (for parallel execution) ---

def create_task_worktree(cwd: str, workflow_id: str, task_id: str) -> WorktreeInfo:
    """Create worktree + branch from HEAD. Cleans up stale if exists."""
    raise NotImplementedError("create_task_worktree: not yet implemented")


def setup_worktree(main_cwd: str, worktree_path: str) -> None:
    """Run .worktree-setup if present, else symlink dep dirs."""
    raise NotImplementedError("setup_worktree: not yet implemented")


def symlink_deps(main_cwd: str, worktree_path: str) -> None:
    """Symlink node_modules, .venv, vendor, etc."""
    raise NotImplementedError("symlink_deps: not yet implemented")


def commit_if_dirty(worktree_path: str, task_id: str, title: str) -> bool:
    """Stage all + commit with [workflow] prefix. Returns True if committed."""
    raise NotImplementedError("commit_if_dirty: not yet implemented")


def merge_back(main_cwd: str, wt: WorktreeInfo) -> MergeResult:
    """Rebase onto main, then fast-forward merge. Serialized by caller."""
    raise NotImplementedError("merge_back: not yet implemented")


def cleanup_worktree(main_cwd: str, wt: WorktreeInfo) -> None:
    """Remove worktree + branch. Idempotent."""
    raise NotImplementedError("cleanup_worktree: not yet implemented")


# --- Workflow worktrees (for init/close multi-workflow isolation) ---

def create_workflow_worktree(cwd: str, workflow_name: str) -> WorktreeInfo:
    """Create ../<repo>-wf-<name>/ on branch wf-<name>."""
    raise NotImplementedError("create_workflow_worktree: not yet implemented")


def close_workflow_worktree(main_cwd: str, wt: WorktreeInfo) -> WorkflowCloseResult:
    """Rebase + merge, or fall back to merge --no-commit on conflict."""
    raise NotImplementedError("close_workflow_worktree: not yet implemented")


def commit_or_amend_workflow_files(cwd: str, workflow_name: str) -> bool:
    """Commit docs/workflows/. Amends if last commit is [workflow-init]."""
    raise NotImplementedError("commit_or_amend_workflow_files: not yet implemented")


def commit_remaining_changes(cwd: str, message: str) -> bool:
    """Stage all + commit with caller's message."""
    raise NotImplementedError("commit_remaining_changes: not yet implemented")
