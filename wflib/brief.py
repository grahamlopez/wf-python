"""Deterministic task brief assembly.

Pure function - plan data in, string out.
"""

from __future__ import annotations

from wflib.types import Plan, Task, TaskResult


def assemble_task_brief(
    task: Task,
    plan: Plan,
    results: dict[str, TaskResult],
) -> str:
    """Build a scoped prompt for an implementation agent.

    Includes: context, file hints, constraints, prior work
    summaries (with diff stats), skills, goal, acceptance criteria.
    Ends with instruction to call report_result when done.
    """
    raise NotImplementedError("assemble_task_brief: not yet implemented")


def _render_prior_work(task: Task, results: dict[str, TaskResult]) -> str:
    """Format dependency task summaries for the brief."""
    raise NotImplementedError("_render_prior_work: not yet implemented")
