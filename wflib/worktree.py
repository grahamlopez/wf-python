"""Git worktree lifecycle - create, setup deps, merge back, cleanup."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import stat
import subprocess

from wflib.git import get_current_branch, get_dirty_files, git, is_clean


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
    main_branch = get_current_branch(cwd)
    branch = f"wf-{workflow_id}-{task_id}"
    worktree_path = f"{os.path.abspath(cwd)}-wf-{workflow_id}-{task_id}"
    wt = WorktreeInfo(path=worktree_path, branch=branch, main_branch=main_branch)
    cleanup_worktree(cwd, wt)
    result = git(["worktree", "add", "-b", branch, worktree_path], cwd=cwd)
    if not result.ok:
        raise RuntimeError(result.stderr.strip() or "git worktree add failed")
    return wt


def setup_worktree(main_cwd: str, worktree_path: str) -> None:
    """Run .worktree-setup if present, else symlink dep dirs."""
    hook_path = os.path.join(main_cwd, ".worktree-setup")
    if os.path.isfile(hook_path):
        mode = os.stat(hook_path).st_mode
        os.chmod(hook_path, mode | stat.S_IXUSR)
        subprocess.run([hook_path], cwd=worktree_path, check=True)
        return
    symlink_deps(main_cwd, worktree_path)


def symlink_deps(main_cwd: str, worktree_path: str) -> None:
    """Symlink node_modules, .venv, vendor, etc."""
    for name in ["node_modules", ".venv", "vendor", ".env"]:
        src = os.path.join(main_cwd, name)
        dst = os.path.join(worktree_path, name)
        if not os.path.exists(src) or os.path.exists(dst):
            continue
        os.symlink(src, dst)


def commit_if_dirty(worktree_path: str, task_id: str, title: str) -> bool:
    """Stage all + commit with [workflow] prefix. Returns True if committed."""
    if is_clean(worktree_path):
        return False
    add_result = git(["add", "-A", "--", ":!docs/workflows/"], cwd=worktree_path)
    if not add_result.ok:
        raise RuntimeError(add_result.stderr.strip() or "git add failed")
    staged = git(["diff", "--cached", "--name-only"], cwd=worktree_path)
    if not staged.ok:
        raise RuntimeError(staged.stderr.strip() or "git diff --cached failed")
    if staged.stdout.strip() == "":
        return False
    message = f"[workflow] {task_id}: {title}"
    commit_result = git(["commit", "-m", message], cwd=worktree_path)
    if not commit_result.ok:
        raise RuntimeError(commit_result.stderr.strip() or "git commit failed")
    return True


def merge_back(main_cwd: str, wt: WorktreeInfo) -> MergeResult:
    """Rebase onto main, then fast-forward merge. Serialized by caller."""
    rebase_result = git(["rebase", wt.main_branch], cwd=wt.path)
    if not rebase_result.ok:
        conflicts = rebase_result.stderr.strip() or rebase_result.stdout.strip() or None
        conflict_files = get_dirty_files(wt.path)
        return MergeResult(
            success=False,
            conflicts=conflicts,
            conflict_files=conflict_files or None,
        )
    checkout_result = git(["checkout", wt.main_branch], cwd=main_cwd)
    if not checkout_result.ok:
        raise RuntimeError(checkout_result.stderr.strip() or "git checkout failed")
    merge_result = git(["merge", "--ff-only", wt.branch], cwd=main_cwd)
    if not merge_result.ok:
        conflicts = merge_result.stderr.strip() or merge_result.stdout.strip() or None
        return MergeResult(success=False, conflicts=conflicts)
    return MergeResult(success=True)


def cleanup_worktree(main_cwd: str, wt: WorktreeInfo) -> None:
    """Remove worktree + branch. Idempotent."""
    git(["worktree", "remove", "--force", wt.path], cwd=main_cwd)
    git(["branch", "-D", wt.branch], cwd=main_cwd)


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
