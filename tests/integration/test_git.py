"""Tests for wflib.git — thin git wrapper sanity tests."""

import unittest

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


class TestGitCommand(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_successful_command(self):
        """git(['status']) returns GitResult with ok=True."""

    @unittest.skip("Phase 2")
    def test_failed_command(self):
        """git with bad args returns GitResult with ok=False."""

    @unittest.skip("Phase 2")
    def test_captures_stdout(self):
        """git captures command stdout."""


class TestIsGitRepo(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_git_repo(self):
        """Returns True inside a git repository."""

    @unittest.skip("Phase 2")
    def test_not_git_repo(self):
        """Returns False outside a git repository."""


class TestIsClean(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_clean_repo(self):
        """Returns True for a clean working tree."""

    @unittest.skip("Phase 2")
    def test_dirty_repo(self):
        """Returns False when there are uncommitted changes."""


class TestGetBranch(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_returns_branch_name(self):
        """Returns the current branch name (e.g., 'main')."""


class TestGetHead(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_returns_commit_hash(self):
        """Returns the HEAD commit hash."""

    @unittest.skip("Phase 2")
    def test_short_hash(self):
        """get_head(short=True) returns abbreviated hash."""


class TestGetDirtyFiles(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_lists_modified_files(self):
        """Returns list of modified/untracked files."""

    @unittest.skip("Phase 2")
    def test_empty_when_clean(self):
        """Returns empty list for clean repo."""


if __name__ == "__main__":
    unittest.main()
