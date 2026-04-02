"""Shell completion script generation and dynamic completion callback.

Self-contained - no imports from scheduler, record, runner, or any other
wflib module. Knows only the static CLI surface and how to shell out
for dynamic completions.
"""

from __future__ import annotations

# --- Static data baked into generated scripts and used by complete() ---

SUBCOMMANDS: list[str] = [
    "init", "run", "brainstorm", "plan", "record-brainstorm", "submit-plan",
    "execute", "execute-task", "review", "auto-review", "close",
    "status", "list", "history", "render", "validate", "brief", "recover",
    "schema", "config", "template", "completions", "help",
]

FLAGS: dict[str, list[str]] = {}  # subcommand → ["--cwd", "--model", ...]

COMPONENT_NAMES: list[str] = [
    "plan", "brainstorm", "task", "report-result", "usage",
]


# --- Script generation ---

def generate_bash() -> str:
    """Return a complete bash completion script."""
    raise NotImplementedError("generate_bash: not yet implemented")


def generate_zsh() -> str:
    """Return a complete zsh completion script."""
    raise NotImplementedError("generate_zsh: not yet implemented")


def generate_fish() -> str:
    """Return a complete fish completion script."""
    raise NotImplementedError("generate_fish: not yet implemented")


# --- Dynamic completion callback ---

def complete(words: list[str], cwd: str) -> list[str]:
    """Return completions for the current command line context.
    Called by the generated shell script via `wf --complete <words...>`.
    """
    raise NotImplementedError("complete: not yet implemented")
