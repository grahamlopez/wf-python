"""All text rendering - markdown, usage tables, status formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass

from wflib.types import (
    Plan,
    PlanRecord,
    Task,
    TaskStatus,
    WorkflowRecord,
    WorkflowStatus,
)


@dataclass
class UsageRow:
    label: str = ""
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    turns: int = 0
    model: str | None = None


# --- Simple formatting helpers ---


def fmt_num(n: int) -> str:
    """Format a number with comma separators."""
    return f"{n:,}"


def fmt_cost(n: float) -> str:
    """Format a cost value as dollar amount."""
    if n < 1.0:
        return f"${n:.3f}"
    return f"${n:.2f}"


def fmt_duration(seconds: int) -> str:
    """Format a duration in human-readable form."""
    if seconds < 60:
        return "<1m"
    if seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m"


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    # Lowercase
    slug = text.lower()
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Collapse consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def workflow_label(workflow_id: str, name: str) -> str:
    """Create a display label for a workflow."""
    return f"{name} [{workflow_id}]"


# --- Usage table ---

_STATUS_ICONS = {
    TaskStatus.PENDING: "○",
    TaskStatus.RUNNING: "⏳",
    TaskStatus.DONE: "✓",
    TaskStatus.FAILED: "✗",
    TaskStatus.SKIPPED: "⊘",
}


def format_usage_table(rows: list[UsageRow]) -> str:
    """Markdown table with per-phase and total token usage."""
    if not rows:
        return ""

    # Compute totals
    total_input = sum(r.input for r in rows)
    total_output = sum(r.output for r in rows)
    total_cache_read = sum(r.cache_read for r in rows)
    total_cache_write = sum(r.cache_write for r in rows)
    total_cost = sum(r.cost for r in rows)
    total_turns = sum(r.turns for r in rows)

    lines = []
    lines.append("| Label | Input | Output | Cache Read | Cache Write | Cost | Turns |")
    lines.append("|-------|-------|--------|------------|-------------|------|-------|")

    for r in rows:
        lines.append(
            f"| {r.label} | {fmt_num(r.input)} | {fmt_num(r.output)} "
            f"| {fmt_num(r.cache_read)} | {fmt_num(r.cache_write)} "
            f"| {fmt_cost(r.cost)} | {r.turns} |"
        )

    lines.append(
        f"| **Total** | {fmt_num(total_input)} | {fmt_num(total_output)} "
        f"| {fmt_num(total_cache_read)} | {fmt_num(total_cache_write)} "
        f"| {fmt_cost(total_cost)} | {total_turns} |"
    )

    return "\n".join(lines)


# --- Plan rendering ---


def render_plan_markdown(plan: Plan) -> str:
    """Render just the plan portion as markdown."""
    lines: list[str] = []

    lines.append(f"# Goal\n")
    lines.append(plan.goal)
    lines.append("")

    lines.append(f"## Context\n")
    lines.append(plan.context)
    lines.append("")

    if plan.default_model:
        lines.append(f"**Default model:** {plan.default_model}\n")

    lines.append(f"## Tasks\n")

    for i, task in enumerate(plan.tasks, 1):
        lines.append(f"### {i}. {task.title} (`{task.id}`)\n")
        lines.append(f"**Goal:** {task.goal}\n")

        if task.depends_on:
            lines.append(f"**Depends on:** {', '.join(task.depends_on)}\n")

        if task.files:
            lines.append("**Files:**")
            for f in task.files:
                lines.append(f"- `{f}`")
            lines.append("")

        if task.constraints:
            lines.append("**Constraints:**")
            for c in task.constraints:
                lines.append(f"- {c}")
            lines.append("")

        if task.acceptance:
            lines.append("**Acceptance criteria:**")
            for a in task.acceptance:
                lines.append(f"- {a}")
            lines.append("")

        if task.model:
            lines.append(f"**Model:** {task.model}\n")

    return "\n".join(lines)


# --- Status ---


def format_status(record: WorkflowRecord) -> str:
    """Multi-line status summary (current phase, task list, usage totals)."""
    wf = record.workflow
    lines: list[str] = []

    label = workflow_label(wf.id, wf.name)
    lines.append(f"{label} — {wf.status.value}")
    lines.append("")

    # Task progress
    if record.implementation and record.plan:
        tasks = record.plan.tasks
        results = record.implementation.tasks
        total = len(tasks)
        done = sum(1 for t in tasks if results.get(t.id) and results[t.id].status == TaskStatus.DONE)
        failed = sum(1 for t in tasks if results.get(t.id) and results[t.id].status == TaskStatus.FAILED)
        skipped = sum(1 for t in tasks if results.get(t.id) and results[t.id].status == TaskStatus.SKIPPED)

        lines.append(f"Tasks: {done}/{total} done", )
        if failed:
            lines[-1] += f", {failed} failed"
        if skipped:
            lines[-1] += f", {skipped} skipped"
        lines.append("")
    elif record.plan:
        lines.append(f"Tasks: {len(record.plan.tasks)} planned")
        lines.append("")

    # Total cost
    total_cost = _compute_total_cost(record)
    if total_cost > 0:
        lines.append(f"Total cost: {fmt_cost(total_cost)}")

    return "\n".join(lines)


def _compute_total_cost(record: WorkflowRecord) -> float:
    """Sum up all usage costs in a record.

    NOTE: When record.py's get_total_usage() is implemented (Phase 2),
    this should delegate to get_total_usage(record).cost rather than
    reimplementing the traversal.
    """
    cost = 0.0
    if record.brainstorm:
        cost += record.brainstorm.usage.cost
    if record.plan:
        cost += record.plan.usage.cost
    if record.implementation:
        for tr in record.implementation.tasks.values():
            cost += tr.usage.cost
    for review in record.reviews:
        cost += review.usage.cost
    return cost


# --- Execution summary ---


def format_execution_summary(record: WorkflowRecord) -> str:
    """Final execution report with task results and usage table."""
    lines: list[str] = []

    wf = record.workflow
    lines.append(f"# Execution Summary — {wf.name}\n")

    if not record.plan or not record.implementation:
        lines.append("No execution data available.")
        return "\n".join(lines)

    impl = record.implementation
    tasks = record.plan.tasks

    # Duration
    if impl.started_at and impl.completed_at:
        # Just show timestamps; we don't parse ISO here
        lines.append(f"**Started:** {impl.started_at}")
        lines.append(f"**Completed:** {impl.completed_at}")
        lines.append("")

    # Per-task results
    lines.append("## Task Results\n")

    usage_rows: list[UsageRow] = []

    for task in tasks:
        result = impl.tasks.get(task.id)
        if result is None:
            icon = "○"
            lines.append(f"{icon} {task.id} {task.title}")
            continue

        icon = _STATUS_ICONS.get(result.status, "?")
        cost_str = f"  {fmt_cost(result.usage.cost)}" if result.usage.cost > 0 else ""
        lines.append(f"{icon} {task.id} {task.title}{cost_str}")

        if result.summary:
            lines.append(f"  {result.summary}")

        if result.error:
            lines.append(f"  Error: {result.error}")

        usage_rows.append(UsageRow(
            label=task.id,
            input=result.usage.input,
            output=result.usage.output,
            cache_read=result.usage.cache_read,
            cache_write=result.usage.cache_write,
            cost=result.usage.cost,
            turns=result.usage.turns,
            model=result.usage.model,
        ))

    lines.append("")

    # Usage table
    if usage_rows:
        lines.append("## Usage\n")
        lines.append(format_usage_table(usage_rows))
        lines.append("")

    # Total cost
    total_cost = sum(r.cost for r in usage_rows)
    lines.append(f"**Total cost:** {fmt_cost(total_cost)}")

    return "\n".join(lines)


# --- Model summary ---


def format_model_summary(
    tasks: list[Task],
    default_model: str | None = None,
    execute_model: str | None = None,
) -> str:
    """Pre-execution model resolution summary."""
    lines: list[str] = []
    lines.append("| Task | Model |")
    lines.append("|------|-------|")

    for task in tasks:
        # Resolution: task.model > execute_model > default_model > "(default)"
        model = task.model or execute_model or default_model or "(default)"
        lines.append(f"| {task.id} | {model} |")

    return "\n".join(lines)


# --- Record markdown ---


def render_record_markdown(record: WorkflowRecord) -> str:
    """Full human-readable markdown rendering of an entire workflow record."""
    lines: list[str] = []
    wf = record.workflow

    lines.append(f"# {wf.name}\n")
    lines.append(f"- **ID:** {wf.id}")
    lines.append(f"- **Status:** {wf.status.value}")
    lines.append(f"- **Created:** {wf.created_at}")
    lines.append(f"- **Project:** {wf.project}")
    lines.append(f"- **Branch:** {wf.source_branch}")
    if wf.worktree:
        lines.append(f"- **Worktree:** {wf.worktree}")
    lines.append("")

    # Brainstorm
    if record.brainstorm:
        bs = record.brainstorm
        lines.append("## Brainstorm\n")
        lines.append(f"**Motivation:** {bs.motivation}\n")
        lines.append(f"**Solution:** {bs.solution}\n")
        if bs.design_decisions:
            lines.append("### Design Decisions\n")
            for dd in bs.design_decisions:
                lines.append(f"- **{dd.decision}** — {dd.rationale}")
            lines.append("")
        lines.append(f"*Cost: {fmt_cost(bs.usage.cost)}*\n")

    # Plan
    if record.plan:
        pr = record.plan
        plan = Plan(
            goal=pr.goal,
            context=pr.context,
            tasks=pr.tasks,
            default_model=pr.default_model,
        )
        lines.append("## Plan\n")
        lines.append(render_plan_markdown(plan))

    # Implementation
    if record.implementation:
        impl = record.implementation
        lines.append("## Implementation\n")
        for task in (record.plan.tasks if record.plan else []):
            result = impl.tasks.get(task.id)
            if result is None:
                continue
            icon = _STATUS_ICONS.get(result.status, "?")
            lines.append(f"{icon} **{task.id}** — {task.title}")
            if result.summary:
                lines.append(f"  {result.summary}")
            lines.append("")

    # Reviews
    if record.reviews:
        lines.append("## Reviews\n")
        for i, review in enumerate(record.reviews, 1):
            lines.append(f"### Review {i}\n")
            lines.append(review.review_text)
            lines.append("")
            if review.findings_actionable:
                lines.append("*Actionable findings*\n")
            else:
                lines.append("*No actionable findings*\n")

    # Close
    if record.close:
        cl = record.close
        lines.append("## Close\n")
        lines.append(f"- **Merge result:** {cl.merge_result}")
        if cl.final_commit:
            lines.append(f"- **Final commit:** {cl.final_commit}")
        lines.append(f"- **Diff stat:**\n```\n{cl.diff_stat}\n```")
        lines.append("")

    return "\n".join(lines)


# --- History table ---


def format_history_table(records: list[WorkflowRecord], limit: int = 20) -> str:
    """Plain text table of recent workflows."""
    if not records:
        return "No workflows found."

    display = records[:limit]

    lines: list[str] = []
    lines.append("| Name | Status | Tasks | Cost | Created |")
    lines.append("|------|--------|-------|------|---------|")

    for rec in display:
        wf = rec.workflow
        name = wf.name
        status = wf.status.value

        # Task progress
        if rec.plan and rec.implementation:
            total = len(rec.plan.tasks)
            done = sum(
                1 for t in rec.plan.tasks
                if rec.implementation.tasks.get(t.id)
                and rec.implementation.tasks[t.id].status == TaskStatus.DONE
            )
            tasks_str = f"{done}/{total}"
        elif rec.plan:
            tasks_str = f"0/{len(rec.plan.tasks)}"
        else:
            tasks_str = "-"

        cost = _compute_total_cost(rec)
        cost_str = fmt_cost(cost) if cost > 0 else "-"

        created = wf.created_at

        lines.append(f"| {name} | {status} | {tasks_str} | {cost_str} | {created} |")

    return "\n".join(lines)
