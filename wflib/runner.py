"""Agent subprocess spawning. Profile-driven - zero harness-specific code.

The runner is the bridge between the scheduler and the profile.
It handles process lifecycle while delegating all harness-specific
decisions to the active profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wflib.types import ModelsConfig, ReportResult, Usage


@dataclass
class AgentResult:
    exit_code: int = 0
    summary: str = ""
    notes: str = ""
    error: str | None = None
    usage: Usage = field(default_factory=Usage)
    model: str | None = None
    provider: str | None = None
    messages: list[dict] = field(default_factory=list)


def spawn_headless(
    cwd: str,
    prompt: str,
    system_prompt: str,
    profile: 'RunnerProfile',
    tools: list[str],
    model: str | None = None,
    cmd_override: str | None = None,
    models_config: ModelsConfig | None = None,
) -> AgentResult:
    """Spawn a headless agent subprocess."""
    raise NotImplementedError("spawn_headless: not yet implemented")


def spawn_in_tmux(
    cwd: str,
    prompt: str,
    system_prompt: str,
    profile: 'RunnerProfile',
    tools: list[str],
    task_id: str,
    task_title: str,
    workflow_label: str,
    model: str | None = None,
    auto_close: int | None = None,
    cmd_override: str | None = None,
    preserve_session_dir: str | None = None,
    models_config: ModelsConfig | None = None,
) -> AgentResult:
    """Spawn agent in a tmux pane. Wait for completion via exit-code file."""
    raise NotImplementedError("spawn_in_tmux: not yet implemented")


def _read_agent_results(results_path: str) -> AgentResult:
    """Read a results.json file into an AgentResult."""
    raise NotImplementedError("_read_agent_results: not yet implemented")


def extract_report_result(messages: list[dict]) -> ReportResult | None:
    """Extract ReportResult from the agent's messages.
    Delegates to extract_tool_call(messages, 'report_result') from types.py.
    """
    raise NotImplementedError("extract_report_result: not yet implemented")


def extract_summary_fallback(messages: list[dict]) -> str:
    """Fallback when report_result was not called.
    Returns last 500 chars of the last assistant message's text content.
    """
    raise NotImplementedError("extract_summary_fallback: not yet implemented")
