"""Thin git wrapper."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GitResult:
    ok: bool
    stdout: str
    stderr: str


def git(args: list[str], cwd: str, timeout: int = 60) -> GitResult:
    """Run a git command. Returns GitResult."""
    raise NotImplementedError("git: not yet implemented")


def is_git_repo(cwd: str) -> bool:
    """Check if cwd is inside a git repository."""
    raise NotImplementedError("is_git_repo: not yet implemented")


def is_clean(cwd: str) -> bool:
    """Check if the working tree is clean."""
    raise NotImplementedError("is_clean: not yet implemented")


def get_dirty_files(cwd: str) -> list[str]:
    """Get list of dirty (modified/untracked) files."""
    raise NotImplementedError("get_dirty_files: not yet implemented")


def get_current_branch(cwd: str) -> str:
    """Get the name of the current branch."""
    raise NotImplementedError("get_current_branch: not yet implemented")


def get_head(cwd: str, short: bool = False) -> str:
    """Get the HEAD commit hash."""
    raise NotImplementedError("get_head: not yet implemented")


def get_head_full(cwd: str) -> str | None:
    """Get the full HEAD commit hash, or None if no commits."""
    raise NotImplementedError("get_head_full: not yet implemented")
