"""Tests for wflib.types — dataclass construction, serialization, tool call extraction."""

import json
import unittest

from wflib.types import (
    AgentConfig,
    AutomationConfig,
    AutomationLevel,
    BrainstormRecord,
    CloseRecord,
    CURRENT_SCHEMA_VERSION,
    DesignDecision,
    ExecuteConfig,
    ImplementationEvent,
    ImplementationEventType,
    ImplementationRecord,
    ModelConfig,
    ModelsConfig,
    Plan,
    PlanRecord,
    ReportResult,
    ReviewRecord,
    Task,
    TaskResult,
    TaskStatus,
    UIConfig,
    Usage,
    WorkflowConfig,
    WorkflowMeta,
    WorkflowRecord,
    WorkflowStatus,
    _dataclass_to_dict,
    _dict_to_dataclass,
    extract_tool_call,
    plan_from_json,
    plan_to_json,
    record_from_json,
    record_to_json,
    to_camel_case,
    to_snake_case,
    validate_schema,
)


class TestEnums(unittest.TestCase):
    def test_task_status_values(self):
        """TaskStatus enum has correct string values."""
        self.assertEqual(TaskStatus.PENDING.value, "pending")
        self.assertEqual(TaskStatus.RUNNING.value, "running")
        self.assertEqual(TaskStatus.DONE.value, "done")
        self.assertEqual(TaskStatus.FAILED.value, "failed")
        self.assertEqual(TaskStatus.SKIPPED.value, "skipped")

    def test_workflow_status_values(self):
        """WorkflowStatus enum has correct string values."""
        self.assertEqual(WorkflowStatus.INIT.value, "init")
        self.assertEqual(WorkflowStatus.PLANNING.value, "planning")
        self.assertEqual(WorkflowStatus.IMPLEMENTING.value, "implementing")
        self.assertEqual(WorkflowStatus.REVIEWING.value, "reviewing")
        self.assertEqual(WorkflowStatus.CLOSING.value, "closing")
        self.assertEqual(WorkflowStatus.DONE.value, "done")
        self.assertEqual(WorkflowStatus.FAILED.value, "failed")

    def test_automation_level_values(self):
        """AutomationLevel enum has correct string values."""
        self.assertEqual(AutomationLevel.INTERACTIVE.value, "interactive")
        self.assertEqual(AutomationLevel.SUPERVISED.value, "supervised")
        self.assertEqual(AutomationLevel.AUTOMATIC.value, "automatic")


class TestDataclassConstruction(unittest.TestCase):
    def test_plan_construction(self):
        """Plan can be constructed with required fields."""
        task = Task(
            id="task-1", title="Test", goal="Do something",
            files=["a.py"], constraints=["none"], acceptance=["pass"],
            depends_on=[]
        )
        plan = Plan(goal="goal", context="ctx", tasks=[task])
        self.assertEqual(plan.goal, "goal")
        self.assertEqual(plan.context, "ctx")
        self.assertEqual(len(plan.tasks), 1)
        self.assertIsNone(plan.default_model)

    def test_task_construction_with_defaults(self):
        """Task optional fields default correctly (skills=None, model=None)."""
        task = Task(
            id="t", title="t", goal="g",
            files=[], constraints=[], acceptance=[], depends_on=[]
        )
        self.assertIsNone(task.skills)
        self.assertIsNone(task.model)

    def test_usage_defaults_to_zeros(self):
        """Usage() constructs with all zeros."""
        u = Usage()
        self.assertIsNone(u.model)
        self.assertEqual(u.input, 0)
        self.assertEqual(u.output, 0)
        self.assertEqual(u.cache_read, 0)
        self.assertEqual(u.cache_write, 0)
        self.assertEqual(u.cost, 0.0)
        self.assertEqual(u.turns, 0)

    def test_workflow_config_defaults(self):
        """WorkflowConfig() constructs with all baked-in defaults."""
        cfg = WorkflowConfig()
        # ModelConfig defaults all None
        self.assertIsNone(cfg.model.brainstorm)
        self.assertIsNone(cfg.model.plan)
        self.assertIsNone(cfg.model.implement)
        # AutomationConfig defaults
        self.assertEqual(cfg.automation.brainstorm, AutomationLevel.INTERACTIVE)
        self.assertEqual(cfg.automation.implement, AutomationLevel.SUPERVISED)
        self.assertEqual(cfg.automation.review, AutomationLevel.AUTOMATIC)
        # ExecuteConfig defaults
        self.assertEqual(cfg.execute.concurrency, 4)
        self.assertTrue(cfg.execute.worktrees)
        self.assertTrue(cfg.execute.auto_review)
        # UIConfig defaults
        self.assertEqual(cfg.ui.auto_close, 30)
        self.assertTrue(cfg.ui.tmux)
        # AgentConfig defaults
        self.assertEqual(cfg.agent.profile, "pi")
        self.assertIsNone(cfg.agent.cmd)
        # ModelsConfig defaults
        self.assertEqual(cfg.models.aliases, {})
        self.assertEqual(cfg.models.profiles, {})

    def test_task_result_defaults(self):
        """TaskResult has correct defaults for optional fields."""
        tr = TaskResult(status=TaskStatus.PENDING)
        self.assertIsNone(tr.started_at)
        self.assertIsNone(tr.completed_at)
        self.assertIsNone(tr.exit_code)
        self.assertIsNone(tr.brief)
        self.assertEqual(tr.summary, "")
        self.assertEqual(tr.files_changed, [])
        self.assertIsNone(tr.diff_stat)
        self.assertEqual(tr.notes, "")
        self.assertIsNone(tr.error)
        self.assertIsNone(tr.worktree_path)
        self.assertFalse(tr.worktree_preserved)
        self.assertIsNone(tr.session_file)
        self.assertIsNotNone(tr.usage)

    def test_implementation_record_defaults(self):
        """ImplementationRecord defaults: empty events, empty tasks, empty active_resources."""
        ir = ImplementationRecord()
        self.assertIsNone(ir.started_at)
        self.assertIsNone(ir.completed_at)
        self.assertIsNone(ir.base_commit)
        self.assertEqual(ir.active_resources, {})
        self.assertEqual(ir.events, [])
        self.assertEqual(ir.tasks, {})

    def test_workflow_record_optional_phases(self):
        """WorkflowRecord brainstorm/plan/implementation/close default to None."""
        meta = WorkflowMeta(
            id="x", name="x", created_at="2026-01-01T00:00:00Z",
            status=WorkflowStatus.INIT, project="/tmp",
            source_branch="main", source_commit="abc", worktree=None
        )
        rec = WorkflowRecord(workflow=meta)
        self.assertIsNone(rec.brainstorm)
        self.assertIsNone(rec.plan)
        self.assertIsNone(rec.implementation)
        self.assertEqual(rec.reviews, [])
        self.assertIsNone(rec.close)
        self.assertEqual(rec.schema_version, CURRENT_SCHEMA_VERSION)


class TestCamelSnakeConversion(unittest.TestCase):
    def test_to_camel_case(self):
        """snake_case converts to camelCase: default_model -> defaultModel."""
        self.assertEqual(to_camel_case("default_model"), "defaultModel")
        self.assertEqual(to_camel_case("cache_read"), "cacheRead")
        self.assertEqual(to_camel_case("source_branch"), "sourceBranch")
        self.assertEqual(to_camel_case("auto_close"), "autoClose")
        self.assertEqual(to_camel_case("findings_actionable"), "findingsActionable")
        self.assertEqual(to_camel_case("schema_version"), "schemaVersion")

    def test_to_snake_case(self):
        """camelCase converts to snake_case: defaultModel -> default_model."""
        self.assertEqual(to_snake_case("defaultModel"), "default_model")
        self.assertEqual(to_snake_case("cacheRead"), "cache_read")
        self.assertEqual(to_snake_case("sourceBranch"), "source_branch")
        self.assertEqual(to_snake_case("autoClose"), "auto_close")
        self.assertEqual(to_snake_case("findingsActionable"), "findings_actionable")
        self.assertEqual(to_snake_case("schemaVersion"), "schema_version")

    def test_round_trip_camel_snake(self):
        """to_camel_case(to_snake_case(x)) == x for known keys."""
        keys = ["defaultModel", "cacheRead", "sourceBranch", "autoClose",
                "findingsActionable", "schemaVersion", "worktreePreserved"]
        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(to_camel_case(to_snake_case(key)), key)

    def test_single_word_unchanged(self):
        """Single words pass through unchanged in both directions."""
        self.assertEqual(to_camel_case("goal"), "goal")
        self.assertEqual(to_snake_case("goal"), "goal")
        self.assertEqual(to_camel_case("model"), "model")
        self.assertEqual(to_snake_case("model"), "model")


class TestFromDict(unittest.TestCase):
    def test_plan_from_json(self):
        """plan_from_json constructs Plan from camelCase dict."""
        data = {
            "goal": "Refactor auth",
            "context": "Express app",
            "tasks": [{
                "id": "task-1",
                "title": "Extract token module",
                "goal": "Move JWT logic",
                "files": ["src/auth.ts"],
                "constraints": ["Use visitor pattern"],
                "acceptance": ["tsc compiles"],
                "dependsOn": [],
            }]
        }
        plan = plan_from_json(data)
        self.assertEqual(plan.goal, "Refactor auth")
        self.assertEqual(plan.context, "Express app")
        self.assertIsNone(plan.default_model)
        self.assertEqual(len(plan.tasks), 1)
        self.assertEqual(plan.tasks[0].id, "task-1")

    def test_plan_from_json_with_tasks(self):
        """plan_from_json correctly deserializes nested Task objects."""
        data = {
            "goal": "Split module",
            "context": "TypeScript project",
            "defaultModel": "gpt-4",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Extract A",
                    "goal": "Move A",
                    "files": ["a.ts"],
                    "constraints": ["Keep exports"],
                    "acceptance": ["Compiles"],
                    "dependsOn": [],
                    "skills": ["debugging"],
                    "model": "gpt-3.5",
                },
                {
                    "id": "task-2",
                    "title": "Extract B",
                    "goal": "Move B",
                    "files": ["b.ts"],
                    "constraints": [],
                    "acceptance": ["Tests pass"],
                    "dependsOn": ["task-1"],
                }
            ]
        }
        plan = plan_from_json(data)
        self.assertEqual(plan.default_model, "gpt-4")
        self.assertEqual(len(plan.tasks), 2)
        # First task has optional fields
        t1 = plan.tasks[0]
        self.assertEqual(t1.skills, ["debugging"])
        self.assertEqual(t1.model, "gpt-3.5")
        # Second task has no optional fields
        t2 = plan.tasks[1]
        self.assertIsNone(t2.skills)
        self.assertIsNone(t2.model)
        self.assertEqual(t2.depends_on, ["task-1"])

    def test_plan_from_json_rejects_extra_keys(self):
        """plan_from_json rejects payloads with additional properties."""
        data = {
            "goal": "Split module",
            "context": "TypeScript project",
            "tasks": [{
                "id": "task-1",
                "title": "Extract A",
                "goal": "Move A",
                "files": ["a.ts"],
                "constraints": [],
                "acceptance": [],
                "dependsOn": [],
                "extra": "nope",
            }],
            "extraTop": True,
        }
        with self.assertRaises(ValueError) as ctx:
            plan_from_json(data)
        self.assertIn("additional properties", str(ctx.exception))

    def test_plan_from_json_rejects_wrong_types(self):
        """plan_from_json rejects payloads with wrong types."""
        data = {
            "goal": "Split module",
            "context": 123,
            "tasks": [{
                "id": "task-1",
                "title": "Extract A",
                "goal": "Move A",
                "files": ["a.ts"],
                "constraints": [],
                "acceptance": [],
                "dependsOn": [],
            }],
        }
        with self.assertRaises(ValueError) as ctx:
            plan_from_json(data)
        self.assertIn("expected string", str(ctx.exception))

    def test_record_from_json_minimal(self):
        """record_from_json handles a minimal record (workflow only)."""
        data = {
            "schemaVersion": 1,
            "workflow": {
                "id": "a1b2",
                "name": "test",
                "createdAt": "2026-01-01T00:00:00Z",
                "status": "init",
                "project": "/tmp/proj",
                "sourceBranch": "main",
                "sourceCommit": "abc123",
                "worktree": None,
            }
        }
        record = record_from_json(data)
        self.assertEqual(record.schema_version, 1)
        self.assertEqual(record.workflow.id, "a1b2")
        self.assertEqual(record.workflow.name, "test")
        self.assertEqual(record.workflow.status, WorkflowStatus.INIT)
        self.assertIsNone(record.workflow.worktree)
        self.assertIsNone(record.brainstorm)
        self.assertIsNone(record.plan)
        self.assertIsNone(record.implementation)
        self.assertEqual(record.reviews, [])
        self.assertIsNone(record.close)

    def test_record_from_json_full(self):
        """record_from_json handles a full record with all phases populated."""
        data = _make_full_record_dict()
        record = record_from_json(data)

        # Workflow
        self.assertEqual(record.workflow.status, WorkflowStatus.DONE)
        self.assertEqual(record.workflow.config.automation.brainstorm, AutomationLevel.INTERACTIVE)
        self.assertEqual(record.workflow.config.execute.concurrency, 4)
        self.assertEqual(record.workflow.config.agent.profile, "pi")
        self.assertEqual(record.workflow.config.models.aliases, {"fast": "claude-haiku-4-5"})

        # Brainstorm
        self.assertIsNotNone(record.brainstorm)
        self.assertEqual(record.brainstorm.motivation, "Auth module too big")
        self.assertEqual(len(record.brainstorm.design_decisions), 1)
        self.assertEqual(record.brainstorm.design_decisions[0].decision, "Use visitor")
        self.assertEqual(record.brainstorm.usage.input, 45000)

        # Plan
        self.assertIsNotNone(record.plan)
        self.assertEqual(record.plan.goal, "Split auth module")
        self.assertEqual(len(record.plan.tasks), 1)
        self.assertEqual(record.plan.tasks[0].id, "task-1")

        # Implementation
        self.assertIsNotNone(record.implementation)
        self.assertEqual(len(record.implementation.events), 2)
        self.assertEqual(
            record.implementation.events[0].event,
            ImplementationEventType.TASK_START
        )
        self.assertIn("task-1", record.implementation.tasks)
        self.assertEqual(
            record.implementation.tasks["task-1"].status,
            TaskStatus.DONE
        )

        # Reviews
        self.assertEqual(len(record.reviews), 1)
        self.assertTrue(record.reviews[0].findings_actionable)
        self.assertEqual(record.reviews[0].review_text, "Found issues")

        # Close
        self.assertIsNotNone(record.close)
        self.assertEqual(record.close.merge_result, "clean")
        self.assertEqual(record.close.final_commit, "ghi9012abc3456")

    def test_plan_from_json_missing_required_field(self):
        """plan_from_json raises on missing required field."""
        with self.assertRaises(ValueError) as ctx:
            plan_from_json({"goal": "Test"})
        self.assertIn("context", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            plan_from_json({"goal": "Test", "context": "C"})
        self.assertIn("tasks", str(ctx.exception))

        # Missing required field in nested Task
        with self.assertRaises(ValueError) as ctx:
            plan_from_json({
                "goal": "Test", "context": "C",
                "tasks": [{"id": "task-1"}]
            })
        self.assertIn("title", str(ctx.exception))


class TestToDict(unittest.TestCase):
    def test_plan_to_json(self):
        """plan_to_json produces camelCase dict from Plan."""
        task = Task(
            id="task-1", title="Extract token", goal="Move JWT",
            files=["src/auth.ts"], constraints=["Use visitor"],
            acceptance=["tsc compiles"], depends_on=["task-0"],
            skills=["debugging"], model="gpt-4"
        )
        plan = Plan(goal="Refactor", context="Express", tasks=[task], default_model="gpt-4")
        d = plan_to_json(plan)

        self.assertEqual(d["goal"], "Refactor")
        self.assertEqual(d["context"], "Express")
        self.assertEqual(d["defaultModel"], "gpt-4")
        self.assertEqual(len(d["tasks"]), 1)
        td = d["tasks"][0]
        self.assertEqual(td["id"], "task-1")
        self.assertEqual(td["dependsOn"], ["task-0"])
        self.assertEqual(td["skills"], ["debugging"])
        self.assertEqual(td["model"], "gpt-4")

    def test_record_to_json_round_trip(self):
        """record_to_json -> record_from_json produces equivalent record."""
        original_dict = _make_full_record_dict()
        record = record_from_json(original_dict)
        result_dict = record_to_json(record)

        # Direct dict comparison for better error messages on failure
        self.assertEqual(result_dict, original_dict)

    def test_plan_to_json_omits_none_optionals(self):
        """plan_to_json omits None optional fields (skills, model)."""
        task = Task(
            id="task-1", title="Test", goal="G",
            files=[], constraints=[], acceptance=[], depends_on=[]
        )
        plan = Plan(goal="G", context="C", tasks=[task])
        d = plan_to_json(plan)

        # defaultModel should not be in output
        self.assertNotIn("defaultModel", d)
        # skills and model should not be in task output
        td = d["tasks"][0]
        self.assertNotIn("skills", td)
        self.assertNotIn("model", td)

    def test_plan_round_trip(self):
        """plan_to_json(plan_from_json(plan_dict)) == original plan dict."""
        # Without optional fields
        plan_dict = {
            "goal": "Test goal",
            "context": "Test context",
            "tasks": [{
                "id": "task-1",
                "title": "First task",
                "goal": "Do the thing",
                "files": ["a.py", "b.py"],
                "constraints": ["Keep it simple"],
                "acceptance": ["Tests pass"],
                "dependsOn": [],
            }]
        }
        result = plan_to_json(plan_from_json(plan_dict))
        self.assertEqual(result, plan_dict)

        # With optional fields
        plan_dict_full = {
            "goal": "Test goal",
            "context": "Test context",
            "defaultModel": "gpt-4",
            "tasks": [{
                "id": "task-1",
                "title": "First task",
                "goal": "Do the thing",
                "files": ["a.py"],
                "constraints": [],
                "acceptance": ["Pass"],
                "dependsOn": [],
                "skills": ["debugging"],
                "model": "gpt-3.5",
            }]
        }
        result2 = plan_to_json(plan_from_json(plan_dict_full))
        self.assertEqual(result2, plan_dict_full)

    def test_record_to_json_schema_version_first(self):
        """record_to_json writes schemaVersion as the first key."""
        meta = WorkflowMeta(
            id="x", name="x", created_at="2026-01-01T00:00:00Z",
            status=WorkflowStatus.INIT, project="/tmp",
            source_branch="main", source_commit="abc", worktree=None
        )
        record = WorkflowRecord(workflow=meta)
        d = record_to_json(record)
        first_key = next(iter(d))
        self.assertEqual(first_key, "schemaVersion")

    def test_enum_serialization(self):
        """Enum fields serialize to their .value string."""
        meta = WorkflowMeta(
            id="x", name="x", created_at="2026-01-01T00:00:00Z",
            status=WorkflowStatus.IMPLEMENTING, project="/tmp",
            source_branch="main", source_commit="abc", worktree=None
        )
        d = _dataclass_to_dict(meta)
        self.assertEqual(d["status"], "implementing")

        tr = TaskResult(status=TaskStatus.FAILED)
        d2 = _dataclass_to_dict(tr)
        self.assertEqual(d2["status"], "failed")

    def test_nullable_serialization(self):
        """Optional/nullable fields serialize to null in JSON when None."""
        meta = WorkflowMeta(
            id="x", name="x", created_at="2026-01-01T00:00:00Z",
            status=WorkflowStatus.INIT, project="/tmp",
            source_branch="main", source_commit="abc", worktree=None
        )
        d = _dataclass_to_dict(meta)
        self.assertIsNone(d["worktree"])
        self.assertIn("worktree", d)  # Key is present, value is null


class TestRecordFromJsonEdgeCases(unittest.TestCase):
    def test_schema_version_default_when_absent(self):
        """record_from_json defaults schemaVersion to 1 if absent."""
        data = {
            "workflow": {
                "id": "x", "name": "x", "createdAt": "2026-01-01T00:00:00Z",
                "status": "init", "project": "/tmp",
                "sourceBranch": "main", "sourceCommit": "abc",
            }
        }
        record = record_from_json(data)
        self.assertEqual(record.schema_version, 1)

    def test_schema_version_rejects_newer(self):
        """record_from_json raises ValueError when schemaVersion > CURRENT_SCHEMA_VERSION."""
        data = {
            "schemaVersion": CURRENT_SCHEMA_VERSION + 1,
            "workflow": {
                "id": "x", "name": "x", "createdAt": "2026-01-01T00:00:00Z",
                "status": "init", "project": "/tmp",
                "sourceBranch": "main", "sourceCommit": "abc",
            }
        }
        with self.assertRaises(ValueError) as ctx:
            record_from_json(data)
        self.assertIn("upgrade", str(ctx.exception).lower())

    def test_ignores_unknown_top_level_keys(self):
        """record_from_json ignores unknown top-level keys (forward-compat)."""
        data = {
            "schemaVersion": 1,
            "workflow": {
                "id": "x", "name": "x", "createdAt": "2026-01-01T00:00:00Z",
                "status": "init", "project": "/tmp",
                "sourceBranch": "main", "sourceCommit": "abc",
            },
            "futurePhase": {"some": "data"},
            "council": ["member1", "member2"],
        }
        record = record_from_json(data)
        self.assertEqual(record.workflow.id, "x")
        # Unknown keys are silently ignored
        self.assertFalse(hasattr(record, "futurePhase"))

    def test_implementation_event_string_coercion(self):
        """ImplementationEvent.__post_init__ coerces string event to enum."""
        evt = ImplementationEvent(t="2026-01-01T00:00:00Z", event="taskStart")
        self.assertEqual(evt.event, ImplementationEventType.TASK_START)

    def test_implementation_event_invalid_string(self):
        """ImplementationEvent rejects invalid event strings."""
        with self.assertRaises(ValueError):
            ImplementationEvent(t="2026-01-01T00:00:00Z", event="notAnEvent")

    def test_review_with_fixup_plan(self):
        """record_from_json correctly deserializes ReviewRecord with fixupPlan."""
        data = {
            "schemaVersion": 1,
            "workflow": {
                "id": "x", "name": "x", "createdAt": "2026-01-01T00:00:00Z",
                "status": "reviewing", "project": "/tmp",
                "sourceBranch": "main", "sourceCommit": "abc",
            },
            "reviews": [{
                "recordedAt": "2026-01-01T12:00:00Z",
                "baseCommit": "abc123",
                "reviewText": "Issues found",
                "findingsActionable": True,
                "usage": {"input": 1000, "output": 500},
                "fixupPlan": {
                    "goal": "Fix issues",
                    "context": "Review findings",
                    "tasks": [{
                        "id": "fixup-1",
                        "title": "Fix JSDoc",
                        "goal": "Add missing JSDoc",
                        "files": ["src/token.ts"],
                        "constraints": [],
                        "acceptance": ["JSDoc present"],
                        "dependsOn": [],
                    }]
                },
                "fixupImplementation": {
                    "startedAt": "2026-01-01T12:05:00Z",
                    "completedAt": "2026-01-01T12:10:00Z",
                    "tasks": {
                        "fixup-1": {
                            "status": "done",
                            "summary": "Added JSDoc"
                        }
                    }
                }
            }]
        }
        record = record_from_json(data)
        self.assertEqual(len(record.reviews), 1)
        review = record.reviews[0]
        self.assertIsNotNone(review.fixup_plan)
        self.assertEqual(review.fixup_plan.goal, "Fix issues")
        self.assertEqual(len(review.fixup_plan.tasks), 1)
        self.assertIsNotNone(review.fixup_implementation)
        self.assertEqual(
            review.fixup_implementation.tasks["fixup-1"].status,
            TaskStatus.DONE
        )


class TestExtractToolCall(unittest.TestCase):
    def test_extract_report_result(self):
        """extract_tool_call finds report_result in messages."""
        messages = [
            {"role": "user", "content": "Do the task"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "I'll do it"},
                {"type": "toolCall", "name": "report_result", "arguments": {
                    "summary": "Implemented the feature",
                    "notes": "Had to refactor the helper"
                }}
            ]}
        ]
        result = extract_tool_call(messages, "report_result")
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Implemented the feature")
        self.assertEqual(result["notes"], "Had to refactor the helper")

    def test_extract_submit_plan(self):
        """extract_tool_call finds submit_plan in messages."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "toolCall", "name": "submit_plan", "arguments": {
                    "goal": "Refactor auth",
                    "context": "Express app",
                    "tasks": []
                }}
            ]}
        ]
        result = extract_tool_call(messages, "submit_plan")
        self.assertIsNotNone(result)
        self.assertEqual(result["goal"], "Refactor auth")

    def test_extract_returns_none_when_not_found(self):
        """extract_tool_call returns None when tool not called."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Hi there"}
            ]}
        ]
        self.assertIsNone(extract_tool_call(messages, "report_result"))

    def test_extract_finds_last_occurrence(self):
        """extract_tool_call returns the last matching tool call, not the first."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "toolCall", "name": "report_result", "arguments": {
                    "summary": "First attempt",
                    "notes": ""
                }}
            ]},
            {"role": "user", "content": "Try again"},
            {"role": "assistant", "content": [
                {"type": "toolCall", "name": "report_result", "arguments": {
                    "summary": "Second attempt",
                    "notes": "Fixed it"
                }}
            ]}
        ]
        result = extract_tool_call(messages, "report_result")
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Second attempt")
        self.assertEqual(result["notes"], "Fixed it")

    def test_extract_from_empty_messages(self):
        """extract_tool_call handles empty message list."""
        self.assertIsNone(extract_tool_call([], "report_result"))

    def test_extract_ignores_user_messages(self):
        """extract_tool_call only looks at assistant messages."""
        messages = [
            {"role": "user", "content": [
                {"type": "toolCall", "name": "report_result", "arguments": {
                    "summary": "Fake", "notes": ""
                }}
            ]}
        ]
        self.assertIsNone(extract_tool_call(messages, "report_result"))

    def test_extract_handles_string_content(self):
        """extract_tool_call handles assistant messages with string content."""
        messages = [
            {"role": "assistant", "content": "Just a text response"}
        ]
        self.assertIsNone(extract_tool_call(messages, "report_result"))

    def test_extract_different_tool_name(self):
        """extract_tool_call doesn't match different tool names."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "toolCall", "name": "submit_plan", "arguments": {
                    "goal": "Plan"
                }}
            ]}
        ]
        self.assertIsNone(extract_tool_call(messages, "report_result"))
        self.assertIsNotNone(extract_tool_call(messages, "submit_plan"))


class TestValidateSchema(unittest.TestCase):
    def test_valid_plan(self):
        """validate_schema returns empty errors for valid plan."""
        plan = {
            "goal": "Test",
            "context": "Context",
            "tasks": [{
                "id": "task-1", "title": "T", "goal": "G",
                "files": [], "constraints": [], "acceptance": [],
                "dependsOn": []
            }]
        }
        self.assertEqual(validate_schema(plan, "plan"), [])

    def test_plan_missing_required(self):
        """validate_schema returns errors for missing required plan fields."""
        errors = validate_schema({"goal": "Test"}, "plan")
        self.assertTrue(len(errors) > 0)
        field_errors = " ".join(errors)
        self.assertIn("context", field_errors)
        self.assertIn("tasks", field_errors)

    def test_plan_empty_tasks(self):
        """validate_schema catches empty tasks array (minItems: 1)."""
        plan = {"goal": "Test", "context": "C", "tasks": []}
        errors = validate_schema(plan, "plan")
        self.assertTrue(any("at least 1" in e for e in errors))

    def test_valid_record(self):
        """validate_schema returns empty errors for valid full record."""
        record = {
            "schemaVersion": 1,
            "workflow": {
                "id": "a1b2", "name": "test",
                "createdAt": "2026-01-01T00:00:00Z",
                "status": "init", "project": "/tmp",
                "sourceBranch": "main", "sourceCommit": "abc"
            }
        }
        self.assertEqual(validate_schema(record), [])

    def test_record_missing_workflow(self):
        """validate_schema returns error for record missing workflow."""
        errors = validate_schema({})
        self.assertTrue(any("workflow" in e for e in errors))

    def test_valid_report_result(self):
        """validate_schema validates report-result component."""
        self.assertEqual(
            validate_schema({"summary": "Done", "notes": ""}, "report-result"),
            []
        )

    def test_report_result_missing_fields(self):
        """validate_schema catches missing report-result fields."""
        errors = validate_schema({}, "report-result")
        self.assertTrue(len(errors) >= 2)
        field_errors = " ".join(errors)
        self.assertIn("summary", field_errors)
        self.assertIn("notes", field_errors)

    def test_valid_brainstorm(self):
        """validate_schema validates brainstorm component."""
        brainstorm = {
            "motivation": "Problem",
            "solution": "Approach",
            "designDecisions": [
                {"decision": "Use X", "rationale": "Because Y"}
            ]
        }
        self.assertEqual(validate_schema(brainstorm, "brainstorm"), [])

    def test_valid_task(self):
        """validate_schema validates task component."""
        task = {
            "id": "task-1", "title": "T", "goal": "G",
            "files": [], "constraints": [], "acceptance": [],
            "dependsOn": []
        }
        self.assertEqual(validate_schema(task, "task"), [])

    def test_task_missing_fields(self):
        """validate_schema catches missing task required fields."""
        errors = validate_schema({"id": "task-1"}, "task")
        self.assertTrue(len(errors) > 0)

    def test_task_rejects_extra_keys(self):
        """validate_schema rejects additionalProperties for task."""
        task = {
            "id": "task-1", "title": "T", "goal": "G",
            "files": [], "constraints": [], "acceptance": [],
            "dependsOn": [], "extra": "nope"
        }
        errors = validate_schema(task, "task")
        self.assertTrue(any("extra" in e for e in errors))

    def test_plan_rejects_wrong_types(self):
        """validate_schema rejects wrong-typed plan fields."""
        plan = {
            "goal": "Test",
            "context": 5,
            "tasks": [{
                "id": "task-1", "title": "T", "goal": "G",
                "files": [], "constraints": [], "acceptance": [],
                "dependsOn": []
            }]
        }
        errors = validate_schema(plan, "plan")
        self.assertTrue(any("expected string" in e for e in errors))

    def test_additional_properties_schema_validation(self):
        """validate_schema validates additionalProperties schemas for dict values."""
        record = {
            "workflow": {
                "id": "a1b2", "name": "test",
                "createdAt": "2026-01-01T00:00:00Z",
                "status": "init", "project": "/tmp",
                "sourceBranch": "main", "sourceCommit": "abc"
            },
            "implementation": {
                "activeResources": {
                    "task-1": 123
                }
            }
        }
        errors = validate_schema(record)
        self.assertTrue(any("implementation.activeResources.task-1" in e for e in errors))

    def test_valid_usage(self):
        """validate_schema validates usage component."""
        usage = {
            "model": "gpt-4",
            "input": 1000,
            "output": 500,
            "cacheRead": 0,
            "cacheWrite": 0,
            "cost": 0.01,
            "turns": 1
        }
        self.assertEqual(validate_schema(usage, "usage"), [])

    def test_unknown_component(self):
        """validate_schema returns error for unknown component name."""
        errors = validate_schema({}, "nonexistent")
        self.assertTrue(len(errors) > 0)
        self.assertIn("Unknown component", errors[0])


class TestDictKeyPreservation(unittest.TestCase):
    """Verify that data keys (task IDs, aliases, profile names) with
    underscores are preserved as-is during serialization, not camelCase-converted.
    """

    def test_underscored_task_ids_preserved(self):
        """Task IDs with underscores survive round-trip."""
        impl = ImplementationRecord(
            tasks={
                "task_one": TaskResult(status=TaskStatus.DONE, summary="Done"),
                "task_two": TaskResult(status=TaskStatus.FAILED, error="Oops"),
            }
        )
        d = _dataclass_to_dict(impl)
        self.assertIn("task_one", d["tasks"])
        self.assertIn("task_two", d["tasks"])
        # Must NOT be converted to taskOne / taskTwo
        self.assertNotIn("taskOne", d["tasks"])
        self.assertNotIn("taskTwo", d["tasks"])

    def test_underscored_active_resources_preserved(self):
        """Active resource keys with underscores survive serialization."""
        impl = ImplementationRecord(
            active_resources={"task_foo": "/path/to/worktree"}
        )
        d = _dataclass_to_dict(impl)
        self.assertIn("task_foo", d["activeResources"])
        self.assertNotIn("taskFoo", d["activeResources"])

    def test_underscored_model_aliases_preserved(self):
        """Model alias names with underscores survive serialization."""
        models = ModelsConfig(
            aliases={"my_alias": "claude-sonnet-4-5"},
            profiles={"my_profile": {"gpt_4o": "openai/gpt-4o"}},
        )
        d = _dataclass_to_dict(models)
        self.assertIn("my_alias", d["aliases"])
        self.assertNotIn("myAlias", d["aliases"])
        self.assertIn("my_profile", d["profiles"])
        self.assertNotIn("myProfile", d["profiles"])
        # Nested dict keys also preserved
        self.assertIn("gpt_4o", d["profiles"]["my_profile"])
        self.assertNotIn("gpt4o", d["profiles"]["my_profile"])

    def test_underscored_keys_round_trip(self):
        """Full record round-trip preserves underscored data keys."""
        record_dict = _make_full_record_dict()
        # Add underscored keys to the fixture
        record_dict["implementation"]["tasks"]["task_with_underscores"] = {
            "status": "done",
            "summary": "Task with underscored ID",
            "filesChanged": [],
            "notes": "",
            "worktreePreserved": False,
            "usage": {},
        }
        record_dict["implementation"]["activeResources"] = {
            "task_with_underscores": "/path/wt"
        }
        record_dict["workflow"]["config"]["models"]["aliases"] = {
            "my_fast": "claude-haiku-4-5"
        }

        record = record_from_json(record_dict)
        result = record_to_json(record)

        self.assertIn("task_with_underscores", result["implementation"]["tasks"])
        self.assertIn("task_with_underscores", result["implementation"]["activeResources"])
        self.assertIn("my_fast", result["workflow"]["config"]["models"]["aliases"])


class TestGenericHelpers(unittest.TestCase):
    def test_dataclass_to_dict_basic(self):
        """_dataclass_to_dict serializes a simple dataclass."""
        u = Usage(model="gpt-4", input=100, output=50)
        d = _dataclass_to_dict(u)
        self.assertEqual(d["model"], "gpt-4")
        self.assertEqual(d["input"], 100)
        self.assertEqual(d["output"], 50)
        self.assertEqual(d["cacheRead"], 0)

    def test_dict_to_dataclass_basic(self):
        """_dict_to_dataclass deserializes from camelCase dict."""
        d = {"model": "gpt-4", "input": 100, "output": 50,
             "cacheRead": 0, "cacheWrite": 0, "cost": 0.01, "turns": 1}
        u = _dict_to_dataclass(Usage, d)
        self.assertEqual(u.model, "gpt-4")
        self.assertEqual(u.input, 100)
        self.assertEqual(u.cache_read, 0)

    def test_dict_to_dataclass_with_defaults(self):
        """_dict_to_dataclass allows missing fields that have defaults."""
        d = {"model": "gpt-4"}
        u = _dict_to_dataclass(Usage, d)
        self.assertEqual(u.model, "gpt-4")
        self.assertEqual(u.input, 0)
        self.assertEqual(u.output, 0)

    def test_dict_to_dataclass_raises_on_missing_required(self):
        """_dict_to_dataclass raises ValueError on missing required fields."""
        with self.assertRaises(ValueError) as ctx:
            _dict_to_dataclass(Task, {"id": "task-1"})
        self.assertIn("title", str(ctx.exception))


# --- Helpers ---

def _make_full_record_dict() -> dict:
    """Build a fully-populated record dict for testing round-trips."""
    return {
        "schemaVersion": 1,
        "workflow": {
            "id": "a1b2",
            "name": "auth-refactor",
            "createdAt": "2026-04-01T10:00:00Z",
            "status": "done",
            "project": "/home/user/myproject",
            "sourceBranch": "main",
            "sourceCommit": "abc1234def5678",
            "worktree": "/home/user/myproject-wf-auth-refactor",
            "config": {
                "model": {
                    "brainstorm": "claude-sonnet-4-5",
                    "plan": "claude-sonnet-4-5",
                    "implement": None,
                    "review": None,
                    "fixup": None,
                    "close": None,
                },
                "automation": {
                    "brainstorm": "interactive",
                    "plan": "interactive",
                    "implement": "supervised",
                    "review": "automatic",
                    "close": "automatic",
                },
                "execute": {
                    "concurrency": 4,
                    "worktrees": True,
                    "autoReview": True,
                },
                "ui": {
                    "autoClose": 30,
                    "tmux": True,
                },
                "agent": {
                    "profile": "pi",
                    "cmd": None,
                },
                "models": {
                    "aliases": {"fast": "claude-haiku-4-5"},
                    "profiles": {},
                },
            }
        },
        "brainstorm": {
            "recordedAt": "2026-04-01T10:30:00Z",
            "motivation": "Auth module too big",
            "solution": "Split into modules",
            "designDecisions": [
                {"decision": "Use visitor", "rationale": "Multiple types"}
            ],
            "usage": {
                "model": "claude-sonnet-4-5",
                "input": 45000,
                "output": 8000,
                "cacheRead": 0,
                "cacheWrite": 0,
                "cost": 0.082,
                "turns": 4,
            }
        },
        "plan": {
            "recordedAt": "2026-04-01T11:00:00Z",
            "goal": "Split auth module",
            "context": "Express app",
            "defaultModel": "claude-sonnet-4-5",
            "tasks": [{
                "id": "task-1",
                "title": "Extract token",
                "goal": "Move JWT logic",
                "files": ["src/auth.ts"],
                "constraints": ["Use visitor"],
                "acceptance": ["tsc compiles"],
                "dependsOn": [],
                "skills": None,
                "model": None,
            }],
            "usage": {
                "model": "claude-sonnet-4-5",
                "input": 32000,
                "output": 6000,
                "cacheRead": 0,
                "cacheWrite": 0,
                "cost": 0.0,
                "turns": 0,
            }
        },
        "implementation": {
            "startedAt": "2026-04-01T11:05:00Z",
            "completedAt": "2026-04-01T11:42:00Z",
            "baseCommit": "def5678abc1234",
            "activeResources": {},
            "events": [
                {
                    "t": "2026-04-01T11:05:00Z",
                    "event": "taskStart",
                    "task": "task-1",
                    "detail": None,
                },
                {
                    "t": "2026-04-01T11:18:00Z",
                    "event": "taskComplete",
                    "task": "task-1",
                    "detail": None,
                }
            ],
            "tasks": {
                "task-1": {
                    "status": "done",
                    "startedAt": "2026-04-01T11:05:00Z",
                    "completedAt": "2026-04-01T11:18:00Z",
                    "exitCode": 0,
                    "brief": None,
                    "summary": "Extracted token module",
                    "filesChanged": ["src/token.ts"],
                    "diffStat": None,
                    "notes": "",
                    "error": None,
                    "worktreePath": None,
                    "worktreePreserved": False,
                    "sessionFile": None,
                    "usage": {
                        "model": "claude-sonnet-4-5",
                        "input": 23000,
                        "output": 5400,
                        "cacheRead": 0,
                        "cacheWrite": 0,
                        "cost": 0.0,
                        "turns": 0,
                    }
                }
            }
        },
        "reviews": [{
            "recordedAt": "2026-04-01T11:45:00Z",
            "baseCommit": "def5678abc1234",
            "reviewText": "Found issues",
            "findingsActionable": True,
            "usage": {
                "model": "claude-sonnet-4-5",
                "input": 28000,
                "output": 4200,
                "cacheRead": 0,
                "cacheWrite": 0,
                "cost": 0.0,
                "turns": 0,
            },
            "fixupPlan": None,
            "fixupImplementation": None,
        }],
        "close": {
            "recordedAt": "2026-04-01T12:00:00Z",
            "mergeResult": "clean",
            "finalCommit": "ghi9012abc3456",
            "diffStat": "12 files changed",
        }
    }


if __name__ == "__main__":
    unittest.main()
