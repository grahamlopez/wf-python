"""Tmux pane/window management."""

from __future__ import annotations


# --- Detection ---

def is_tmux_available() -> bool:
    """Check if tmux is installed and a session is running."""
    raise NotImplementedError("is_tmux_available: not yet implemented")


def get_current_window_id() -> str:
    """Get the current tmux window ID."""
    raise NotImplementedError("get_current_window_id: not yet implemented")


def select_window(window_id: str) -> None:
    """Select a tmux window by ID."""
    raise NotImplementedError("select_window: not yet implemented")


# --- Execution window state (module-level, reset between runs) ---

def reset_execution_window() -> None:
    """Reset execution window state."""
    raise NotImplementedError("reset_execution_window: not yet implemented")


def get_or_create_execution_pane(
    cwd: str,
    command: str,
    workflow_label: str,
    task_id: str,
    task_title: str,
) -> str:
    """Get or create a tmux execution pane. Returns pane_id."""
    raise NotImplementedError("get_or_create_execution_pane: not yet implemented")


# --- Pane lifecycle ---

def pane_exists(pane_id: str) -> bool:
    """Check if a tmux pane exists."""
    raise NotImplementedError("pane_exists: not yet implemented")


def wait_for_exit_code_file(exit_code_file: str, pane_id: str) -> None:
    """Poll for completion. Fallback: check pane existence."""
    raise NotImplementedError("wait_for_exit_code_file: not yet implemented")


# --- Helpers ---

def shell_escape(s: str) -> str:
    """Escape a string for safe use in shell commands."""
    raise NotImplementedError("shell_escape: not yet implemented")
