"""All text rendering - markdown, usage tables, status formatting."""

from __future__ import annotations

from dataclasses import dataclass

from wflib.types import Plan, Task, WorkflowRecord


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


def render_record_markdown(record: WorkflowRecord) -> str:
    """Full human-readable markdown rendering of an entire workflow record."""
    raise NotImplementedError("render_record_markdown: not yet implemented")


def render_plan_markdown(plan: Plan) -> str:
    """Render just the plan portion as markdown."""
    raise NotImplementedError("render_plan_markdown: not yet implemented")


def format_usage_table(rows: list[UsageRow]) -> str:
    """Markdown table with per-phase and total token usage."""
    raise NotImplementedError("format_usage_table: not yet implemented")


def format_history_table(records: list[WorkflowRecord], limit: int = 20) -> str:
    """Plain text table of recent workflows."""
    raise NotImplementedError("format_history_table: not yet implemented")


def format_status(record: WorkflowRecord) -> str:
    """Multi-line status summary (current phase, task list, usage totals)."""
    raise NotImplementedError("format_status: not yet implemented")


def format_execution_summary(record: WorkflowRecord) -> str:
    """Final execution report with task results and usage table."""
    raise NotImplementedError("format_execution_summary: not yet implemented")


def format_model_summary(
    tasks: list[Task],
    default_model: str | None = None,
    execute_model: str | None = None,
) -> str:
    """Pre-execution model resolution summary."""
    raise NotImplementedError("format_model_summary: not yet implemented")


def fmt_num(n: int) -> str:
    """Format a number with comma separators."""
    raise NotImplementedError("fmt_num: not yet implemented")


def fmt_cost(n: float) -> str:
    """Format a cost value as dollar amount."""
    raise NotImplementedError("fmt_cost: not yet implemented")


def fmt_duration(seconds: int) -> str:
    """Format a duration in human-readable form."""
    raise NotImplementedError("fmt_duration: not yet implemented")


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    raise NotImplementedError("slugify: not yet implemented")


def workflow_label(workflow_id: str, name: str) -> str:
    """Create a display label for a workflow."""
    raise NotImplementedError("workflow_label: not yet implemented")
