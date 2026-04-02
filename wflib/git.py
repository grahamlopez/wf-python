"""Thin git wrapper."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass
class GitResult:
    ok: bool
    stdout: str
    stderr: str


def git(args: list[str], cwd: str, timeout: int = 60) -> GitResult:
    """Run a git command. Returns GitResult."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return GitResult(
        ok=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def is_git_repo(cwd: str) -> bool:
    """Check if cwd is inside a git repository."""
    result = git(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
    return result.ok and result.stdout.strip() == "true"


def is_clean(cwd: str) -> bool:
    """Check if the working tree is clean."""
    result = git(["status", "--porcelain"], cwd=cwd)
    if not result.ok:
        return False
    return result.stdout.strip() == ""


def get_dirty_files(cwd: str) -> list[str]:
    """Get list of dirty (modified/untracked) files."""
    result = git(["status", "--porcelain"], cwd=cwd)
    if not result.ok:
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path_part = line[3:] if len(line) >= 3 else ""
        if "->" in path_part:
            path_part = path_part.split("->", 1)[1]
        path = path_part.strip()
        if path:
            files.append(path)
    return files


def get_current_branch(cwd: str) -> str:
    """Get the name of the current branch."""
    result = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if not result.ok:
        raise RuntimeError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def get_head(cwd: str, short: bool = False) -> str:
    """Get the HEAD commit hash."""
    args = ["rev-parse"]
    if short:
        args.append("--short")
    args.append("HEAD")
    result = git(args, cwd=cwd)
    if not result.ok:
        raise RuntimeError(result.stderr.strip() or "git rev-parse failed")
    return result.stdout.strip()


def get_head_full(cwd: str) -> str | None:
    """Get the full HEAD commit hash, or None if no commits."""
    result = git(["rev-parse", "HEAD"], cwd=cwd)
    if not result.ok:
        return None
    return result.stdout.strip()
