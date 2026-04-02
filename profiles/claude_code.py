"""Claude Code Runner Profile.

Encodes everything needed to spawn and read results from the Claude Code harness.
"""

from __future__ import annotations

from pathlib import Path
import json

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
        merged = dict(self.BUILTIN_MODEL_MAP)
        merged.update(models_config.profiles.get(self.name, {}))
        return merged

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        """Map a model name to the exact claude-specific string."""
        canonical = resolve_alias(name, models_config)
        model_map = self._effective_map(models_config)
        if canonical in model_map:
            mapped = model_map[canonical]
            if mapped is None:
                available = ", ".join(
                    key for key, value in model_map.items() if value is not None
                )
                raise ValueError(
                    f"Model '{name}' (canonical: '{canonical}') is not available "
                    f"on the claude-code harness. Available models: {available}"
                )
            return mapped
        return canonical

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        """Return (canonical_name, harness_id) pairs for all models."""
        return [
            (name, harness_id)
            for name, harness_id in self._effective_map(models_config).items()
            if harness_id is not None
        ]

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        """Build the full argv for headless claude execution."""
        cmd = cmd_override or "claude"
        args = [
            cmd,
            "-p",
            "--bare",
            "--output-format",
            "stream-json",
            "--append-system-prompt-file",
            system_prompt_file,
        ]

        if tools:
            mcp_config = self._build_mcp_config(tools)
            args += ["--mcp-config", json.dumps(mcp_config)]

        if model:
            config = models_config or ModelsConfig()
            args += ["--model", self.resolve_model(model, config)]

        args.append(prompt)
        return args

    def build_tmux_wrapper(self, **kwargs) -> str:
        """Claude Code tmux support is not yet implemented."""
        raise NotImplementedError(
            "Claude Code tmux support is not yet implemented. "
            "Use --no-tmux for headless execution."
        )

    def parse_headless_output(self, stdout: str) -> dict:
        """Parse captured stdout from headless mode."""
        return claude_stream_json.parse(stdout)

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        """Parse session/results from tmux mode."""
        raise NotImplementedError("Claude Code session parsing not yet implemented")

    def get_tool_paths(self) -> dict[str, str]:
        """Map tool names to MCP server paths."""
        mcp_path = f"mcp://{self._wf_dir}/tools/mcp_server.py"
        return {
            "report-result": mcp_path,
            "submit-plan": mcp_path,
            "record-brainstorm": mcp_path,
        }

    @property
    def supports_tmux(self) -> bool:
        return False

    def _build_mcp_config(self, tools: list[str]) -> dict:
        """Build MCP server config that exposes the requested tools."""
        return {
            "mcpServers": {
                "wf-tools": {
                    "command": "python3",
                    "args": [
                        f"{self._wf_dir}/tools/mcp_server.py",
                        "--tools",
                        ",".join(tools),
                    ],
                }
            }
        }

    @property
    def _wf_dir(self) -> str:
        return wf_dir()
