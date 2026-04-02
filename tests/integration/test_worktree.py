"""Tests for wflib.worktree — create, symlink, commit, merge-back, cleanup."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from wflib.git import is_clean
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


def init_repo(base_dir: Path) -> Path:
    repo = base_dir / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "checkout", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    (repo / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)
    return repo


class TestCreateTaskWorktree(unittest.TestCase):
    def test_creates_worktree_and_branch(self):
        """Creates a git worktree with a named branch."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf1", "task1")
            self.assertTrue(Path(wt.path).exists())
            branches = subprocess.run(
                ["git", "branch", "--list", wt.branch],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn(wt.branch, branches)

    def test_returns_worktree_info(self):
        """Returns WorktreeInfo with path, branch, main_branch."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf2", "task2")
            expected_path = f"{os.path.abspath(str(repo))}-wf-wf2-task2"
            self.assertIsInstance(wt, WorktreeInfo)
            self.assertEqual(wt.path, expected_path)
            self.assertEqual(wt.branch, "wf-wf2-task2")
            self.assertEqual(wt.main_branch, "main")

    def test_cleans_stale_worktree(self):
        """Cleans up a stale worktree if one exists at the same path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf3", "task3")
            stale_file = Path(wt.path) / "stale.txt"
            stale_file.write_text("stale\n")
            wt2 = create_task_worktree(str(repo), "wf3", "task3")
            self.assertTrue(Path(wt2.path).exists())
            self.assertFalse(stale_file.exists())


class TestSetupWorktree(unittest.TestCase):
    def test_runs_worktree_setup_hook(self):
        """Runs .worktree-setup if present in main repo."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            hook_path = repo / ".worktree-setup"
            hook_path.write_text("#!/bin/sh\n" "touch .hook-ran\n")
            wt = create_task_worktree(str(repo), "wf4", "task4")
            setup_worktree(str(repo), wt.path)
            self.assertTrue((Path(wt.path) / ".hook-ran").exists())

    def test_symlinks_deps_when_no_hook(self):
        """Symlinks node_modules/.venv/vendor when no .worktree-setup hook."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            (repo / "node_modules").mkdir()
            wt = create_task_worktree(str(repo), "wf5", "task5")
            setup_worktree(str(repo), wt.path)
            self.assertTrue(os.path.islink(Path(wt.path) / "node_modules"))


class TestSymlinkDeps(unittest.TestCase):
    def test_symlinks_node_modules(self):
        """Symlinks node_modules from main to worktree."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            main = base / "main"
            worktree = base / "worktree"
            main.mkdir()
            worktree.mkdir()
            (main / "node_modules").mkdir()
            (main / ".env").write_text("ENV=1\n")
            symlink_deps(str(main), str(worktree))
            node_link = worktree / "node_modules"
            env_link = worktree / ".env"
            self.assertTrue(node_link.is_symlink())
            self.assertTrue(env_link.is_symlink())
            self.assertEqual(os.readlink(node_link), str(main / "node_modules"))
            self.assertEqual(os.readlink(env_link), str(main / ".env"))

    def test_skips_missing_dirs(self):
        """Skips symlink when source directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            main = base / "main"
            worktree = base / "worktree"
            main.mkdir()
            worktree.mkdir()
            symlink_deps(str(main), str(worktree))
            for name in ["node_modules", ".venv", "vendor", ".env"]:
                self.assertFalse((worktree / name).exists())


class TestCommitIfDirty(unittest.TestCase):
    def test_commits_when_dirty(self):
        """Stages all and commits with [workflow] prefix."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf6", "task6")
            (Path(wt.path) / "README.md").write_text("updated\n")
            committed = commit_if_dirty(wt.path, "task6", "Update readme")
            self.assertTrue(committed)
            self.assertTrue(is_clean(wt.path))
            message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=wt.path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(message, "[workflow] task6: Update readme")

    def test_returns_false_when_clean(self):
        """Returns False when working tree is clean."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf7", "task7")
            self.assertFalse(commit_if_dirty(wt.path, "task7", "No changes"))

    def test_excludes_docs_workflows(self):
        """Uses git add -A -- ':!docs/workflows/' to exclude record files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf8", "task8")
            (Path(wt.path) / "README.md").write_text("updated\n")
            docs_dir = Path(wt.path) / "docs" / "workflows"
            docs_dir.mkdir(parents=True)
            (docs_dir / "workflow.json").write_text("{}\n")
            committed = commit_if_dirty(wt.path, "task8", "Update readme")
            self.assertTrue(committed)
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=wt.path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("docs/", status)
            files = subprocess.run(
                ["git", "show", "--name-only", "--pretty="],
                cwd=wt.path,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("README.md", files)
            self.assertNotIn("docs/workflows/workflow.json", files)


class TestMergeBack(unittest.TestCase):
    def test_clean_rebase_and_ff(self):
        """Rebases onto main then fast-forward merges."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf9", "task9")
            (Path(wt.path) / "README.md").write_text("updated\n")
            commit_if_dirty(wt.path, "task9", "Update readme")
            result = merge_back(str(repo), wt)
            self.assertTrue(result.success)
            self.assertTrue((repo / "README.md").read_text().startswith("updated"))

    def test_conflict_returns_merge_result(self):
        """Returns MergeResult with conflicts populated on conflict."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf10", "task10")
            (repo / "README.md").write_text("main change\n")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "main change"], cwd=repo, check=True, capture_output=True, text=True)
            (Path(wt.path) / "README.md").write_text("task change\n")
            commit_if_dirty(wt.path, "task10", "Update readme")
            result = merge_back(str(repo), wt)
            self.assertFalse(result.success)
            self.assertIsNotNone(result.conflicts)
            self.assertIn("README.md", result.conflict_files or [])

    def test_main_branch_has_task_commits(self):
        """After clean merge, main branch has the task's commits."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf11", "task11")
            (Path(wt.path) / "README.md").write_text("updated\n")
            commit_if_dirty(wt.path, "task11", "Update readme")
            result = merge_back(str(repo), wt)
            self.assertTrue(result.success)
            message = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(message, "[workflow] task11: Update readme")


class TestCleanupWorktree(unittest.TestCase):
    def test_removes_worktree_and_branch(self):
        """Removes the worktree directory and its branch."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf12", "task12")
            cleanup_worktree(str(repo), wt)
            self.assertFalse(Path(wt.path).exists())
            branches = subprocess.run(
                ["git", "branch", "--list", wt.branch],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(branches, "")

    def test_idempotent(self):
        """Calling cleanup twice does not error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            wt = create_task_worktree(str(repo), "wf13", "task13")
            cleanup_worktree(str(repo), wt)
            cleanup_worktree(str(repo), wt)


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
