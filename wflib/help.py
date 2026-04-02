"""Agent-friendly reference system.

~800 lines, pure functions, no I/O beyond print().
"""

from __future__ import annotations

from typing import Callable

TOPICS: list[tuple[str, str, Callable]] = []   # (name, title, content_fn)
TOPIC_MAP: dict[str, tuple[str, Callable]] = {}  # name → (title, content_fn)


def get_help(topic: str | None = None) -> str:
    """Return help text. topic=None → full dump. Never raises."""
    raise NotImplementedError("get_help: not yet implemented")


def help_command(args: list[str]) -> None:
    """CLI entry point. Prints to stdout."""
    raise NotImplementedError("help_command: not yet implemented")
