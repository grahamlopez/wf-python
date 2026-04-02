"""Agent subprocess spawning. Profile-driven - zero harness-specific code.

The runner is the bridge between the scheduler and the profile.
It handles process lifecycle while delegating all harness-specific
decisions to the active profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os

from wflib.types import (
    ModelsConfig,
    ReportResult,
    Usage,
    _dict_to_dataclass,
    extract_tool_call,
)


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
    if not os.path.exists(results_path):
        return AgentResult(
            exit_code=1,
            error=f"Results file not found: {results_path}",
        )

    try:
        with open(results_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        return AgentResult(
            exit_code=1,
            error=f"Malformed JSON in results file: {results_path}: {exc}",
        )
    except OSError as exc:
        return AgentResult(
            exit_code=1,
            error=f"Failed to read results file: {results_path}: {exc}",
        )

    messages = data.get("messages")
    if not isinstance(messages, list):
        messages = []

    usage_data = data.get("usage")
    if isinstance(usage_data, dict):
        usage = _dict_to_dataclass(Usage, usage_data)
    else:
        usage = Usage()

    report = extract_report_result(messages)
    if report is None:
        summary = extract_summary_fallback(messages)
        notes = ""
    else:
        summary = report.summary
        notes = report.notes

    return AgentResult(
        exit_code=data.get("exitCode", 0),
        summary=summary,
        notes=notes,
        error=None,
        usage=usage,
        model=data.get("model"),
        provider=data.get("provider"),
        messages=messages,
    )


def extract_report_result(messages: list[dict]) -> ReportResult | None:
    """Extract ReportResult from the agent's messages.
    Delegates to extract_tool_call(messages, 'report_result') from types.py.
    """
    result = extract_tool_call(messages, "report_result")
    if not isinstance(result, dict):
        return None
    return ReportResult(
        summary=result.get("summary", ""),
        notes=result.get("notes", ""),
    )


def extract_summary_fallback(messages: list[dict]) -> str:
    """Fallback when report_result was not called.
    Returns last 500 chars of the last assistant message's text content.
    """
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            if content:
                return content[-500:]
            continue
        if isinstance(content, list):
            for block in reversed(content):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "text":
                    continue
                text = block.get("text")
                if isinstance(text, str) and text:
                    return text[-500:]
    return ""
