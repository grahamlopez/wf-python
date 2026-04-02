"""Pi Runner Profile.

Encodes everything needed to spawn and read results from the pi agent harness.
"""

from __future__ import annotations

from pathlib import Path

from adapters import pi_json_mode, pi_session
from profiles import resolve_alias
from wflib.types import ModelsConfig


class PiProfile:
    name = "pi"

    # Built-in canonical name → exact pi model string.
    BUILTIN_MODEL_MAP: dict[str, str | None] = {
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-opus-4": "claude-opus-4",
        "claude-haiku-4-5": "claude-haiku-4-5",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gemini-pro": "gcp/google/gemini-3-pro",
    }

    def _effective_map(self, models_config: ModelsConfig) -> dict[str, str | None]:
        """Merge built-in MODEL_MAP with config [models.pi] overrides."""
        raise NotImplementedError("PiProfile._effective_map: not yet implemented")

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        """Map a model name to the exact pi-specific string."""
        raise NotImplementedError("PiProfile.resolve_model: not yet implemented")

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        """Return (canonical_name, harness_id) pairs for all models."""
        raise NotImplementedError("PiProfile.list_models: not yet implemented")

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        """Build the full argv for headless pi execution."""
        raise NotImplementedError("PiProfile.build_headless_cmd: not yet implemented")

    def build_tmux_wrapper(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt_file: str,
        session_dir: str,
        exit_code_file: str,
        results_file: str,
        auto_close: int | None = None,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> str:
        """Generate a bash wrapper for tmux execution."""
        raise NotImplementedError("PiProfile.build_tmux_wrapper: not yet implemented")

    def parse_headless_output(self, stdout: str) -> dict:
        """Parse captured stdout from headless mode."""
        raise NotImplementedError("PiProfile.parse_headless_output: not yet implemented")

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        """Parse session/results from tmux mode."""
        raise NotImplementedError("PiProfile.parse_session_output: not yet implemented")

    def get_tool_paths(self) -> dict[str, str]:
        """Map tool names to pi extension paths."""
        raise NotImplementedError("PiProfile.get_tool_paths: not yet implemented")

    @property
    def supports_tmux(self) -> bool:
        return True

    @property
    def _wf_dir(self) -> str:
        """Root of the wf installation (parent of profiles/)."""
        return str(Path(__file__).parent.parent)

    @property
    def _ext_dir(self) -> str:
        """Pi extensions directory (~/.pi/agent/extensions)."""
        return str(Path.home() / ".pi" / "agent" / "extensions")
