"""Tmux pane/window management."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time

_EXECUTION_WINDOW_ID: str | None = None


def _run_tmux(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"tmux {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result


def _set_window_layout(window_id: str) -> None:
    _run_tmux(["select-layout", "-t", window_id, "tiled"], check=False)


def _set_pane_title(window_id: str, pane_id: str, title: str) -> None:
    _run_tmux(["set-option", "-t", window_id, "pane-border-status", "top"], check=False)
    _run_tmux(
        ["set-option", "-t", window_id, "pane-border-format", "#{pane_title}"],
        check=False,
    )
    _run_tmux(["select-pane", "-t", pane_id, "-T", title], check=False)


# --- Detection ---

def is_tmux_available() -> bool:
    """Check if tmux is installed and a session is running."""
    if shutil.which("tmux") is None:
        return False
    return bool(os.environ.get("TMUX"))


def get_current_window_id() -> str:
    """Get the current tmux window ID."""
    result = _run_tmux(["display-message", "-p", "#{window_id}"])
    return result.stdout.strip()


def select_window(window_id: str) -> None:
    """Select a tmux window by ID."""
    _run_tmux(["select-window", "-t", window_id])


# --- Execution window state (module-level, reset between runs) ---

def reset_execution_window() -> None:
    """Reset execution window state."""
    global _EXECUTION_WINDOW_ID
    _EXECUTION_WINDOW_ID = None


def get_or_create_execution_pane(
    cwd: str,
    command: str,
    workflow_label: str,
    task_id: str,
    task_title: str,
) -> str:
    """Get or create a tmux execution pane. Returns pane_id."""
    global _EXECUTION_WINDOW_ID

    if _EXECUTION_WINDOW_ID is not None:
        window_check = _run_tmux(
            ["display-message", "-t", _EXECUTION_WINDOW_ID, "-p"],
            check=False,
        )
        if window_check.returncode != 0:
            _EXECUTION_WINDOW_ID = None

    if _EXECUTION_WINDOW_ID is None:
        window_name = f"wf:{workflow_label}"
        result = _run_tmux(
            [
                "new-window",
                "-P",
                "-F",
                "#{pane_id}",
                "-n",
                window_name,
                "-c",
                cwd,
                "-d",
            ]
        )
        pane_id = result.stdout.strip()
        window_id = _run_tmux(
            ["display-message", "-t", pane_id, "-p", "#{window_id}"]
        ).stdout.strip()
        _EXECUTION_WINDOW_ID = window_id
    else:
        result = _run_tmux(
            [
                "split-window",
                "-P",
                "-F",
                "#{pane_id}",
                "-t",
                _EXECUTION_WINDOW_ID,
                "-c",
                cwd,
                "-d",
            ]
        )
        pane_id = result.stdout.strip()
        window_id = _EXECUTION_WINDOW_ID

    title = f"{task_id}: {task_title}"
    _set_pane_title(window_id, pane_id, title)
    _set_window_layout(window_id)
    _run_tmux(["send-keys", "-t", pane_id, command, "Enter"])
    return pane_id


# --- Pane lifecycle ---

def pane_exists(pane_id: str) -> bool:
    """Check if a tmux pane exists."""
    # display-message -t returns rc=0 even for non-existent panes in some
    # tmux versions. list-panes -t reliably returns rc=1 when the pane is gone.
    result = _run_tmux(["list-panes", "-t", pane_id, "-F", "#{pane_id}"], check=False)
    return result.returncode == 0


def wait_for_exit_code_file(exit_code_file: str, pane_id: str) -> None:
    """Poll for completion. Fallback: check pane existence."""
    while True:
        if os.path.exists(exit_code_file):
            return
        if not pane_exists(pane_id):
            with open(exit_code_file, "w", encoding="utf-8") as handle:
                handle.write("1")
            return
        time.sleep(0.5)


# --- Helpers ---

def shell_escape(s: str) -> str:
    """Escape a string for safe use in shell commands."""
    return shlex.quote(s)
