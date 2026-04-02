"""Subprocess helper for CLI tests.

Provides run_wf() which spawns bin/wf as a subprocess with configurable
cwd, stdin, env vars, and returns an object with stdout, stderr, returncode.
"""

import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Union

# Locate bin/wf relative to this file (tests/util.py -> repo_root/bin/wf)
_REPO_ROOT = Path(__file__).resolve().parent.parent
_WF_BIN = _REPO_ROOT / "bin" / "wf"


class WfResult:
    """Result of running bin/wf as a subprocess."""

    __slots__ = ("stdout", "stderr", "returncode")

    def __init__(self, stdout: str, stderr: str, returncode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def __repr__(self) -> str:
        return (
            f"WfResult(returncode={self.returncode!r}, "
            f"stdout={self.stdout!r}, stderr={self.stderr!r})"
        )


def run_wf(
    args: Union[str, Sequence[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    stdin: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
) -> WfResult:
    """Run bin/wf with the given arguments and return the result.

    Parameters
    ----------
    args:
        Command-line arguments as a single string (shell-like parsing) or a
        list of arguments. Example:
        ``"init myproject --cwd /tmp/proj --no-worktree"``
    cwd:
        Working directory for the subprocess. Defaults to the repo root.
    stdin:
        String to feed to the subprocess's stdin. If None, stdin is closed.
    env:
        Extra environment variables to set. Merged on top of the current
        environment (os.environ is inherited; these add/override).
    timeout:
        Maximum seconds to wait for the process. Defaults to 30.

    Returns
    -------
    WfResult
        Object with .stdout, .stderr, .returncode attributes.
    """
    if isinstance(args, str):
        argv = shlex.split(args)
    else:
        argv = list(args)

    cmd = ["python3", str(_WF_BIN)] + argv

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=cwd or _REPO_ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=run_env,
    )

    return WfResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )
