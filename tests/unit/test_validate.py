"""Tests for wflib.validate — plan validation: deps, cycles, heuristic warnings."""

import unittest

from wflib.validate import (
    ValidationResult,
    validate_plan,
    _check_refs,
    _check_cycles,
    _check_duplicate_ids,
    _check_empty_acceptance,
    _check_constraint_count,
    _check_empty_goal,
)
from wflib.types import Plan, Task


_SENTINEL = object()

def _make_task(
    id: str = "task-1",
    title: str = "Test task",
    goal: str = "A sufficiently long goal for validation",
    files: list[str] | None = None,
    constraints: object = _SENTINEL,
    acceptance: object = _SENTINEL,
    depends_on: list[str] | None = None,
    **kwargs,
) -> Task:
    """Helper to build a Task with sensible defaults."""
    return Task(
        id=id,
        title=title,
        goal=goal,
        files=files if files is not None else ["src/main.py"],
        constraints=constraints if constraints is not _SENTINEL else ["keep it simple"],
        acceptance=acceptance if acceptance is not _SENTINEL else ["tests pass"],
        depends_on=depends_on if depends_on is not None else [],
        **kwargs,
    )


def _make_plan(tasks: list[Task] | None = None, **kwargs) -> Plan:
    """Helper to build a Plan with sensible defaults."""
    return Plan(
        goal=kwargs.get("goal", "Implement feature X"),
        context=kwargs.get("context", "Project context"),
        tasks=tasks or [_make_task()],
    )


class TestStructuralChecks(unittest.TestCase):
    def test_valid_plan_passes(self):
        """A well-formed plan with valid deps returns no errors."""
        tasks = [
            _make_task(id="task-1", depends_on=[]),
            _make_task(id="task-2", depends_on=["task-1"]),
            _make_task(id="task-3", depends_on=["task-1", "task-2"]),
        ]
        plan = _make_plan(tasks=tasks)
        result = validate_plan(plan)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_missing_dep_ref(self):
        """dependsOn referencing a non-existent task ID is a hard error."""
        tasks = [
            _make_task(id="task-1", depends_on=[]),
            _make_task(id="task-2", depends_on=["task-99"]),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_refs(plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("task-2", errors[0])
        self.assertIn("task-99", errors[0])

    def test_missing_dep_ref_raises(self):
        """validate_plan raises ValueError for missing dep refs."""
        tasks = [
            _make_task(id="task-1", depends_on=["nonexistent"]),
        ]
        plan = _make_plan(tasks=tasks)
        with self.assertRaises(ValueError) as ctx:
            validate_plan(plan)
        self.assertIn("nonexistent", str(ctx.exception))

    def test_multiple_missing_refs(self):
        """Multiple missing refs each produce an error."""
        tasks = [
            _make_task(id="task-1", depends_on=["x", "y"]),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_refs(plan)
        self.assertEqual(len(errors), 2)

    def test_cycle_detection_simple(self):
        """A->B->A cycle is detected as a hard error."""
        tasks = [
            _make_task(id="A", depends_on=["B"]),
            _make_task(id="B", depends_on=["A"]),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_cycles(plan)
        self.assertGreaterEqual(len(errors), 1)
        # The cycle message should mention both A and B
        cycle_msg = errors[0]
        self.assertIn("A", cycle_msg)
        self.assertIn("B", cycle_msg)
        self.assertIn("cycle", cycle_msg.lower())

    def test_cycle_detection_transitive(self):
        """A->B->C->A cycle is detected."""
        tasks = [
            _make_task(id="A", depends_on=["C"]),
            _make_task(id="B", depends_on=["A"]),
            _make_task(id="C", depends_on=["B"]),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_cycles(plan)
        self.assertGreaterEqual(len(errors), 1)
        cycle_msg = errors[0]
        self.assertIn("cycle", cycle_msg.lower())

    def test_duplicate_ids(self):
        """Duplicate task IDs are a hard error."""
        tasks = [
            _make_task(id="task-1"),
            _make_task(id="task-1"),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_duplicate_ids(plan)
        self.assertEqual(len(errors), 1)
        self.assertIn("task-1", errors[0])

    def test_duplicate_ids_raises(self):
        """validate_plan raises ValueError for duplicate IDs."""
        tasks = [
            _make_task(id="task-1"),
            _make_task(id="task-1"),
        ]
        plan = _make_plan(tasks=tasks)
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_self_dependency(self):
        """A task depending on itself is a cycle error."""
        tasks = [
            _make_task(id="task-1", depends_on=["task-1"]),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_cycles(plan)
        self.assertGreaterEqual(len(errors), 1)
        self.assertIn("cycle", errors[0].lower())
        self.assertIn("task-1", errors[0])

    def test_no_cycle_in_dag(self):
        """A valid DAG (no cycle) produces no cycle errors."""
        tasks = [
            _make_task(id="A", depends_on=[]),
            _make_task(id="B", depends_on=["A"]),
            _make_task(id="C", depends_on=["A"]),
            _make_task(id="D", depends_on=["B", "C"]),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_cycles(plan)
        self.assertEqual(errors, [])

    def test_no_duplicate_ids(self):
        """Unique IDs produce no duplicate errors."""
        tasks = [
            _make_task(id="a"),
            _make_task(id="b"),
            _make_task(id="c"),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_duplicate_ids(plan)
        self.assertEqual(errors, [])

    def test_triple_duplicate(self):
        """Three tasks with same ID produce two errors."""
        tasks = [
            _make_task(id="dup"),
            _make_task(id="dup"),
            _make_task(id="dup"),
        ]
        plan = _make_plan(tasks=tasks)
        errors = _check_duplicate_ids(plan)
        self.assertEqual(len(errors), 2)


class TestHeuristicWarnings(unittest.TestCase):
    def test_empty_acceptance_warns(self):
        """Tasks with zero acceptance criteria produce a warning."""
        tasks = [
            _make_task(id="task-1", acceptance=[]),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_empty_acceptance(plan)
        self.assertEqual(len(warnings), 1)
        self.assertIn("task-1", warnings[0])
        self.assertIn("acceptance", warnings[0].lower())

    def test_nonempty_acceptance_no_warning(self):
        """Tasks with acceptance criteria produce no warning."""
        tasks = [
            _make_task(id="task-1", acceptance=["tests pass"]),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_empty_acceptance(plan)
        self.assertEqual(warnings, [])

    def test_high_constraint_count_warns(self):
        """Tasks with >6 constraints produce a warning."""
        tasks = [
            _make_task(
                id="task-1",
                constraints=["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
            ),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_constraint_count(plan)
        self.assertEqual(len(warnings), 1)
        self.assertIn("task-1", warnings[0])
        self.assertIn("7", warnings[0])

    def test_exactly_six_constraints_no_warning(self):
        """Tasks with exactly 6 constraints produce no warning."""
        tasks = [
            _make_task(
                id="task-1",
                constraints=["c1", "c2", "c3", "c4", "c5", "c6"],
            ),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_constraint_count(plan)
        self.assertEqual(warnings, [])

    def test_custom_threshold(self):
        """Custom threshold is respected."""
        tasks = [
            _make_task(id="task-1", constraints=["c1", "c2", "c3"]),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_constraint_count(plan, threshold=2)
        self.assertEqual(len(warnings), 1)

    def test_empty_goal_warns(self):
        """Tasks with empty or very short goal produce a warning."""
        tasks = [
            _make_task(id="task-1", goal=""),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_empty_goal(plan)
        self.assertEqual(len(warnings), 1)
        self.assertIn("task-1", warnings[0])

    def test_short_goal_warns(self):
        """Tasks with goal shorter than 10 chars produce a warning."""
        tasks = [
            _make_task(id="task-1", goal="fix it"),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_empty_goal(plan)
        self.assertEqual(len(warnings), 1)

    def test_whitespace_only_goal_warns(self):
        """Goals that are only whitespace are considered empty."""
        tasks = [
            _make_task(id="task-1", goal="         "),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_empty_goal(plan)
        self.assertEqual(len(warnings), 1)

    def test_sufficient_goal_no_warning(self):
        """Goals of 10+ chars produce no warning."""
        tasks = [
            _make_task(id="task-1", goal="Extract the auth module"),
        ]
        plan = _make_plan(tasks=tasks)
        warnings = _check_empty_goal(plan)
        self.assertEqual(warnings, [])

    def test_normal_plan_no_warnings(self):
        """A well-formed plan with reasonable sizes produces no warnings."""
        tasks = [
            _make_task(
                id="task-1",
                goal="A properly described goal for validation",
                acceptance=["tests pass", "lint clean"],
                constraints=["use stdlib only"],
            ),
            _make_task(
                id="task-2",
                goal="Another properly described goal here",
                acceptance=["integration tests pass"],
                constraints=["no new dependencies"],
                depends_on=["task-1"],
            ),
        ]
        plan = _make_plan(tasks=tasks)
        result = validate_plan(plan)
        self.assertEqual(result.warnings, [])

    def test_multiple_warnings_from_different_checks(self):
        """Warnings from multiple heuristic checks are all collected."""
        tasks = [
            _make_task(id="task-1", goal="short", acceptance=[]),
            _make_task(
                id="task-2",
                constraints=["c1", "c2", "c3", "c4", "c5", "c6", "c7"],
            ),
        ]
        plan = _make_plan(tasks=tasks)
        result = validate_plan(plan)
        # task-1: empty acceptance + short goal = 2 warnings
        # task-2: high constraint count = 1 warning
        self.assertEqual(len(result.warnings), 3)


class TestValidationResult(unittest.TestCase):
    def test_errors_and_warnings_separate(self):
        """A plan can have warnings without errors (valid but suspect)."""
        tasks = [
            _make_task(id="task-1", acceptance=[]),
        ]
        plan = _make_plan(tasks=tasks)
        result = validate_plan(plan)
        self.assertEqual(result.errors, [])
        self.assertGreater(len(result.warnings), 0)

    def test_errors_mean_invalid(self):
        """A plan with errors is invalid regardless of warnings."""
        tasks = [
            _make_task(id="task-1", depends_on=["nonexistent"], acceptance=[]),
        ]
        plan = _make_plan(tasks=tasks)
        with self.assertRaises(ValueError):
            validate_plan(plan)

    def test_validation_result_defaults(self):
        """ValidationResult defaults to empty lists."""
        result = ValidationResult()
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_single_task_valid_plan(self):
        """A single well-formed task passes all checks."""
        tasks = [_make_task(id="task-1")]
        plan = _make_plan(tasks=tasks)
        result = validate_plan(plan)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
