"""Mock Profile for E2E Tests.

Deterministic mock profile for E2E testing.
Reads WF_TEST_SCENARIO env var to locate the scenario file.
"""

from __future__ import annotations

from pathlib import Path

from profiles import resolve_alias, wf_dir
from wflib.types import ModelsConfig


class MockProfile:
    """Deterministic mock profile for E2E testing."""
    name = "mock"

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        """Resolve aliases, no harness-specific mapping."""
        return resolve_alias(name, models_config)

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        """Mock doesn't have real models."""
        return []

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        """Build command for the mock agent."""
        mock_agent = cmd_override or f"{self._wf_dir}/tests/e2e/mock_agent.py"
        return ["python3", mock_agent, prompt]

    def build_tmux_wrapper(self, **kwargs) -> str:
        """Mock profile does not support tmux."""
        raise NotImplementedError("Mock profile does not support tmux")

    def parse_headless_output(self, stdout: str) -> dict:
        """Mock agent writes results.json directly; stdout is ignored."""
        return {}

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        """Mock profile does not have sessions."""
        raise NotImplementedError("Mock profile does not have sessions")

    def get_tool_paths(self) -> dict[str, str]:
        """Mock agent doesn't need tool extensions."""
        return {}

    @property
    def supports_tmux(self) -> bool:
        return False

    @property
    def _wf_dir(self) -> str:
        return wf_dir()
