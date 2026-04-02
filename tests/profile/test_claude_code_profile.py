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
    def test_parse_stream_json_output(self):
        """Recorded stream-json stdout parsed into correct results dict."""
        import json

        profile = ClaudeCodeProfile()
        stdout = "\n".join(
            json.dumps(event)
            for event in [
                {
                    "type": "assistant",
                    "message": {"role": "assistant", "content": []},
                },
                {"type": "text", "text": "Drafting"},
                {
                    "type": "tool_use",
                    "name": "report_result",
                    "input": {"summary": "All set", "notes": ""},
                },
                {
                    "type": "result",
                    "model": "claude-sonnet-4-5",
                    "usage": {
                        "input_tokens": 18,
                        "output_tokens": 6,
                        "cache_read_input_tokens": 2,
                        "cache_creation_input_tokens": 1,
                        "cost": 0.012,
                        "turns": 1,
                    },
                },
            ]
        )

        result = profile.parse_headless_output(stdout)
        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["model"], "claude-sonnet-4-5")
        self.assertEqual(result["provider"], "anthropic")
        self.assertEqual(
            result["usage"],
            {
                "input": 18,
                "output": 6,
                "cacheRead": 2,
                "cacheWrite": 1,
                "cost": 0.012,
                "turns": 1,
            },
        )
        self.assertEqual(
            result["messages"],
            [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Drafting"},
                        {
                            "type": "toolCall",
                            "name": "report_result",
                            "arguments": {"summary": "All set", "notes": ""},
                        },
                    ],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
