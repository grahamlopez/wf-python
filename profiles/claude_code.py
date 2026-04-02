"""Claude Code Runner Profile.

Encodes everything needed to spawn and read results from the Claude Code harness.
"""

from __future__ import annotations

from pathlib import Path

from adapters import claude_stream_json
from profiles import resolve_alias, wf_dir
from wflib.types import ModelsConfig


class ClaudeCodeProfile:
    name = "claude-code"

    # Built-in canonical name → exact claude CLI model string.
    BUILTIN_MODEL_MAP: dict[str, str | None] = {
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-opus-4": "claude-opus-4",
        "claude-haiku-4-5": "claude-haiku-4-5",
        "gpt-4o": None,
        "gpt-4o-mini": None,
        "gemini-pro": None,
    }

    def _effective_map(self, models_config: ModelsConfig) -> dict[str, str | None]:
        """Merge built-in MODEL_MAP with config [models.claude-code] overrides."""
        raise NotImplementedError("ClaudeCodeProfile._effective_map: not yet implemented")

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        """Map a model name to the exact claude-specific string."""
        raise NotImplementedError("ClaudeCodeProfile.resolve_model: not yet implemented")

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        """Return (canonical_name, harness_id) pairs for all models."""
        raise NotImplementedError("ClaudeCodeProfile.list_models: not yet implemented")

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        """Build the full argv for headless claude execution."""
        raise NotImplementedError("ClaudeCodeProfile.build_headless_cmd: not yet implemented")

    def build_tmux_wrapper(self, **kwargs) -> str:
        """Claude Code tmux support is not yet implemented."""
        raise NotImplementedError(
            "Claude Code tmux support is not yet implemented. "
            "Use --no-tmux for headless execution."
        )

    def parse_headless_output(self, stdout: str) -> dict:
        """Parse captured stdout from headless mode."""
        raise NotImplementedError("ClaudeCodeProfile.parse_headless_output: not yet implemented")

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        """Parse session/results from tmux mode."""
        raise NotImplementedError("Claude Code session parsing not yet implemented")

    def get_tool_paths(self) -> dict[str, str]:
        """Map tool names to MCP server paths."""
        raise NotImplementedError("ClaudeCodeProfile.get_tool_paths: not yet implemented")

    @property
    def supports_tmux(self) -> bool:
        return False

    def _build_mcp_config(self, tools: list[str]) -> dict:
        """Build MCP server config that exposes the requested tools."""
        raise NotImplementedError("ClaudeCodeProfile._build_mcp_config: not yet implemented")

    @property
    def _wf_dir(self) -> str:
        return wf_dir()
