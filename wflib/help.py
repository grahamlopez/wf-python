"""Agent-friendly reference system.

~800 lines, pure functions, no I/O beyond print().
"""

from __future__ import annotations

from typing import Callable

TOPICS: list[tuple[str, str, Callable[[], str]]] = []   # (name, title, content_fn)
TOPIC_MAP: dict[str, tuple[str, Callable[[], str]]] = {}  # name → (title, content_fn)


def _register_topic(name: str, title: str, content_fn: Callable[[], str]) -> None:
    TOPICS.append((name, title, content_fn))
    TOPIC_MAP[name] = (title, content_fn)


def _placeholder_topic(name: str, title: str) -> str:
    return (
        f"{title}\n"
        f"{'=' * len(title)}\n\n"
        f"TODO: help content for '{name}' is not yet implemented."
    )


def _seed_topics() -> None:
    if TOPICS:
        return

    topics = [
        ("overview", "Overview"),
        ("lifecycle", "Lifecycle"),
        ("subcommands", "Subcommands (Quick Reference)"),
        ("record", "Record File Anatomy"),
        ("config", "Config"),
        ("models", "Models"),
        ("worktrees", "Worktrees"),
        ("exit-codes", "Exit Codes"),
        ("recovery", "Recovery"),
        ("debugging", "Debugging"),
        ("harness", "Harness"),
        ("init", "wf init"),
        ("run", "wf run"),
        ("brainstorm", "wf brainstorm"),
        ("plan", "wf plan"),
        ("record-brainstorm", "wf record-brainstorm"),
        ("submit-plan", "wf submit-plan"),
        ("execute", "wf execute"),
        ("execute-task", "wf execute-task"),
        ("review", "wf review"),
        ("close", "wf close"),
        ("status", "wf status"),
        ("list", "wf list"),
        ("render", "wf render"),
        ("validate", "wf validate"),
        ("brief", "wf brief"),
        ("recover", "wf recover"),
        ("schema", "wf schema"),
        ("templates", "wf template(s)"),
    ]

    for name, title in topics:
        _register_topic(name, title, lambda n=name, t=title: _placeholder_topic(n, t))


def _format_topic(name: str) -> str:
    title, content_fn = TOPIC_MAP[name]
    return content_fn()


def get_help(topic: str | None = None) -> str:
    """Return help text. topic=None → full dump. Never raises."""
    _seed_topics()

    if topic is None:
        return "\n\n".join(_format_topic(name) for name, _, _ in TOPICS)

    if topic == "topics":
        lines = ["Available help topics:"]
        lines.extend(f"  {name}" for name, _, _ in TOPICS)
        return "\n".join(lines)

    if topic in TOPIC_MAP:
        return _format_topic(topic)

    matches = sorted(name for name in TOPIC_MAP if name.startswith(topic))
    if len(matches) == 1:
        return _format_topic(matches[0])
    if len(matches) > 1:
        lines = [f"Ambiguous help topic '{topic}'. Matches:"]
        lines.extend(f"  {name}" for name in matches)
        return "\n".join(lines)

    return (
        f"Unknown help topic '{topic}'. "
        "Use 'wf help topics' to list available topics."
    )


def help_command(args: list[str]) -> None:
    """CLI entry point. Prints to stdout."""
    topic = args[0] if args else None
    print(get_help(topic))
