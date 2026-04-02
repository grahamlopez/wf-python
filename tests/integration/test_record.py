"""Tests for wflib.record — create, load, save, atomic writes, phase transitions."""

import tempfile
import unittest
from pathlib import Path

from wflib.record import (
    clear_active_resource,
    create_record,
    get_plan,
    get_total_usage,
    list_records,
    load_record,
    record_brainstorm,
    record_close,
    record_event,
    record_implementation_complete,
    record_plan,
    record_task_complete,
    record_task_start,
    save_record,
)
from wflib.types import (
    BrainstormRecord,
    DesignDecision,
    ImplementationEventType,
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


def _base_record(status: WorkflowStatus = WorkflowStatus.INIT) -> WorkflowRecord:
    return WorkflowRecord(
        workflow=WorkflowMeta(
            id="a1b2",
            name="demo",
            created_at="2025-01-01T00:00:00Z",
            status=status,
            project="/tmp/demo",
            source_branch="main",
            source_commit="abc123",
            worktree=None,
            config=WorkflowConfig(),
        )
    )


class TestCreateRecord(unittest.TestCase):
    def test_creates_file(self):
        """create_record writes docs/workflows/<name>.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            record = create_record("demo", tmpdir, "main", "abc123")
            path = Path(tmpdir) / "docs" / "workflows" / "demo.json"
            self.assertTrue(path.is_file())
            self.assertEqual(record.workflow.name, "demo")

    def test_generates_workflow_id(self):
        """Created record has a non-empty workflow ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            record = create_record("demo", tmpdir, "main", "abc123")
            workflow_id = record.workflow.id
            self.assertEqual(len(workflow_id), 4)
            int(workflow_id, 16)

    def test_initial_status_is_init(self):
        """Created record has status 'init'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            record = create_record("demo", tmpdir, "main", "abc123")
            self.assertEqual(record.workflow.status, WorkflowStatus.INIT)

    def test_raises_on_duplicate_name(self):
        """Raises if a record with the same name already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            create_record("demo", tmpdir, "main", "abc123")
            with self.assertRaises(FileExistsError):
                create_record("demo", tmpdir, "main", "abc123")

    def test_includes_config_snapshot(self):
        """Created record includes the provided WorkflowConfig."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = WorkflowConfig()
            config.agent.profile = "mock"
            record = create_record("demo", tmpdir, "main", "abc123", config=config)
            self.assertEqual(record.workflow.config, config)


class TestLoadSaveRecord(unittest.TestCase):
    def test_round_trip(self):
        """save_record then load_record produces equivalent record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            record = create_record("demo", tmpdir, "main", "abc123")
            record.workflow.status = WorkflowStatus.PLANNING
            save_record(record, tmpdir)
            loaded = load_record("demo", tmpdir)
            self.assertEqual(record, loaded)

    def test_atomic_write(self):
        """save_record uses atomic write (tmp + rename)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            record = create_record("demo", tmpdir, "main", "abc123")
            save_record(record, tmpdir)
            workflows_dir = Path(tmpdir) / "docs" / "workflows"
            files = sorted(p.name for p in workflows_dir.iterdir())
            self.assertEqual(files, ["demo.json"])

    def test_load_missing_raises(self):
        """load_record raises FileNotFoundError for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                load_record("missing", tmpdir)

    def test_load_malformed_raises(self):
        """load_record raises ValueError for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflows_dir = Path(tmpdir) / "docs" / "workflows"
            workflows_dir.mkdir(parents=True)
            bad_path = workflows_dir / "bad.json"
            bad_path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_record("bad", tmpdir)


class TestListRecords(unittest.TestCase):
    def test_lists_valid_records_skips_malformed(self):
        """list_records returns valid records and warns on malformed files."""
        import io
        import contextlib
        import json as _json

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 2 valid records
            create_record("alpha", tmpdir, "main", "aaa111")
            create_record("beta", tmpdir, "main", "bbb222")

            # Create 1 malformed .json file
            workflows_dir = Path(tmpdir) / "docs" / "workflows"
            bad_path = workflows_dir / "corrupt.json"
            bad_path.write_text("{not valid json", encoding="utf-8")

            # Capture stderr
            stderr_buf = io.StringIO()
            with contextlib.redirect_stderr(stderr_buf):
                records = list_records(tmpdir)

            # Should return exactly 2 valid records
            self.assertEqual(len(records), 2)
            names = sorted(r.workflow.name for r in records)
            self.assertEqual(names, ["alpha", "beta"])

            # Should have warned about the malformed file
            stderr_output = stderr_buf.getvalue()
            self.assertIn("Warning", stderr_output)
            self.assertIn("corrupt.json", stderr_output)


class TestPhaseTransitions(unittest.TestCase):
    def test_record_brainstorm_sets_planning(self):
        """record_brainstorm sets status to 'planning'."""
        record = _base_record()
        usage = Usage(input=1, output=2, cache_read=0, cache_write=0, cost=0.1, turns=1)
        decisions = [DesignDecision(decision="Use A", rationale="Simpler")]

        record_brainstorm(record, "Motivation", "Solution", decisions, usage)

        self.assertEqual(record.workflow.status, WorkflowStatus.PLANNING)
        self.assertIsNotNone(record.brainstorm)
        self.assertEqual(record.brainstorm.motivation, "Motivation")
        self.assertEqual(record.brainstorm.solution, "Solution")
        self.assertEqual(record.brainstorm.design_decisions, decisions)
        self.assertEqual(record.brainstorm.usage, usage)
        self.assertTrue(record.brainstorm.recorded_at)

    def test_record_plan_sets_implementing(self):
        """record_plan sets status to 'implementing'."""
        record = _base_record(status=WorkflowStatus.PLANNING)
        task = Task(
            id="task-1",
            title="First task",
            goal="Do work",
            files=["file.py"],
            constraints=["Keep it simple"],
            acceptance=["Tests pass"],
            depends_on=[],
        )
        plan = Plan(goal="Goal", context="Context", tasks=[task], default_model="gpt-4")
        usage = Usage(input=3, output=4, cache_read=0, cache_write=0, cost=0.2, turns=1)

        record_plan(record, plan, usage)

        self.assertEqual(record.workflow.status, WorkflowStatus.IMPLEMENTING)
        self.assertIsNotNone(record.plan)
        self.assertEqual(record.plan.goal, plan.goal)
        self.assertEqual(record.plan.context, plan.context)
        self.assertEqual(record.plan.tasks, plan.tasks)
        self.assertEqual(record.plan.default_model, plan.default_model)
        self.assertEqual(record.plan.usage, usage)
        self.assertIsNotNone(record.implementation)
        self.assertIn("task-1", record.implementation.tasks)
        self.assertEqual(record.implementation.tasks["task-1"].status, TaskStatus.PENDING)

    def test_record_implementation_complete_sets_reviewing(self):
        """record_implementation_complete sets status to 'reviewing'."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord(started_at="2025-01-01T00:00:00Z")

        record_implementation_complete(record)

        self.assertEqual(record.workflow.status, WorkflowStatus.REVIEWING)
        self.assertIsNotNone(record.implementation.completed_at)

    def test_record_close_sets_done(self):
        """record_close sets status to 'done'."""
        record = _base_record(status=WorkflowStatus.REVIEWING)

        record_close(record, "clean", "def456", "1 file changed")

        self.assertEqual(record.workflow.status, WorkflowStatus.DONE)
        self.assertIsNotNone(record.close)
        self.assertEqual(record.close.merge_result, "clean")
        self.assertEqual(record.close.final_commit, "def456")
        self.assertEqual(record.close.diff_stat, "1 file changed")
        self.assertTrue(record.close.recorded_at)


class TestTaskTracking(unittest.TestCase):
    def test_record_task_start(self):
        """record_task_start marks task as running with timestamp."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord(
            tasks={"task-1": TaskResult(status=TaskStatus.PENDING)}
        )

        record_task_start(record, "task-1")

        result = record.implementation.tasks["task-1"]
        self.assertEqual(result.status, TaskStatus.RUNNING)
        self.assertIsNotNone(result.started_at)

    def test_record_task_start_adds_active_resource(self):
        """record_task_start adds worktree to activeResources."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord(
            tasks={"task-1": TaskResult(status=TaskStatus.PENDING)}
        )

        record_task_start(record, "task-1", worktree_path="/tmp/wt-task-1")

        self.assertEqual(record.implementation.active_resources["task-1"], "/tmp/wt-task-1")
        self.assertEqual(record.implementation.tasks["task-1"].worktree_path, "/tmp/wt-task-1")

    def test_record_task_complete(self):
        """record_task_complete stores TaskResult."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord(
            tasks={"task-1": TaskResult(status=TaskStatus.PENDING)}
        )
        result = TaskResult(status=TaskStatus.DONE, summary="Done")

        record_task_complete(record, "task-1", result)

        self.assertEqual(record.implementation.tasks["task-1"], result)

    def test_clear_active_resource(self):
        """clear_active_resource removes worktree from activeResources."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord(
            active_resources={"task-1": "/tmp/wt1", "task-2": "/tmp/wt2"}
        )

        clear_active_resource(record, "task-1")

        self.assertNotIn("task-1", record.implementation.active_resources)
        self.assertIn("task-2", record.implementation.active_resources)


class TestEvents(unittest.TestCase):
    def test_record_event_appends(self):
        """record_event appends to implementation.events."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord()

        record_event(record, ImplementationEventType.MERGE_START, task="task-1", detail="Start merge")

        self.assertEqual(len(record.implementation.events), 1)
        event = record.implementation.events[0]
        self.assertEqual(event.event, ImplementationEventType.MERGE_START)
        self.assertEqual(event.task, "task-1")
        self.assertEqual(event.detail, "Start merge")

    def test_event_has_timestamp(self):
        """Appended events have a timestamp."""
        record = _base_record(status=WorkflowStatus.IMPLEMENTING)
        record.implementation = ImplementationRecord()

        record_event(record, ImplementationEventType.MERGE_COMPLETE)

        event = record.implementation.events[0]
        self.assertTrue(event.t)
        self.assertIn("T", event.t)


class TestQueryHelpers(unittest.TestCase):
    def test_get_plan_returns_plan(self):
        """get_plan extracts Plan from record with a plan phase."""
        task = Task(
            id="task-1",
            title="First task",
            goal="Do work",
            files=["file.py"],
            constraints=["Keep it simple"],
            acceptance=["Tests pass"],
            depends_on=[],
        )
        plan_record = PlanRecord(
            recorded_at="2025-01-01T00:00:00Z",
            goal="Build feature",
            context="Context",
            default_model="gpt-4",
            tasks=[task],
            usage=Usage(input=1, output=2, cache_read=3, cache_write=4, cost=0.1, turns=1),
        )
        record = WorkflowRecord(
            workflow=WorkflowMeta(
                id="a1b2",
                name="demo",
                created_at="2025-01-01T00:00:00Z",
                status=WorkflowStatus.PLANNING,
                project="/tmp/demo",
                source_branch="main",
                source_commit="abc123",
                worktree=None,
                config=WorkflowConfig(),
            ),
            plan=plan_record,
        )
        plan = get_plan(record)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.goal, plan_record.goal)
        self.assertEqual(plan.context, plan_record.context)
        self.assertEqual(plan.tasks, plan_record.tasks)
        self.assertEqual(plan.default_model, plan_record.default_model)

    def test_get_plan_returns_none(self):
        """get_plan returns None when no plan recorded."""
        record = WorkflowRecord(
            workflow=WorkflowMeta(
                id="a1b2",
                name="demo",
                created_at="2025-01-01T00:00:00Z",
                status=WorkflowStatus.INIT,
                project="/tmp/demo",
                source_branch="main",
                source_commit="abc123",
                worktree=None,
                config=WorkflowConfig(),
            )
        )
        self.assertIsNone(get_plan(record))

    def test_get_total_usage_aggregates(self):
        """get_total_usage sums across all phases."""
        brainstorm_usage = Usage(input=1, output=2, cache_read=3, cache_write=4, cost=0.5, turns=1)
        plan_usage = Usage(input=10, output=20, cache_read=30, cache_write=40, cost=1.5, turns=2)
        task_usage_1 = Usage(input=100, output=200, cache_read=0, cache_write=0, cost=2.0, turns=3)
        task_usage_2 = Usage(input=300, output=400, cache_read=5, cache_write=6, cost=3.0, turns=4)
        review_usage = Usage(input=7, output=8, cache_read=9, cache_write=10, cost=0.2, turns=1)

        record = WorkflowRecord(
            workflow=WorkflowMeta(
                id="a1b2",
                name="demo",
                created_at="2025-01-01T00:00:00Z",
                status=WorkflowStatus.REVIEWING,
                project="/tmp/demo",
                source_branch="main",
                source_commit="abc123",
                worktree=None,
                config=WorkflowConfig(),
            ),
            brainstorm=BrainstormRecord(
                recorded_at="2025-01-01T00:00:00Z",
                motivation="Motivation",
                solution="Solution",
                design_decisions=[],
                usage=brainstorm_usage,
            ),
            plan=PlanRecord(
                recorded_at="2025-01-01T00:10:00Z",
                goal="Goal",
                context="Context",
                default_model=None,
                tasks=[],
                usage=plan_usage,
            ),
            implementation=ImplementationRecord(
                tasks={
                    "task-1": TaskResult(status=TaskStatus.DONE, usage=task_usage_1),
                    "task-2": TaskResult(status=TaskStatus.DONE, usage=task_usage_2),
                }
            ),
            reviews=[
                ReviewRecord(
                    recorded_at="2025-01-01T01:00:00Z",
                    base_commit="abc123",
                    review_text="Looks good",
                    findings_actionable=False,
                    usage=review_usage,
                )
            ],
        )

        total = get_total_usage(record)
        expected = Usage(
            input=418,
            output=630,
            cache_read=47,
            cache_write=60,
            cost=7.2,
            turns=11,
        )
        self.assertEqual(total, expected)


if __name__ == "__main__":
    unittest.main()
