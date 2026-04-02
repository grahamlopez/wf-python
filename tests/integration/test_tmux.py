"""Tests for wflib.tmux — pane creation, exit-code polling, window management."""

import os
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

from wflib.tmux import (
    get_or_create_execution_pane,
    is_tmux_available,
    pane_exists,
    reset_execution_window,
    shell_escape,
    wait_for_exit_code_file,
)


def _get_window_id_for_pane(pane_id: str) -> str:
    result = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane_id, "#{window_id}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


class TestIsTmuxAvailable(unittest.TestCase):
    def test_returns_bool(self):
        """Returns True or False based on tmux availability."""
        with mock.patch("shutil.which", return_value="/usr/bin/tmux"):
            with mock.patch.dict(os.environ, {"TMUX": "/tmp/tmux"}, clear=False):
                self.assertTrue(is_tmux_available())

        with mock.patch("shutil.which", return_value=None):
            with mock.patch.dict(os.environ, {"TMUX": "/tmp/tmux"}, clear=False):
                self.assertFalse(is_tmux_available())

        with mock.patch("shutil.which", return_value="/usr/bin/tmux"):
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertFalse(is_tmux_available())


class TestShellEscape(unittest.TestCase):
    def test_escapes_special_chars(self):
        """Escapes shell-special characters."""
        self.assertEqual(shell_escape("hello world"), "'hello world'")
        self.assertEqual(shell_escape("hello$world"), "'hello$world'")

    def test_empty_string(self):
        """Handles empty string."""
        self.assertEqual(shell_escape(""), "''")


@unittest.skipUnless(os.environ.get("TMUX"), "requires tmux session")
class TestPaneManagement(unittest.TestCase):
    def tearDown(self) -> None:
        reset_execution_window()

    def test_get_or_create_execution_pane(self):
        """Creates a pane and returns its ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pane_id_1 = get_or_create_execution_pane(
                cwd=temp_dir,
                command=f"printf 'ok' > {temp_dir}/file-1",
                workflow_label="tmux-test",
                task_id="task-1",
                task_title="First task",
            )
            pane_id_2 = get_or_create_execution_pane(
                cwd=temp_dir,
                command=f"printf 'ok' > {temp_dir}/file-2",
                workflow_label="tmux-test",
                task_id="task-2",
                task_title="Second task",
            )

            window_id_1 = _get_window_id_for_pane(pane_id_1)
            window_id_2 = _get_window_id_for_pane(pane_id_2)
            self.assertTrue(window_id_1)
            self.assertEqual(window_id_1, window_id_2)
            self.assertNotEqual(pane_id_1, pane_id_2)

            subprocess.run(["tmux", "kill-window", "-t", window_id_1], check=False)

    def test_pane_exists_for_valid_pane(self):
        """pane_exists returns True for an active pane."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pane_id = get_or_create_execution_pane(
                cwd=temp_dir,
                command="sleep 2",
                workflow_label="tmux-test",
                task_id="task-3",
                task_title="Pane check",
            )
            self.assertTrue(pane_exists(pane_id))
            subprocess.run(["tmux", "kill-pane", "-t", pane_id], check=False)

    def test_pane_exists_for_gone_pane(self):
        """pane_exists returns False for a non-existent pane."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pane_id = get_or_create_execution_pane(
                cwd=temp_dir,
                command="sleep 1",
                workflow_label="tmux-test",
                task_id="task-4",
                task_title="Pane gone",
            )
            subprocess.run(["tmux", "kill-pane", "-t", pane_id], check=False)
            time.sleep(0.2)
            self.assertFalse(pane_exists(pane_id))


@unittest.skipUnless(os.environ.get("TMUX"), "requires tmux session")
class TestExitCodePolling(unittest.TestCase):
    def tearDown(self) -> None:
        reset_execution_window()

    def test_wait_for_exit_code_file(self):
        """Polls until exit-code file appears."""
        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code_file = os.path.join(temp_dir, "exit-code")
            pane_id = get_or_create_execution_pane(
                cwd=temp_dir,
                command="sleep 2",
                workflow_label="tmux-test",
                task_id="task-5",
                task_title="Exit polling",
            )

            def _write_exit_code() -> None:
                time.sleep(0.6)
                with open(exit_code_file, "w", encoding="utf-8") as handle:
                    handle.write("0")

            thread = threading.Thread(target=_write_exit_code)
            thread.start()
            wait_for_exit_code_file(exit_code_file, pane_id)
            thread.join()

            with open(exit_code_file, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read().strip(), "0")
            subprocess.run(["tmux", "kill-pane", "-t", pane_id], check=False)

    def test_fallback_on_pane_gone(self):
        """Falls back when pane disappears before exit-code file written."""
        with tempfile.TemporaryDirectory() as temp_dir:
            exit_code_file = os.path.join(temp_dir, "exit-code")
            pane_id = get_or_create_execution_pane(
                cwd=temp_dir,
                command="sleep 2",
                workflow_label="tmux-test",
                task_id="task-6",
                task_title="Pane gone",
            )
            subprocess.run(["tmux", "kill-pane", "-t", pane_id], check=False)
            wait_for_exit_code_file(exit_code_file, pane_id)

            with open(exit_code_file, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read().strip(), "1")


if __name__ == "__main__":
    unittest.main()
