"""Agent subprocess spawning. Profile-driven - zero harness-specific code.

The runner is the bridge between the scheduler and the profile.
It handles process lifecycle while delegating all harness-specific
decisions to the active profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import subprocess
import tempfile

from wflib import tmux
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
    results_path = os.environ.get("WF_RESULTS_PATH")
    if not results_path:
        results_path = os.path.join(cwd, "results.json")

    system_prompt_file: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write(system_prompt)
            handle.flush()
            system_prompt_file = handle.name

        cmd = profile.build_headless_cmd(
            system_prompt_file=system_prompt_file,
            model=model,
            tools=tools,
            prompt=prompt,
            cmd_override=cmd_override,
            models_config=models_config,
        )

        env = os.environ.copy()
        env.setdefault("WF_RESULTS_PATH", results_path)

        timeout = None
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            return AgentResult(
                exit_code=1,
                error=f"Agent timed out after {exc.timeout} seconds",
            )

        results = profile.parse_headless_output(completed.stdout)
        if results or not os.path.exists(results_path):
            try:
                results_dir = os.path.dirname(results_path)
                if results_dir:
                    os.makedirs(results_dir, exist_ok=True)
                with open(results_path, "w", encoding="utf-8") as handle:
                    json.dump(results, handle)
            except OSError as exc:
                return AgentResult(
                    exit_code=1,
                    error=f"Failed to write results file: {results_path}: {exc}",
                )

        if completed.returncode != 0 and not os.path.exists(results_path):
            error = completed.stderr.strip() or (
                f"Agent exited with code {completed.returncode}"
            )
            return AgentResult(exit_code=completed.returncode, error=error)

        return _read_agent_results(results_path)
    except Exception as exc:
        return AgentResult(exit_code=1, error=f"Failed to spawn agent: {exc}")
    finally:
        if system_prompt_file and os.path.exists(system_prompt_file):
            try:
                os.remove(system_prompt_file)
            except OSError:
                pass


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
    if not profile.supports_tmux:
        raise NotImplementedError(
            f"Profile '{profile.name}' does not support tmux execution."
        )

    results_path = os.environ.get("WF_RESULTS_PATH")
    if not results_path:
        results_path = os.path.join(cwd, "results.json")

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    system_prompt_file: str | None = None
    prompt_file: str | None = None
    wrapper_file: str | None = None
    exit_code_file: str | None = None

    try:
        temp_dir = tempfile.TemporaryDirectory()
        base_dir = temp_dir.name

        if preserve_session_dir:
            session_dir = preserve_session_dir
            os.makedirs(session_dir, exist_ok=True)
        else:
            session_dir = os.path.join(base_dir, "session")
            os.makedirs(session_dir, exist_ok=True)

        results_dir = os.path.dirname(results_path)
        if results_dir:
            os.makedirs(results_dir, exist_ok=True)

        exit_code_file = os.path.join(base_dir, "exit-code")

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8",
            dir=base_dir,
        ) as handle:
            handle.write(prompt)
            handle.flush()
            prompt_file = handle.name

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8",
            dir=base_dir,
        ) as handle:
            handle.write(system_prompt)
            handle.flush()
            system_prompt_file = handle.name

        wrapper_script = profile.build_tmux_wrapper(
            system_prompt_file=system_prompt_file,
            model=model,
            tools=tools,
            prompt_file=prompt_file,
            session_dir=session_dir,
            exit_code_file=exit_code_file,
            results_file=results_path,
            auto_close=auto_close,
            cmd_override=cmd_override,
            models_config=models_config,
        )

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8",
            dir=base_dir,
        ) as handle:
            handle.write(wrapper_script)
            handle.flush()
            wrapper_file = handle.name

        os.chmod(wrapper_file, 0o755)

        command = tmux.shell_escape(wrapper_file)
        pane_id = tmux.get_or_create_execution_pane(
            cwd=cwd,
            command=command,
            workflow_label=workflow_label,
            task_id=task_id,
            task_title=task_title,
        )
        tmux.wait_for_exit_code_file(exit_code_file, pane_id)

        return _read_agent_results(results_path)
    except Exception as exc:
        return AgentResult(exit_code=1, error=f"Failed to spawn agent in tmux: {exc}")
    finally:
        for path in (system_prompt_file, prompt_file, wrapper_file, exit_code_file):
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        if temp_dir is not None:
            temp_dir.cleanup()


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
