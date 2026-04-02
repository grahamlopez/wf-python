"""Tests for profiles.pi — command construction + recorded output through pi adapters."""

import unittest

from profiles.pi import PiProfile
from wflib.types import ModelsConfig


class TestPiHeadlessCommand(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_basic_command_structure(self):
        """Headless command starts with pi --mode json -p --no-session --no-extensions."""

    @unittest.skip("Phase 3")
    def test_appends_system_prompt(self):
        """Command includes --append-system-prompt with the system prompt file."""

    @unittest.skip("Phase 3")
    def test_loads_research_and_web_fetch(self):
        """Command includes -e flags for research.ts and web-fetch/index.ts."""

    @unittest.skip("Phase 3")
    def test_loads_tool_extensions(self):
        """Requested tools are loaded as -e flags."""

    @unittest.skip("Phase 3")
    def test_model_flag(self):
        """Model is resolved and passed as --model."""


class TestPiTmuxWrapper(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_wrapper_script_structure(self):
        """Wrapper script has shebang, trap, pi invocation, adapter call, exit-code write."""

    @unittest.skip("Phase 3")
    def test_auto_close_extension(self):
        """Auto-close > 0 adds the auto-quit.ts extension."""

    @unittest.skip("Phase 3")
    def test_session_dir_flag(self):
        """Wrapper includes --session-dir for tmux sessions."""


class TestPiRecordedOutput(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_parse_headless_json_mode(self):
        """Recorded pi --mode json stdout parsed into correct results dict."""

    @unittest.skip("Phase 3")
    def test_parse_session_output(self):
        """Recorded pi session .jsonl parsed into correct results dict."""


if __name__ == "__main__":
    unittest.main()
