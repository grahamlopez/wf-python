"""Tests for profiles — protocol compliance, command construction, model resolution."""

import unittest

from profiles import BUILTIN_ALIASES, RunnerProfile, get_profile, resolve_alias
from profiles.pi import PiProfile
from profiles.claude_code import ClaudeCodeProfile
from profiles.mock import MockProfile
from wflib.types import ModelsConfig


class TestProfileProtocol(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_pi_implements_protocol(self):
        """PiProfile implements the full RunnerProfile protocol."""

    @unittest.skip("Phase 3")
    def test_claude_code_implements_protocol(self):
        """ClaudeCodeProfile implements the full RunnerProfile protocol."""

    @unittest.skip("Phase 3")
    def test_mock_implements_protocol(self):
        """MockProfile implements the full RunnerProfile protocol."""


class TestGetProfile(unittest.TestCase):
    def test_get_pi(self):
        """get_profile('pi') returns PiProfile."""
        profile = get_profile("pi")
        self.assertIsInstance(profile, PiProfile)

    def test_get_claude_code(self):
        """get_profile('claude-code') returns ClaudeCodeProfile."""
        profile = get_profile("claude-code")
        self.assertIsInstance(profile, ClaudeCodeProfile)

    def test_get_mock(self):
        """get_profile('mock') returns MockProfile."""
        profile = get_profile("mock")
        self.assertIsInstance(profile, MockProfile)

    def test_unknown_raises(self):
        """get_profile('unknown') raises ValueError."""
        with self.assertRaises(ValueError):
            get_profile("unknown")


class TestResolveAlias(unittest.TestCase):
    def test_builtin_alias(self):
        """'sonnet' resolves to 'claude-sonnet-4-5'."""
        self.assertEqual(
            resolve_alias("sonnet", ModelsConfig()),
            BUILTIN_ALIASES["sonnet"],
        )

    def test_config_alias_overrides_builtin(self):
        """Config aliases take precedence over built-in aliases."""
        models_config = ModelsConfig(aliases={"sonnet": "custom-sonnet"})
        self.assertEqual(
            resolve_alias("sonnet", models_config),
            "custom-sonnet",
        )

    def test_unknown_passes_through(self):
        """Unknown names pass through unchanged."""
        self.assertEqual(
            resolve_alias("unknown-thing", ModelsConfig()),
            "unknown-thing",
        )


class TestPiModelResolution(unittest.TestCase):
    def test_canonical_anthropic_identity(self):
        """Anthropic models map to themselves on pi."""
        profile = PiProfile()
        self.assertEqual(
            profile.resolve_model("claude-sonnet-4-5", ModelsConfig()),
            "claude-sonnet-4-5",
        )

    def test_gpt4o_maps_to_openai_prefix(self):
        """'gpt-4o' maps to 'openai/gpt-4o' on pi."""
        profile = PiProfile()
        self.assertEqual(
            profile.resolve_model("gpt-4o", ModelsConfig()),
            "openai/gpt-4o",
        )

    def test_config_override(self):
        """Config [models.pi] overrides built-in mapping."""
        profile = PiProfile()
        models_config = ModelsConfig(profiles={"pi": {"gpt-4o": "custom/gpt-4o"}})
        self.assertEqual(
            profile.resolve_model("gpt-4o", models_config),
            "custom/gpt-4o",
        )

    def test_unknown_passthrough(self):
        """Unknown model names pass through verbatim."""
        profile = PiProfile()
        self.assertEqual(
            profile.resolve_model("custom-model", ModelsConfig()),
            "custom-model",
        )


class TestPiCommandConstruction(unittest.TestCase):
    def test_headless_cmd_basic(self):
        """build_headless_cmd produces correct base argv."""
        profile = PiProfile()
        system_prompt = "/tmp/system.md"
        cmd = profile.build_headless_cmd(
            system_prompt_file=system_prompt,
            model=None,
            tools=[],
            prompt="Hello",
        )
        self.assertEqual(
            cmd,
            [
                "pi",
                "--mode",
                "json",
                "-p",
                "--no-session",
                "--no-extensions",
                "--append-system-prompt",
                system_prompt,
                "-e",
                f"{profile._ext_dir}/research.ts",
                "-e",
                f"{profile._ext_dir}/web-fetch/index.ts",
                "Hello",
            ],
        )

    def test_headless_cmd_with_model(self):
        """build_headless_cmd includes --model flag when model specified."""
        profile = PiProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model="sonnet",
            tools=[],
            prompt="Hello",
        )
        model_index = cmd.index("--model")
        self.assertEqual(cmd[model_index + 1], "claude-sonnet-4-5")

    def test_headless_cmd_with_tools(self):
        """build_headless_cmd includes -e flags for requested tools."""
        profile = PiProfile()
        tools = ["report-result", "submit-plan"]
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=tools,
            prompt="Hello",
        )
        tool_paths = profile.get_tool_paths()
        for tool in tools:
            tool_path = tool_paths[tool]
            self.assertIn(tool_path, cmd)
            self.assertEqual(cmd[cmd.index(tool_path) - 1], "-e")

    def test_headless_cmd_override(self):
        """cmd_override replaces the default binary path."""
        profile = PiProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=[],
            prompt="Hello",
            cmd_override="/opt/custom/pi",
        )
        self.assertEqual(cmd[0], "/opt/custom/pi")


class TestClaudeCodeModelResolution(unittest.TestCase):
    def test_anthropic_identity(self):
        """Anthropic models map to themselves on claude-code."""
        profile = ClaudeCodeProfile()
        self.assertEqual(
            profile.resolve_model("claude-opus-4", ModelsConfig()),
            "claude-opus-4",
        )

    def test_unavailable_model_raises(self):
        """'gpt-4o' raises ValueError on claude-code (not available)."""
        profile = ClaudeCodeProfile()
        with self.assertRaisesRegex(ValueError, "Available models"):
            profile.resolve_model("gpt-4o", ModelsConfig())


class TestClaudeCodeCommandConstruction(unittest.TestCase):
    def test_headless_cmd_basic(self):
        """build_headless_cmd produces correct base argv for claude."""
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
        self.assertIn("--append-system-prompt-file", cmd)
        self.assertEqual(cmd[-1], "hello")

    def test_headless_cmd_with_mcp_tools(self):
        """build_headless_cmd includes --mcp-config for tools."""
        profile = ClaudeCodeProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="system.md",
            model=None,
            tools=["report-result"],
            prompt="hello",
            models_config=ModelsConfig(),
        )
        self.assertIn("--mcp-config", cmd)

    def test_tmux_not_supported(self):
        """build_tmux_wrapper raises NotImplementedError."""
        profile = ClaudeCodeProfile()
        with self.assertRaises(NotImplementedError):
            profile.build_tmux_wrapper()


class TestMockProfile(unittest.TestCase):
    def test_headless_cmd(self):
        """build_headless_cmd returns mock agent invocation."""
        profile = MockProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="system.md",
            model=None,
            tools=[],
            prompt="brief.md",
            models_config=ModelsConfig(),
        )
        self.assertEqual(cmd[0], "python3")
        self.assertTrue(cmd[1].endswith("tests/e2e/mock_agent.py"))
        self.assertEqual(cmd[2], "brief.md")

    def test_tmux_not_supported(self):
        """build_tmux_wrapper raises NotImplementedError."""
        profile = MockProfile()
        with self.assertRaises(NotImplementedError):
            profile.build_tmux_wrapper()

    def test_list_models_empty(self):
        """list_models returns empty list."""
        profile = MockProfile()
        self.assertEqual(profile.list_models(ModelsConfig()), [])


if __name__ == "__main__":
    unittest.main()
