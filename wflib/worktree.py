"""Git worktree lifecycle - create, setup deps, merge back, cleanup."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import stat
import subprocess

from wflib.git import get_current_branch, get_dirty_files, git, is_clean
from wflib.types import MergeState


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
    merge_state: MergeState
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
        try:
            subprocess.run(
                [hook_path],
                cwd=worktree_path,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f".worktree-setup hook failed: {exc.stderr or exc.stdout or 'unknown error'}"
            ) from exc
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


def _stage_and_commit(cwd: str, add_args: list[str], commit_args: list[str]) -> bool:
    """Stage files, check for staged changes, and commit.

    Encapsulates the repeated pattern: git add <add_args>, check staged files
    via git diff --cached, git commit <commit_args>.  Returns True if a commit
    was created, False if nothing was staged.  Raises RuntimeError on failure.
    """
    add_result = git(["add"] + add_args, cwd=cwd)
    if not add_result.ok:
        raise RuntimeError(add_result.stderr.strip() or "git add failed")
    staged = git(["diff", "--cached", "--name-only"], cwd=cwd)
    if not staged.ok:
        raise RuntimeError(staged.stderr.strip() or "git diff --cached failed")
    if staged.stdout.strip() == "":
        return False
    commit_result = git(["commit"] + commit_args, cwd=cwd)
    if not commit_result.ok:
        raise RuntimeError(commit_result.stderr.strip() or "git commit failed")
    return True


def commit_if_dirty(worktree_path: str, task_id: str, title: str) -> bool:
    """Stage all + commit with [workflow] prefix. Returns True if committed."""
    if is_clean(worktree_path):
        return False
    message = f"[workflow] {task_id}: {title}"
    return _stage_and_commit(
        worktree_path,
        ["-A", "--", ":!docs/workflows/"],
        ["-m", message],
    )


def merge_back(main_cwd: str, wt: WorktreeInfo) -> MergeResult:
    """Rebase onto main, then fast-forward merge. Serialized by caller."""
    rebase_result = git(["rebase", wt.main_branch], cwd=wt.path)
    if not rebase_result.ok:
        # Intentionally leave the rebase in-progress on conflict.
        # The caller (task_executor._merge_and_cleanup) inspects the
        # MergeResult, detects the conflict, and spawns a resolution
        # agent that can resolve the conflicted files inside the
        # worktree while the rebase is still active.  The resolution
        # agent runs `git rebase --continue` or `--abort` once done.
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
    main_branch = get_current_branch(cwd)
    repo_root = os.path.abspath(cwd)
    repo_name = os.path.basename(repo_root.rstrip(os.sep))
    worktree_path = os.path.join(os.path.dirname(repo_root), f"{repo_name}-wf-{workflow_name}")
    branch = f"wf-{workflow_name}"
    wt = WorktreeInfo(path=worktree_path, branch=branch, main_branch=main_branch)
    cleanup_worktree(cwd, wt)
    result = git(["worktree", "add", "-b", branch, worktree_path], cwd=cwd)
    if not result.ok:
        raise RuntimeError(result.stderr.strip() or "git worktree add failed")
    return wt


def close_workflow_worktree(main_cwd: str, wt: WorktreeInfo) -> WorkflowCloseResult:
    """Rebase + merge, or fall back to merge --no-commit on conflict.

    NOTE: This function only performs the merge.  Worktree and branch
    cleanup is the caller's responsibility (e.g. wf close), matching
    the merge_back pattern where cleanup_worktree is called separately
    after merge results are inspected.
    """
    checkout_result = git(["checkout", wt.main_branch], cwd=main_cwd)
    if not checkout_result.ok:
        raise RuntimeError(checkout_result.stderr.strip() or "git checkout failed")
    base_result = git(["rev-parse", "HEAD"], cwd=main_cwd)
    if not base_result.ok:
        raise RuntimeError(base_result.stderr.strip() or "git rev-parse failed")
    base_commit = base_result.stdout.strip()

    rebase_result = git(["rebase", wt.main_branch], cwd=wt.path)
    if rebase_result.ok:
        merge_result = git(["merge", "--ff-only", wt.branch], cwd=main_cwd)
        if not merge_result.ok:
            conflicts = merge_result.stderr.strip() or merge_result.stdout.strip()
            return WorkflowCloseResult(merge_state="failed", conflicts=conflicts)
        diff_result = git(["diff", "--stat", base_commit], cwd=main_cwd)
        diff_stat = diff_result.stdout.strip() if diff_result.ok else ""
        return WorkflowCloseResult(merge_state="clean", diff_stat=diff_stat)

    git(["rebase", "--abort"], cwd=wt.path)
    merge_result = git(["merge", "--no-commit", wt.branch], cwd=main_cwd)
    conflicts = (
        merge_result.stderr.strip()
        or merge_result.stdout.strip()
        or rebase_result.stderr.strip()
        or rebase_result.stdout.strip()
    )
    conflict_files = get_dirty_files(main_cwd)
    diff_result = git(["diff", "--stat", base_commit], cwd=main_cwd)
    diff_stat = diff_result.stdout.strip() if diff_result.ok else ""
    return WorkflowCloseResult(
        merge_state="conflicted",
        conflict_files=conflict_files,
        conflicts=conflicts,
        diff_stat=diff_stat,
    )


def commit_or_amend_workflow_files(cwd: str, workflow_name: str) -> bool:
    """Commit docs/workflows/. Amends if last commit starts with [workflow]."""
    message_result = git(["log", "-1", "--pretty=%s"], cwd=cwd)
    # In a brand-new repo with no commits yet, `git log` will fail.
    # Treat that the same as "no previous workflow commit" and fall
    # through to a fresh commit.
    if message_result.ok and message_result.stdout.strip().startswith("[workflow"):
        commit_args = ["--amend", "--no-edit"]
    else:
        message = f"[workflow] {workflow_name}: update record"
        commit_args = ["-m", message]
    return _stage_and_commit(cwd, ["docs/workflows"], commit_args)


def commit_remaining_changes(cwd: str, message: str) -> bool:
    """Stage all + commit with caller's message."""
    return _stage_and_commit(cwd, ["-A"], ["-m", message])
