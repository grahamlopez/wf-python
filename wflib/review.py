"""Code review orchestration - diff context building and review agent spawning."""

from __future__ import annotations

from dataclasses import dataclass, field

from wflib.types import Plan, Usage, WorkflowConfig


@dataclass
class ReviewResult:
    review_text: str = ""
    usage: Usage = field(default_factory=Usage)
    model: str | None = None
    provider: str | None = None


@dataclass
class AutoReviewResult(ReviewResult):
    plan: Plan | None = None      # fixup plan, if issues found


def build_diff_context(cwd: str, base_commit: str | None = None) -> str:
    """Build markdown diff context (commits, stat, full diff).
    Caps full diff at 100KB. Falls back to uncommitted changes.
    """
    raise NotImplementedError("build_diff_context: not yet implemented")


async def run_review(
    cwd: str,
    config: WorkflowConfig,
    base_commit: str | None = None,
    description: str | None = None,
    scope: str | None = None,
    cli_model: str | None = None,
) -> ReviewResult:
    """Spawn a code review subagent."""
    raise NotImplementedError("run_review: not yet implemented")


async def run_auto_review(
    cwd: str,
    config: WorkflowConfig,
    base_commit: str | None = None,
    cli_model: str | None = None,
) -> AutoReviewResult:
    """Spawn review agent with submit_plan tool."""
    raise NotImplementedError("run_auto_review: not yet implemented")


def extract_plan_from_messages(messages: list[dict]) -> dict | None:
    """Extract a fixup plan from the review agent's messages."""
    raise NotImplementedError("extract_plan_from_messages: not yet implemented")
