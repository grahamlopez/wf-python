"""Code review orchestration - diff context building and review agent spawning."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

from wflib import git as gitmod
from wflib import runner
from wflib.types import (
    Plan,
    Usage,
    WorkflowConfig,
    extract_tool_call,
    plan_from_json,
)
from profiles import get_profile, wf_dir


# --- Constants ---

_DIFF_CAP_BYTES = 100 * 1024  # 100KB cap on full diff


# --- Result dataclasses ---

@dataclass
class ReviewResult:
    review_text: str = ""
    usage: Usage = field(default_factory=Usage)
    model: str | None = None
    provider: str | None = None


@dataclass
class AutoReviewResult(ReviewResult):
    plan: Plan | None = None      # fixup plan, if issues found


# --- Diff context ---

def build_diff_context(cwd: str, base_commit: str | None = None) -> str:
    """Build markdown diff context (commits, stat, full diff).
    Caps full diff at 100KB. Falls back to uncommitted changes if no base_commit.
    """
    sections: list[str] = []

    if base_commit:
        # Commit log since base
        log_result = gitmod.git(
            ["log", "--oneline", f"{base_commit}..HEAD"], cwd=cwd
        )
        if log_result.ok and log_result.stdout.strip():
            sections.append(
                f"## Commits since {base_commit[:8]}\n\n```\n{log_result.stdout.strip()}\n```"
            )

        # Diff stat
        stat_result = gitmod.git(
            ["diff", "--stat", base_commit, "HEAD"], cwd=cwd
        )
        if stat_result.ok and stat_result.stdout.strip():
            sections.append(
                f"## Diff stat\n\n```\n{stat_result.stdout.strip()}\n```"
            )

        # Full diff (capped)
        diff_result = gitmod.git(
            ["diff", base_commit, "HEAD"], cwd=cwd
        )
        if diff_result.ok and diff_result.stdout.strip():
            diff_text = diff_result.stdout
            if len(diff_text.encode("utf-8", errors="replace")) > _DIFF_CAP_BYTES:
                diff_text = diff_text[: _DIFF_CAP_BYTES] + "\n\n... (diff truncated at 100KB)"
            sections.append(f"## Full diff\n\n```diff\n{diff_text.strip()}\n```")
    else:
        # Fallback: uncommitted changes
        stat_result = gitmod.git(["diff", "--stat"], cwd=cwd)
        if stat_result.ok and stat_result.stdout.strip():
            sections.append(
                f"## Diff stat (uncommitted)\n\n```\n{stat_result.stdout.strip()}\n```"
            )

        diff_result = gitmod.git(["diff"], cwd=cwd)
        if diff_result.ok and diff_result.stdout.strip():
            diff_text = diff_result.stdout
            if len(diff_text.encode("utf-8", errors="replace")) > _DIFF_CAP_BYTES:
                diff_text = diff_text[: _DIFF_CAP_BYTES] + "\n\n... (diff truncated at 100KB)"
            sections.append(f"## Full diff (uncommitted)\n\n```diff\n{diff_text.strip()}\n```")

        # Also include staged changes
        staged_stat = gitmod.git(["diff", "--stat", "--cached"], cwd=cwd)
        if staged_stat.ok and staged_stat.stdout.strip():
            sections.append(
                f"## Staged changes\n\n```\n{staged_stat.stdout.strip()}\n```"
            )

        staged_diff = gitmod.git(["diff", "--cached"], cwd=cwd)
        if staged_diff.ok and staged_diff.stdout.strip():
            diff_text = staged_diff.stdout
            if len(diff_text.encode("utf-8", errors="replace")) > _DIFF_CAP_BYTES:
                diff_text = diff_text[: _DIFF_CAP_BYTES] + "\n\n... (diff truncated at 100KB)"
            sections.append(f"## Staged diff\n\n```diff\n{diff_text.strip()}\n```")

    if not sections:
        return "# Diff Context\n\nNo changes detected.\n"

    return "# Diff Context\n\n" + "\n\n".join(sections) + "\n"


# --- Prompt loading ---

def _load_prompt(filename: str) -> str:
    """Load a prompt file from the prompts/ directory."""
    prompt_path = os.path.join(wf_dir(), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# --- Extract last assistant text ---

def _extract_last_assistant_text(messages: list[dict]) -> str:
    """Extract the text content from the last assistant message."""
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            if content:
                return content
            continue
        if isinstance(content, list):
            for block in reversed(content):
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "text":
                    continue
                text = block.get("text")
                if isinstance(text, str) and text:
                    return text
    return ""


# --- Review orchestration ---

async def run_review(
    cwd: str,
    config: WorkflowConfig,
    base_commit: str | None = None,
    description: str | None = None,
    scope: str | None = None,
    cli_model: str | None = None,
) -> ReviewResult:
    """Spawn a code review subagent.

    Reads profile, tmux, auto_close from config. Resolves the runner
    profile and delegates spawning to runner.py.
    Uses config.model.review as default model; cli_model overrides.
    """
    profile = get_profile(config.agent.profile)
    model = cli_model or config.model.review

    # Build the diff context
    diff_context = build_diff_context(cwd, base_commit)

    # Build prompt
    prompt_parts: list[str] = []
    if description:
        prompt_parts.append(f"## Review Description\n\n{description}")
    if scope:
        prompt_parts.append(f"## Review Scope\n\n{scope}")
    prompt_parts.append(diff_context)
    prompt = "\n\n".join(prompt_parts)

    # Load system prompt
    system_prompt = _load_prompt("reviewer.md")

    # Spawn the agent
    result = await asyncio.to_thread(
        runner.spawn_headless,
        cwd=cwd,
        prompt=prompt,
        system_prompt=system_prompt,
        profile=profile,
        tools=[],
        model=model,
        models_config=config.models,
    )

    review_text = _extract_last_assistant_text(result.messages)

    return ReviewResult(
        review_text=review_text,
        usage=result.usage,
        model=result.model,
        provider=result.provider,
    )


async def run_auto_review(
    cwd: str,
    config: WorkflowConfig,
    base_commit: str | None = None,
    cli_model: str | None = None,
) -> AutoReviewResult:
    """Spawn review agent with submit_plan tool.

    Uses prompts/reviewer-with-plan.md as system prompt.
    After agent exits, extracts submit_plan tool call from messages.
    If found, parses into a Plan and validates it.
    Returns AutoReviewResult with optional fixup plan.
    """
    profile = get_profile(config.agent.profile)
    model = cli_model or config.model.review

    # Build the diff context
    diff_context = build_diff_context(cwd, base_commit)

    # Load system prompt
    system_prompt = _load_prompt("reviewer-with-plan.md")

    # Get tool paths — we need submit-plan for auto-review
    tool_paths = profile.get_tool_paths()
    tools: list[str] = []
    if "submit-plan" in tool_paths:
        tools.append(tool_paths["submit-plan"])

    # Spawn the agent
    result = await asyncio.to_thread(
        runner.spawn_headless,
        cwd=cwd,
        prompt=diff_context,
        system_prompt=system_prompt,
        profile=profile,
        tools=tools,
        model=model,
        models_config=config.models,
    )

    review_text = _extract_last_assistant_text(result.messages)

    # Try to extract a fixup plan from the agent's messages
    plan = extract_plan_from_messages(result.messages)

    return AutoReviewResult(
        review_text=review_text,
        usage=result.usage,
        model=result.model,
        provider=result.provider,
        plan=plan,
    )


def extract_plan_from_messages(messages: list[dict]) -> Plan | None:
    """Extract a fixup plan from the review agent's messages.

    Delegates to extract_tool_call(messages, 'submit_plan') from types.py,
    then converts to Plan via plan_from_json. Returns None if the reviewer
    found no actionable issues (i.e. did not call submit_plan).
    """
    plan_data = extract_tool_call(messages, "submit_plan")
    if plan_data is None:
        return None
    try:
        return plan_from_json(plan_data)
    except (ValueError, TypeError):
        return None
