"""Tests for wflib.git — thin git wrapper sanity tests."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from wflib.git import (
    GitResult,
    get_current_branch,
    get_dirty_files,
    get_head,
    get_head_full,
    git,
    is_clean,
    is_git_repo,
)


def init_repo(base_dir: Path, with_commit: bool = True) -> Path:
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
    if with_commit:
        (repo / "README.md").write_text("hello\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True, text=True)
    return repo


class TestGitCommand(unittest.TestCase):
    def test_successful_command(self):
        """git(['status']) returns GitResult with ok=True."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            result = git(["status"], cwd=str(repo))
            self.assertIsInstance(result, GitResult)
            self.assertTrue(result.ok)

    def test_failed_command(self):
        """git with bad args returns GitResult with ok=False."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            result = git(["not-a-command"], cwd=str(repo))
            self.assertFalse(result.ok)

    def test_captures_stdout(self):
        """git captures command stdout."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            result = git(["rev-parse", "--is-inside-work-tree"], cwd=str(repo))
            self.assertTrue(result.ok)
            self.assertIn("true", result.stdout)


class TestIsGitRepo(unittest.TestCase):
    def test_git_repo(self):
        """Returns True inside a git repository."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            self.assertTrue(is_git_repo(str(repo)))

    def test_not_git_repo(self):
        """Returns False outside a git repository."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            self.assertFalse(is_git_repo(tmp_dir))


class TestIsClean(unittest.TestCase):
    def test_clean_repo(self):
        """Returns True for a clean working tree."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            self.assertTrue(is_clean(str(repo)))

    def test_dirty_repo(self):
        """Returns False when there are uncommitted changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            (repo / "README.md").write_text("hello\nchanged\n")
            self.assertFalse(is_clean(str(repo)))


class TestGetBranch(unittest.TestCase):
    def test_returns_branch_name(self):
        """Returns the current branch name (e.g., 'main')."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            self.assertEqual(get_current_branch(str(repo)), "main")


class TestGetHead(unittest.TestCase):
    def test_returns_commit_hash(self):
        """Returns the HEAD commit hash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            expected = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(get_head(str(repo)), expected)

    def test_short_hash(self):
        """get_head(short=True) returns abbreviated hash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            expected = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(get_head(str(repo), short=True), expected)

    def test_head_full_returns_none_for_empty_repo(self):
        """get_head_full returns None when no commits exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir), with_commit=False)
            self.assertIsNone(get_head_full(str(repo)))


class TestGetDirtyFiles(unittest.TestCase):
    def test_lists_modified_files(self):
        """Returns list of modified/untracked files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            (repo / "README.md").write_text("hello\nchanged\n")
            (repo / "new.txt").write_text("new file\n")
            dirty = sorted(get_dirty_files(str(repo)))
            self.assertEqual(dirty, ["README.md", "new.txt"])

    def test_empty_when_clean(self):
        """Returns empty list for clean repo."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = init_repo(Path(tmp_dir))
            self.assertEqual(get_dirty_files(str(repo)), [])


if __name__ == "__main__":
    unittest.main()
