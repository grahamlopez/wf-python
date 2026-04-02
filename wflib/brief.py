"""Deterministic task brief assembly.

Pure function - plan data in, string out.
"""

from __future__ import annotations

from wflib.types import Plan, Task, TaskResult, TaskStatus


def assemble_task_brief(
    task: Task,
    plan: Plan,
    results: dict[str, TaskResult],
) -> str:
    """Build a scoped prompt for an implementation agent.

    Includes: context, file hints, constraints, prior work
    summaries (with diff stats), skills, goal, acceptance criteria.
    Ends with instruction to call report_result when done.

    Does NOT include: other tasks, planner reasoning, step-by-step instructions.
    """
    sections: list[str] = []

    # Title
    sections.append(f"# Task: {task.title}")

    # Plan context
    sections.append(f"## Context\n{plan.context}")

    # File hints
    if task.files:
        file_list = "\n".join(f"- `{f}`" for f in task.files)
        sections.append(f"## Relevant Files (start here)\n{file_list}")

    # Constraints
    if task.constraints:
        constraint_list = "\n".join(f"- {c}" for c in task.constraints)
        sections.append(f"## Constraints\n{constraint_list}")

    # Prior work summaries
    prior_work = _render_prior_work(task, results)
    if prior_work:
        sections.append(prior_work)

    # Skills hint
    if task.skills:
        skill_names = ", ".join(task.skills)
        sections.append(
            f"## Skills\nThese skills may be useful: {skill_names}. "
            "Load them with the appropriate skill loading mechanism if needed."
        )

    # Goal
    sections.append(f"## Goal\n{task.goal}")

    # Acceptance criteria
    if task.acceptance:
        criteria_list = "\n".join(f"- {a}" for a in task.acceptance)
        sections.append(f"## Done When\n{criteria_list}")

    # Report result instruction
    sections.append(
        "## When You Are Done\n"
        "Call the report_result tool with a summary of what was accomplished "
        "and any notes about difficulties, surprises, or things the caller "
        "should know."
    )

    return "\n\n".join(sections) + "\n"


def _render_prior_work(task: Task, results: dict[str, TaskResult]) -> str:
    """Format dependency task summaries for the brief.

    Only includes tasks listed in task.depends_on that have status 'done'
    in results. Returns empty string if there are no completed dependencies.
    """
    if not task.depends_on:
        return ""

    completed: list[str] = []
    for dep_id in task.depends_on:
        dep_result = results.get(dep_id)
        if dep_result is None or dep_result.status != TaskStatus.DONE:
            continue

        parts = [f"### {dep_id}"]
        if dep_result.summary:
            parts.append(dep_result.summary)
        if dep_result.diff_stat:
            parts.append(f"```\n{dep_result.diff_stat}\n```")
        if dep_result.notes:
            parts.append(f"Notes: {dep_result.notes}")

        completed.append("\n".join(parts))

    if not completed:
        return ""

    return "## Prior Work\nThese tasks were completed by other agents. Their changes are already on disk — read the files for current state.\n\n" + "\n\n".join(completed)
