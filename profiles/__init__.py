"""Runner profiles for wf - one per agent harness."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from wflib.types import ModelsConfig


class RunnerProfile(Protocol):
    """Complete interface for driving one agent harness."""

    name: str

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        """Build the full argv for headless (non-interactive) execution."""
        ...

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
        """Return the full shell script content for a tmux wrapper."""
        ...

    def parse_headless_output(self, stdout: str) -> dict:
        """Parse captured stdout from headless mode into a results dict."""
        ...

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        """Parse session/results from tmux mode into a results dict."""
        ...

    def get_tool_paths(self) -> dict[str, str]:
        """Map tool names to their implementation paths."""
        ...

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        """Map a model name to the exact string for this harness."""
        ...

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        """Return (canonical_name, harness_id) pairs for all models."""
        ...

    @property
    def supports_tmux(self) -> bool:
        """Whether this profile supports interactive tmux mode."""
        ...


# --- Built-in aliases (shared across all profiles) ---

BUILTIN_ALIASES: dict[str, str] = {
    "sonnet": "claude-sonnet-4-5",
    "opus": "claude-opus-4",
    "haiku": "claude-haiku-4-5",
}


def resolve_alias(name: str, models_config: ModelsConfig) -> str:
    """Resolve a model alias to its canonical name.
    Config aliases (models_config.aliases) override built-in aliases.
    Returns the input unchanged if it's not a known alias.
    """
    raise NotImplementedError("resolve_alias: not yet implemented")


def wf_dir() -> str:
    """Root of the wf installation (parent of profiles/)."""
    return str(Path(__file__).resolve().parent.parent)


# --- Profile registry ---

def get_profile(name: str) -> RunnerProfile:
    """Look up a profile by name. Raises ValueError for unknown profiles.

    Built-in profiles:
      - "pi"          PiProfile (default)
      - "claude-code"  ClaudeCodeProfile
      - "mock"         MockProfile (for E2E tests)
    """
    raise NotImplementedError("get_profile: not yet implemented")
