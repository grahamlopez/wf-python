"""Tests for profiles.claude_code — command construction + recorded output."""

import unittest

from profiles.claude_code import ClaudeCodeProfile
from wflib.types import ModelsConfig


class TestClaudeCodeHeadlessCommand(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_basic_command_structure(self):
        """Headless command starts with claude -p --bare --output-format stream-json."""

    @unittest.skip("Phase 3")
    def test_appends_system_prompt(self):
        """Command includes --append-system-prompt-file."""

    @unittest.skip("Phase 3")
    def test_mcp_config_for_tools(self):
        """Requested tools generate --mcp-config pointing to mcp_server.py."""

    @unittest.skip("Phase 3")
    def test_model_flag(self):
        """Model is resolved and passed as --model."""


class TestClaudeCodeTmuxNotSupported(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_build_tmux_wrapper_raises(self):
        """build_tmux_wrapper raises NotImplementedError."""

    @unittest.skip("Phase 3")
    def test_supports_tmux_false(self):
        """supports_tmux property returns False."""


class TestClaudeCodeRecordedOutput(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_parse_stream_json_output(self):
        """Recorded stream-json stdout parsed into correct results dict."""


if __name__ == "__main__":
    unittest.main()
