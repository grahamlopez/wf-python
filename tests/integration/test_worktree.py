"""Tests for wflib.worktree — create, symlink, commit, merge-back, cleanup."""

import unittest

from wflib.worktree import (
    MergeResult,
    WorkflowCloseResult,
    WorktreeInfo,
    cleanup_worktree,
    close_workflow_worktree,
    commit_if_dirty,
    commit_or_amend_workflow_files,
    commit_remaining_changes,
    create_task_worktree,
    create_workflow_worktree,
    merge_back,
    setup_worktree,
    symlink_deps,
)


class TestCreateTaskWorktree(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_creates_worktree_and_branch(self):
        """Creates a git worktree with a named branch."""

    @unittest.skip("Phase 2")
    def test_returns_worktree_info(self):
        """Returns WorktreeInfo with path, branch, main_branch."""

    @unittest.skip("Phase 2")
    def test_cleans_stale_worktree(self):
        """Cleans up a stale worktree if one exists at the same path."""


class TestSetupWorktree(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_runs_worktree_setup_hook(self):
        """Runs .worktree-setup if present in main repo."""

    @unittest.skip("Phase 2")
    def test_symlinks_deps_when_no_hook(self):
        """Symlinks node_modules/.venv/vendor when no .worktree-setup hook."""


class TestSymlinkDeps(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_symlinks_node_modules(self):
        """Symlinks node_modules from main to worktree."""

    @unittest.skip("Phase 2")
    def test_skips_missing_dirs(self):
        """Skips symlink when source directory doesn't exist."""


class TestCommitIfDirty(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_commits_when_dirty(self):
        """Stages all and commits with [workflow] prefix."""

    @unittest.skip("Phase 2")
    def test_returns_false_when_clean(self):
        """Returns False when working tree is clean."""

    @unittest.skip("Phase 2")
    def test_excludes_docs_workflows(self):
        """Uses git add -A -- ':!docs/workflows/' to exclude record files."""


class TestMergeBack(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_clean_rebase_and_ff(self):
        """Rebases onto main then fast-forward merges."""

    @unittest.skip("Phase 2")
    def test_conflict_returns_merge_result(self):
        """Returns MergeResult with conflicts populated on conflict."""

    @unittest.skip("Phase 2")
    def test_main_branch_has_task_commits(self):
        """After clean merge, main branch has the task's commits."""


class TestCleanupWorktree(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_removes_worktree_and_branch(self):
        """Removes the worktree directory and its branch."""

    @unittest.skip("Phase 2")
    def test_idempotent(self):
        """Calling cleanup twice does not error."""


class TestWorkflowWorktree(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_create_workflow_worktree(self):
        """Creates workflow worktree at ../<repo>-wf-<name>/."""

    @unittest.skip("Phase 2")
    def test_close_workflow_worktree_clean(self):
        """Close with clean rebase returns clean merge state."""

    @unittest.skip("Phase 2")
    def test_close_workflow_worktree_conflict(self):
        """Close with conflict returns conflicted state."""


if __name__ == "__main__":
    unittest.main()
