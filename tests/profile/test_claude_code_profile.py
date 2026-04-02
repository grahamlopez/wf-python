"""Tests for profiles.claude_code — command construction + recorded output."""

import unittest

from profiles.claude_code import ClaudeCodeProfile
from wflib.types import ModelsConfig


class TestClaudeCodeHeadlessCommand(unittest.TestCase):
    def test_basic_command_structure(self):
        """Headless command starts with claude -p --bare --output-format stream-json."""
        profile = ClaudeCodeProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="system.md",
            model=None,
            tools=[],
            prompt="hello",
            models_config=ModelsConfig(),
        )
        self.assertEqual(
            cmd[:5],
            ["claude", "-p", "--bare", "--output-format", "stream-json"],
        )
        self.assertEqual(cmd[-1], "hello")

    def test_appends_system_prompt(self):
        """Command includes --append-system-prompt-file."""
        profile = ClaudeCodeProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="system.md",
            model=None,
            tools=[],
            prompt="hello",
            models_config=ModelsConfig(),
        )
        index = cmd.index("--append-system-prompt-file")
        self.assertEqual(cmd[index + 1], "system.md")

    def test_mcp_config_for_tools(self):
        """Requested tools generate --mcp-config pointing to mcp_server.py."""
        import json

        profile = ClaudeCodeProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="system.md",
            model=None,
            tools=["report-result", "submit-plan"],
            prompt="hello",
            models_config=ModelsConfig(),
        )
        index = cmd.index("--mcp-config")
        mcp_config = json.loads(cmd[index + 1])
        server = mcp_config["mcpServers"]["wf-tools"]
        self.assertEqual(server["command"], "python3")
        self.assertEqual(
            server["args"],
            [
                f"{profile._wf_dir}/tools/mcp_server.py",
                "--tools",
                "report-result,submit-plan",
            ],
        )

    def test_model_flag(self):
        """Model is resolved and passed as --model."""
        profile = ClaudeCodeProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="system.md",
            model="claude-opus-4",
            tools=[],
            prompt="hello",
            models_config=ModelsConfig(),
        )
        index = cmd.index("--model")
        self.assertEqual(cmd[index + 1], "claude-opus-4")


class TestClaudeCodeTmuxNotSupported(unittest.TestCase):
    def test_build_tmux_wrapper_raises(self):
        """build_tmux_wrapper raises NotImplementedError."""
        profile = ClaudeCodeProfile()
        with self.assertRaises(NotImplementedError):
            profile.build_tmux_wrapper()

    def test_supports_tmux_false(self):
        """supports_tmux property returns False."""
        profile = ClaudeCodeProfile()
        self.assertFalse(profile.supports_tmux)


class TestClaudeCodeRecordedOutput(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_parse_stream_json_output(self):
        """Recorded stream-json stdout parsed into correct results dict."""


if __name__ == "__main__":
    unittest.main()
