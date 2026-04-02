"""Tests for wflib.render — markdown rendering, usage tables, status formatting."""

import unittest

from wflib.render import (
    UsageRow,
    fmt_cost,
    fmt_duration,
    fmt_num,
    format_execution_summary,
    format_history_table,
    format_model_summary,
    format_status,
    format_usage_table,
    render_plan_markdown,
    render_record_markdown,
    slugify,
    workflow_label,
)
from wflib.types import (
    BrainstormRecord,
    CloseRecord,
    DesignDecision,
    ImplementationRecord,
    Plan,
    PlanRecord,
    ReviewRecord,
    Task,
    TaskResult,
    TaskStatus,
    Usage,
    WorkflowConfig,
    WorkflowMeta,
    WorkflowRecord,
    WorkflowStatus,
)


def _make_task(id: str = "task-1", title: str = "First task", **kwargs) -> Task:
    defaults = dict(
        goal="Do something",
        files=["file.py"],
        constraints=["Keep it simple"],
        acceptance=["Tests pass"],
        depends_on=[],
        skills=None,
        model=None,
    )
    defaults.update(kwargs)
    return Task(id=id, title=title, **defaults)


def _make_plan(**kwargs) -> Plan:
    defaults = dict(
        goal="Implement the feature",
        context="We are building a CLI tool.",
        tasks=[_make_task()],
        default_model=None,
    )
    defaults.update(kwargs)
    return Plan(**defaults)


def _make_usage(**kwargs) -> Usage:
    defaults = dict(
        model=None, input=100, output=50,
        cache_read=10, cache_write=5,
        cost=0.045, turns=3,
    )
    defaults.update(kwargs)
    return Usage(**defaults)


def _make_task_result(status=TaskStatus.DONE, **kwargs) -> TaskResult:
    defaults = dict(
        started_at="2025-01-01T00:00:00Z",
        completed_at="2025-01-01T00:05:00Z",
        exit_code=0,
        summary="Completed successfully",
        usage=_make_usage(),
    )
    defaults.update(kwargs)
    return TaskResult(status=status, **defaults)


def _make_workflow_meta(**kwargs) -> WorkflowMeta:
    defaults = dict(
        id="a1b2",
        name="auth-refactor",
        created_at="2025-01-01T00:00:00Z",
        status=WorkflowStatus.INIT,
        project="/tmp/project",
        source_branch="main",
        source_commit="abc123",
        worktree=None,
    )
    defaults.update(kwargs)
    return WorkflowMeta(**defaults)


def _make_record(**kwargs) -> WorkflowRecord:
    defaults = dict(workflow=_make_workflow_meta())
    defaults.update(kwargs)
    return WorkflowRecord(**defaults)


class TestFormatUsageTable(unittest.TestCase):
    def test_single_row(self):
        """Renders a single-row usage table correctly."""
        rows = [UsageRow(label="brainstorm", input=1000, output=500,
                         cache_read=200, cache_write=100, cost=0.045, turns=3)]
        result = format_usage_table(rows)
        # Should have header, separator, data row, total row
        lines = result.strip().split("\n")
        self.assertEqual(len(lines), 4)
        # Header
        self.assertIn("Label", lines[0])
        self.assertIn("Input", lines[0])
        self.assertIn("Cost", lines[0])
        self.assertIn("Turns", lines[0])
        # Data row
        self.assertIn("brainstorm", lines[2])
        self.assertIn("1,000", lines[2])
        self.assertIn("500", lines[2])
        self.assertIn("$0.045", lines[2])
        self.assertIn("3", lines[2])
        # Total row
        self.assertIn("**Total**", lines[3])
        self.assertIn("1,000", lines[3])
        self.assertIn("$0.045", lines[3])

    def test_multiple_rows_with_total(self):
        """Renders multiple rows with a total row."""
        rows = [
            UsageRow(label="task-1", input=1000, output=500,
                     cache_read=100, cache_write=50, cost=0.045, turns=3),
            UsageRow(label="task-2", input=2000, output=800,
                     cache_read=300, cache_write=150, cost=0.082, turns=5),
        ]
        result = format_usage_table(rows)
        lines = result.strip().split("\n")
        self.assertEqual(len(lines), 5)  # header + sep + 2 data + total
        # Check totals in last row
        total_line = lines[-1]
        self.assertIn("**Total**", total_line)
        self.assertIn("3,000", total_line)   # 1000+2000
        self.assertIn("1,300", total_line)    # 500+800
        self.assertIn("$0.127", total_line)   # 0.045+0.082
        self.assertIn("8", total_line)        # 3+5

    def test_empty_rows(self):
        """Handles empty row list gracefully."""
        result = format_usage_table([])
        self.assertEqual(result, "")


class TestRenderPlanMarkdown(unittest.TestCase):
    def test_includes_goal_and_context(self):
        """Rendered plan includes goal and context."""
        plan = _make_plan(goal="Build auth module", context="This is a web app.")
        result = render_plan_markdown(plan)
        self.assertIn("# Goal", result)
        self.assertIn("Build auth module", result)
        self.assertIn("## Context", result)
        self.assertIn("This is a web app.", result)

    def test_includes_task_details(self):
        """Rendered plan includes task titles, goals, constraints."""
        task = _make_task(
            id="task-1",
            title="Extract module",
            goal="Separate auth logic",
            files=["auth.py", "tokens.py"],
            constraints=["No breaking changes"],
            acceptance=["All tests pass", "Module loads correctly"],
        )
        plan = _make_plan(tasks=[task])
        result = render_plan_markdown(plan)
        self.assertIn("Extract module", result)
        self.assertIn("`task-1`", result)
        self.assertIn("Separate auth logic", result)
        self.assertIn("`auth.py`", result)
        self.assertIn("`tokens.py`", result)
        self.assertIn("No breaking changes", result)
        self.assertIn("All tests pass", result)
        self.assertIn("Module loads correctly", result)

    def test_shows_dependency_graph(self):
        """Rendered plan shows task dependencies."""
        task1 = _make_task(id="task-1", title="First")
        task2 = _make_task(id="task-2", title="Second", depends_on=["task-1"])
        plan = _make_plan(tasks=[task1, task2])
        result = render_plan_markdown(plan)
        self.assertIn("Depends on:", result)
        self.assertIn("task-1", result)

    def test_shows_default_model(self):
        """Rendered plan shows default model when set."""
        plan = _make_plan(default_model="claude-sonnet")
        result = render_plan_markdown(plan)
        self.assertIn("Default model:", result)
        self.assertIn("claude-sonnet", result)

    def test_task_with_model_override(self):
        """Rendered plan shows per-task model override."""
        task = _make_task(model="claude-opus")
        plan = _make_plan(tasks=[task])
        result = render_plan_markdown(plan)
        self.assertIn("Model:", result)
        self.assertIn("claude-opus", result)


class TestFormatStatus(unittest.TestCase):
    def test_init_status(self):
        """Status display for workflow in init state."""
        record = _make_record()
        result = format_status(record)
        self.assertIn("auth-refactor [a1b2]", result)
        self.assertIn("init", result)

    def test_implementing_with_progress(self):
        """Status display shows task progress (e.g., 3/5 done)."""
        tasks = [_make_task(id=f"task-{i}", title=f"Task {i}") for i in range(1, 6)]
        plan = PlanRecord(
            recorded_at="2025-01-01T00:00:00Z",
            goal="Test",
            context="Test",
            default_model=None,
            tasks=tasks,
            usage=_make_usage(),
        )
        impl = ImplementationRecord(
            started_at="2025-01-01T00:00:00Z",
            tasks={
                "task-1": _make_task_result(TaskStatus.DONE),
                "task-2": _make_task_result(TaskStatus.DONE),
                "task-3": _make_task_result(TaskStatus.DONE),
                "task-4": _make_task_result(TaskStatus.FAILED, error="Test failure"),
                "task-5": _make_task_result(TaskStatus.SKIPPED),
            },
        )
        record = _make_record(
            workflow=_make_workflow_meta(status=WorkflowStatus.IMPLEMENTING),
            plan=plan,
            implementation=impl,
        )
        result = format_status(record)
        self.assertIn("3/5 done", result)
        self.assertIn("1 failed", result)
        self.assertIn("1 skipped", result)

    def test_done_status_with_cost(self):
        """Status display for completed workflow includes total cost."""
        plan = PlanRecord(
            recorded_at="2025-01-01T00:00:00Z",
            goal="Test",
            context="Test",
            default_model=None,
            tasks=[_make_task()],
            usage=_make_usage(cost=0.055),
        )
        impl = ImplementationRecord(
            started_at="2025-01-01T00:00:00Z",
            tasks={
                "task-1": _make_task_result(TaskStatus.DONE, usage=_make_usage(cost=0.045)),
            },
        )
        brainstorm = BrainstormRecord(
            recorded_at="2025-01-01T00:00:00Z",
            motivation="Test",
            solution="Test",
            design_decisions=[],
            usage=_make_usage(cost=0.082),
        )
        record = _make_record(
            workflow=_make_workflow_meta(status=WorkflowStatus.DONE),
            brainstorm=brainstorm,
            plan=plan,
            implementation=impl,
        )
        result = format_status(record)
        self.assertIn("done", result)
        # Total cost = brainstorm(0.082) + plan(0.055) + task(0.045) = 0.182
        self.assertIn("$0.182", result)


class TestHelpers(unittest.TestCase):
    def test_fmt_num(self):
        """fmt_num formats large numbers with separators."""
        self.assertEqual(fmt_num(0), "0")
        self.assertEqual(fmt_num(999), "999")
        self.assertEqual(fmt_num(1000), "1,000")
        self.assertEqual(fmt_num(23000), "23,000")
        self.assertEqual(fmt_num(1000000), "1,000,000")

    def test_fmt_cost(self):
        """fmt_cost formats cost as dollar amount."""
        # Under $1 → 3 decimal places
        self.assertEqual(fmt_cost(0.0), "$0.000")
        self.assertEqual(fmt_cost(0.045), "$0.045")
        self.assertEqual(fmt_cost(0.1), "$0.100")
        self.assertEqual(fmt_cost(0.999), "$0.999")
        # $1 and above → 2 decimal places
        self.assertEqual(fmt_cost(1.0), "$1.00")
        self.assertEqual(fmt_cost(1.50), "$1.50")
        self.assertEqual(fmt_cost(10.5), "$10.50")
        self.assertEqual(fmt_cost(100.0), "$100.00")

    def test_fmt_duration(self):
        """fmt_duration formats seconds as human-readable duration."""
        self.assertEqual(fmt_duration(0), "<1m")
        self.assertEqual(fmt_duration(30), "<1m")
        self.assertEqual(fmt_duration(59), "<1m")
        self.assertEqual(fmt_duration(60), "1m 0s")
        self.assertEqual(fmt_duration(90), "1m 30s")
        self.assertEqual(fmt_duration(3599), "59m 59s")
        self.assertEqual(fmt_duration(3600), "1h 0m")
        self.assertEqual(fmt_duration(3660), "1h 1m")
        self.assertEqual(fmt_duration(7200), "2h 0m")

    def test_slugify(self):
        """slugify converts text to URL-safe slug."""
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("My Project!"), "my-project")
        self.assertEqual(slugify("  leading and trailing  "), "leading-and-trailing")
        self.assertEqual(slugify("auth--refactor"), "auth-refactor")
        self.assertEqual(slugify("CamelCase Test"), "camelcase-test")
        self.assertEqual(slugify("special @#$ chars"), "special-chars")
        self.assertEqual(slugify("already-a-slug"), "already-a-slug")

    def test_workflow_label(self):
        """workflow_label combines id and name."""
        self.assertEqual(workflow_label("a1b2", "auth-refactor"), "auth-refactor [a1b2]")
        self.assertEqual(workflow_label("xyz9", "my-project"), "my-project [xyz9]")


class TestFormatExecutionSummary(unittest.TestCase):
    def test_basic_summary(self):
        """Execution summary shows per-task results with status icons."""
        tasks = [
            _make_task(id="task-1", title="Extract module"),
            _make_task(id="task-2", title="Write tests"),
            _make_task(id="task-3", title="Documentation"),
        ]
        plan = PlanRecord(
            recorded_at="2025-01-01T00:00:00Z",
            goal="Test",
            context="Test context",
            default_model=None,
            tasks=tasks,
            usage=_make_usage(),
        )
        impl = ImplementationRecord(
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:15:00Z",
            tasks={
                "task-1": _make_task_result(TaskStatus.DONE, usage=_make_usage(cost=0.045)),
                "task-2": _make_task_result(TaskStatus.FAILED, error="Test failure",
                                            usage=_make_usage(cost=0.032)),
                "task-3": _make_task_result(TaskStatus.SKIPPED, usage=_make_usage(cost=0.0)),
            },
        )
        record = _make_record(
            workflow=_make_workflow_meta(status=WorkflowStatus.DONE),
            plan=plan,
            implementation=impl,
        )
        result = format_execution_summary(record)

        # Check icons
        self.assertIn("✓ task-1 Extract module", result)
        self.assertIn("✗ task-2 Write tests", result)
        self.assertIn("⊘ task-3 Documentation", result)

        # Check cost
        self.assertIn("$0.045", result)
        self.assertIn("$0.032", result)

        # Check usage table
        self.assertIn("Label", result)
        self.assertIn("Total", result)

        # Check total cost
        self.assertIn("Total cost", result)

    def test_no_implementation(self):
        """Execution summary handles missing implementation data."""
        record = _make_record()
        result = format_execution_summary(record)
        self.assertIn("No execution data", result)


class TestFormatModelSummary(unittest.TestCase):
    def test_with_defaults(self):
        """Model summary uses default model when no overrides."""
        tasks = [_make_task(id="task-1"), _make_task(id="task-2")]
        result = format_model_summary(tasks, default_model="claude-sonnet")
        self.assertIn("task-1", result)
        self.assertIn("task-2", result)
        self.assertIn("claude-sonnet", result)

    def test_with_task_override(self):
        """Model summary shows per-task model override."""
        tasks = [
            _make_task(id="task-1"),
            _make_task(id="task-2", model="claude-opus"),
        ]
        result = format_model_summary(tasks, default_model="claude-sonnet")
        # task-1 should use default
        lines = result.split("\n")
        task1_line = [l for l in lines if "task-1" in l][0]
        task2_line = [l for l in lines if "task-2" in l][0]
        self.assertIn("claude-sonnet", task1_line)
        self.assertIn("claude-opus", task2_line)

    def test_execute_model_override(self):
        """Model summary uses execute_model when set."""
        tasks = [_make_task(id="task-1")]
        result = format_model_summary(tasks, default_model="claude-sonnet",
                                       execute_model="claude-haiku")
        self.assertIn("claude-haiku", result)

    def test_no_model(self):
        """Model summary shows (default) when no model specified."""
        tasks = [_make_task(id="task-1")]
        result = format_model_summary(tasks)
        self.assertIn("(default)", result)


class TestRenderRecordMarkdown(unittest.TestCase):
    def test_minimal_record(self):
        """Renders a minimal record with just workflow metadata."""
        record = _make_record()
        result = render_record_markdown(record)
        self.assertIn("# auth-refactor", result)
        self.assertIn("a1b2", result)
        self.assertIn("init", result)

    def test_with_brainstorm(self):
        """Renders brainstorm section."""
        brainstorm = BrainstormRecord(
            recorded_at="2025-01-01T00:00:00Z",
            motivation="Need better auth",
            solution="Split into modules",
            design_decisions=[
                DesignDecision(decision="Use JWT", rationale="Industry standard"),
            ],
            usage=_make_usage(cost=0.082),
        )
        record = _make_record(brainstorm=brainstorm)
        result = render_record_markdown(record)
        self.assertIn("## Brainstorm", result)
        self.assertIn("Need better auth", result)
        self.assertIn("Split into modules", result)
        self.assertIn("Use JWT", result)
        self.assertIn("Industry standard", result)
        self.assertIn("$0.082", result)

    def test_with_plan(self):
        """Renders plan section."""
        plan = PlanRecord(
            recorded_at="2025-01-01T00:00:00Z",
            goal="Build auth",
            context="Web app project",
            default_model=None,
            tasks=[_make_task(id="task-1", title="Extract module")],
            usage=_make_usage(),
        )
        record = _make_record(plan=plan)
        result = render_record_markdown(record)
        self.assertIn("## Plan", result)
        self.assertIn("Build auth", result)
        self.assertIn("Extract module", result)

    def test_with_close(self):
        """Renders close section."""
        close = CloseRecord(
            recorded_at="2025-01-01T00:00:00Z",
            merge_result="clean",
            final_commit="abc123",
            diff_stat="3 files changed, 100 insertions(+), 20 deletions(-)",
        )
        record = _make_record(close=close)
        result = render_record_markdown(record)
        self.assertIn("## Close", result)
        self.assertIn("clean", result)
        self.assertIn("abc123", result)
        self.assertIn("3 files changed", result)

    def test_with_reviews(self):
        """Renders review section."""
        review = ReviewRecord(
            recorded_at="2025-01-01T00:00:00Z",
            base_commit="abc123",
            review_text="Code looks good overall.",
            findings_actionable=False,
            usage=_make_usage(),
        )
        record = _make_record(reviews=[review])
        result = render_record_markdown(record)
        self.assertIn("## Reviews", result)
        self.assertIn("Code looks good overall.", result)
        self.assertIn("No actionable findings", result)


class TestFormatHistoryTable(unittest.TestCase):
    def test_empty(self):
        """Handles empty list."""
        result = format_history_table([])
        self.assertIn("No workflows found", result)

    def test_single_record(self):
        """Renders a single record in history table."""
        record = _make_record()
        result = format_history_table([record])
        self.assertIn("Name", result)
        self.assertIn("Status", result)
        self.assertIn("auth-refactor", result)
        self.assertIn("init", result)

    def test_limit(self):
        """Respects limit parameter."""
        records = [
            _make_record(workflow=_make_workflow_meta(id=f"w{i}", name=f"wf-{i}"))
            for i in range(10)
        ]
        result = format_history_table(records, limit=3)
        # Should only have 3 data rows (+ header + separator)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        self.assertEqual(len(lines), 5)  # header + sep + 3 data rows


if __name__ == "__main__":
    unittest.main()
