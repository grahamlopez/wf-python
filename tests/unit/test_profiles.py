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
    @unittest.skip("Phase 3")
    def test_get_pi(self):
        """get_profile('pi') returns PiProfile."""

    @unittest.skip("Phase 3")
    def test_get_claude_code(self):
        """get_profile('claude-code') returns ClaudeCodeProfile."""

    @unittest.skip("Phase 3")
    def test_get_mock(self):
        """get_profile('mock') returns MockProfile."""

    @unittest.skip("Phase 3")
    def test_unknown_raises(self):
        """get_profile('unknown') raises ValueError."""


class TestResolveAlias(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_builtin_alias(self):
        """'sonnet' resolves to 'claude-sonnet-4-5'."""

    @unittest.skip("Phase 3")
    def test_config_alias_overrides_builtin(self):
        """Config aliases take precedence over built-in aliases."""

    @unittest.skip("Phase 3")
    def test_unknown_passes_through(self):
        """Unknown names pass through unchanged."""


class TestPiModelResolution(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_canonical_anthropic_identity(self):
        """Anthropic models map to themselves on pi."""

    @unittest.skip("Phase 3")
    def test_gpt4o_maps_to_openai_prefix(self):
        """'gpt-4o' maps to 'openai/gpt-4o' on pi."""

    @unittest.skip("Phase 3")
    def test_config_override(self):
        """Config [models.pi] overrides built-in mapping."""

    @unittest.skip("Phase 3")
    def test_unknown_passthrough(self):
        """Unknown model names pass through verbatim."""


class TestPiCommandConstruction(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_headless_cmd_basic(self):
        """build_headless_cmd produces correct base argv."""

    @unittest.skip("Phase 3")
    def test_headless_cmd_with_model(self):
        """build_headless_cmd includes --model flag when model specified."""

    @unittest.skip("Phase 3")
    def test_headless_cmd_with_tools(self):
        """build_headless_cmd includes -e flags for requested tools."""

    @unittest.skip("Phase 3")
    def test_headless_cmd_override(self):
        """cmd_override replaces the default binary path."""


class TestClaudeCodeModelResolution(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_anthropic_identity(self):
        """Anthropic models map to themselves on claude-code."""

    @unittest.skip("Phase 3")
    def test_unavailable_model_raises(self):
        """'gpt-4o' raises ValueError on claude-code (not available)."""


class TestClaudeCodeCommandConstruction(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_headless_cmd_basic(self):
        """build_headless_cmd produces correct base argv for claude."""

    @unittest.skip("Phase 3")
    def test_headless_cmd_with_mcp_tools(self):
        """build_headless_cmd includes --mcp-config for tools."""

    @unittest.skip("Phase 3")
    def test_tmux_not_supported(self):
        """build_tmux_wrapper raises NotImplementedError."""


class TestMockProfile(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_headless_cmd(self):
        """build_headless_cmd returns mock agent invocation."""

    @unittest.skip("Phase 3")
    def test_tmux_not_supported(self):
        """build_tmux_wrapper raises NotImplementedError."""

    @unittest.skip("Phase 3")
    def test_list_models_empty(self):
        """list_models returns empty list."""


if __name__ == "__main__":
    unittest.main()
