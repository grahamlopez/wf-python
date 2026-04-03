"""Tests for wflib.scheduler — pure scheduling functions.

Tests cover the 4 pure functions:
  - get_ready_tasks
  - skip_dependents
  - reset_ready_skipped
  - resolve_task_model
"""

import unittest

from wflib.scheduler import (
    get_ready_tasks,
    skip_dependents,
    reset_ready_skipped,
    resolve_task_model,
)
from wflib.types import (
    ModelConfig,
    Plan,
    Task,
    TaskStatus,
    WorkflowConfig,
)


def _task(tid: str, depends_on: list[str] | None = None, model: str | None = None) -> Task:
    """Helper to build a minimal Task."""
    return Task(
        id=tid,
        title=f"Task {tid}",
        goal=f"Goal for {tid}",
        files=[],
        constraints=[],
        acceptance=[],
        depends_on=depends_on or [],
        model=model,
    )


def _plan(tasks: list[Task], default_model: str | None = None) -> Plan:
    """Helper to build a minimal Plan."""
    return Plan(
        goal="Test plan",
        context="Test context",
        tasks=tasks,
        default_model=default_model,
    )


# ============================================================
# get_ready_tasks
# ============================================================


class TestGetReadyTasks(unittest.TestCase):
    """Tests for get_ready_tasks."""

    def test_empty_plan(self):
        """Empty plan → no ready tasks."""
        plan = _plan([])
        result = get_ready_tasks(plan, {})
        self.assertEqual(result, [])

    def test_all_independent(self):
        """All tasks with no deps → all ready."""
        tasks = [_task("c"), _task("a"), _task("b")]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.PENDING, "b": TaskStatus.PENDING, "c": TaskStatus.PENDING}
        result = get_ready_tasks(plan, statuses)
        # Should be sorted lexicographically
        self.assertEqual([t.id for t in result], ["a", "b", "c"])

    def test_deps_met(self):
        """Task with deps met → ready."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.DONE, "b": TaskStatus.PENDING}
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["b"])

    def test_deps_not_met(self):
        """Task with deps not met → not ready."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.PENDING, "b": TaskStatus.PENDING}
        result = get_ready_tasks(plan, statuses)
        # Only 'a' is ready (no deps), 'b' is not (dep on 'a' not done)
        self.assertEqual([t.id for t in result], ["a"])

    def test_diamond_pattern_root_only(self):
        """Diamond: A→{B,C}→D — initially only A is ready."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("d", depends_on=["b", "c"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.PENDING,
            "b": TaskStatus.PENDING,
            "c": TaskStatus.PENDING,
            "d": TaskStatus.PENDING,
        }
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["a"])

    def test_diamond_pattern_middle_tier(self):
        """Diamond: A done → B and C ready."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("d", depends_on=["b", "c"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.DONE,
            "b": TaskStatus.PENDING,
            "c": TaskStatus.PENDING,
            "d": TaskStatus.PENDING,
        }
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["b", "c"])

    def test_diamond_pattern_final(self):
        """Diamond: B,C done → D ready."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("d", depends_on=["b", "c"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.DONE,
            "b": TaskStatus.DONE,
            "c": TaskStatus.DONE,
            "d": TaskStatus.PENDING,
        }
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["d"])

    def test_done_tasks_not_returned(self):
        """Tasks already done are not returned as ready."""
        tasks = [_task("a"), _task("b")]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.DONE, "b": TaskStatus.PENDING}
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["b"])

    def test_failed_tasks_not_returned(self):
        """Tasks already failed are not returned as ready."""
        tasks = [_task("a"), _task("b")]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.FAILED, "b": TaskStatus.PENDING}
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["b"])

    def test_running_tasks_not_returned(self):
        """Tasks currently running are not returned as ready."""
        tasks = [_task("a"), _task("b")]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.RUNNING, "b": TaskStatus.PENDING}
        result = get_ready_tasks(plan, statuses)
        self.assertEqual([t.id for t in result], ["b"])

    def test_missing_status_defaults_to_pending(self):
        """Task not in statuses dict is treated as pending."""
        tasks = [_task("a")]
        plan = _plan(tasks)
        # Empty statuses dict — task 'a' should default to PENDING
        result = get_ready_tasks(plan, {})
        self.assertEqual([t.id for t in result], ["a"])


# ============================================================
# skip_dependents
# ============================================================


class TestSkipDependents(unittest.TestCase):
    """Tests for skip_dependents."""

    def test_direct_dependent_skipped(self):
        """Direct dependent of failed task is skipped."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.FAILED, "b": TaskStatus.PENDING}
        skipped = skip_dependents(plan, statuses, "a")
        self.assertEqual(skipped, ["b"])
        self.assertEqual(statuses["b"], TaskStatus.SKIPPED)

    def test_transitive_chain(self):
        """A→B→C, A fails → B and C both skipped."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["b"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.FAILED,
            "b": TaskStatus.PENDING,
            "c": TaskStatus.PENDING,
        }
        skipped = skip_dependents(plan, statuses, "a")
        self.assertIn("b", skipped)
        self.assertIn("c", skipped)
        self.assertEqual(len(skipped), 2)
        self.assertEqual(statuses["b"], TaskStatus.SKIPPED)
        self.assertEqual(statuses["c"], TaskStatus.SKIPPED)

    def test_diamond_convergence(self):
        """A→{B,C}→D, A fails → B, C, D all skipped."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("d", depends_on=["b", "c"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.FAILED,
            "b": TaskStatus.PENDING,
            "c": TaskStatus.PENDING,
            "d": TaskStatus.PENDING,
        }
        skipped = skip_dependents(plan, statuses, "a")
        self.assertEqual(set(skipped), {"b", "c", "d"})
        self.assertEqual(statuses["b"], TaskStatus.SKIPPED)
        self.assertEqual(statuses["c"], TaskStatus.SKIPPED)
        self.assertEqual(statuses["d"], TaskStatus.SKIPPED)

    def test_done_tasks_not_skipped(self):
        """Already-done tasks are not skipped."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.FAILED, "b": TaskStatus.DONE}
        skipped = skip_dependents(plan, statuses, "a")
        self.assertEqual(skipped, [])
        self.assertEqual(statuses["b"], TaskStatus.DONE)

    def test_already_failed_not_reskipped(self):
        """Already-failed tasks are not re-skipped (not added to skipped list)."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["b"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.FAILED,
            "b": TaskStatus.FAILED,
            "c": TaskStatus.PENDING,
        }
        skipped = skip_dependents(plan, statuses, "a")
        # b is already failed, so not re-skipped. c is reachable transitively.
        self.assertNotIn("b", skipped)
        self.assertIn("c", skipped)
        self.assertEqual(statuses["b"], TaskStatus.FAILED)  # unchanged
        self.assertEqual(statuses["c"], TaskStatus.SKIPPED)

    def test_no_dependents(self):
        """Failed task with no dependents → empty list."""
        tasks = [_task("a"), _task("b")]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.FAILED, "b": TaskStatus.PENDING}
        skipped = skip_dependents(plan, statuses, "a")
        self.assertEqual(skipped, [])
        self.assertEqual(statuses["b"], TaskStatus.PENDING)  # unrelated


# ============================================================
# reset_ready_skipped
# ============================================================


class TestResetReadySkipped(unittest.TestCase):
    """Tests for reset_ready_skipped."""

    def test_single_skipped_reset(self):
        """Skipped task with all deps done → reset to pending."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.DONE, "b": TaskStatus.SKIPPED}
        reset = reset_ready_skipped(plan, statuses)
        self.assertEqual(reset, ["b"])
        self.assertEqual(statuses["b"], TaskStatus.PENDING)

    def test_chain_stabilization(self):
        """Resetting B unblocks C (chain: A→B→C, both B and C skipped)."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["b"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.DONE,
            "b": TaskStatus.SKIPPED,
            "c": TaskStatus.SKIPPED,
        }
        reset = reset_ready_skipped(plan, statuses)
        # Both should be reset: B first (deps met), then C (B now pending → but
        # wait, C depends on B which is now PENDING not DONE, so C should NOT reset yet)
        # Actually: B gets reset to PENDING (its dep A is DONE). C depends on B which
        # is now PENDING (not DONE), so C stays SKIPPED.
        # BUT the function resets skipped→pending when deps are DONE. After B is reset
        # to PENDING, B's status is PENDING, not DONE. C depends on B being DONE.
        # So only B should be reset.
        #
        # Wait, re-read the function: it iterates until no changes. B gets reset because
        # A is DONE. Then it loops again: C depends on B, B is PENDING (not DONE), so C
        # is NOT reset. That's correct.
        self.assertEqual(reset, ["b"])
        self.assertEqual(statuses["b"], TaskStatus.PENDING)
        self.assertEqual(statuses["c"], TaskStatus.SKIPPED)

    def test_chain_full_unblock(self):
        """When all intermediate deps are done, the whole chain resets.
        A→B→C, all done except B and C are skipped but A and B are done.
        Actually: A done, B skipped, C skipped. B depends on A (done) → reset.
        But C needs B done, and B just got reset to pending, not done.
        So for full chain unblock: A done, B done, C skipped → C resets."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["b"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.DONE,
            "b": TaskStatus.DONE,
            "c": TaskStatus.SKIPPED,
        }
        reset = reset_ready_skipped(plan, statuses)
        self.assertEqual(reset, ["c"])
        self.assertEqual(statuses["c"], TaskStatus.PENDING)

    def test_no_reset_when_deps_not_met(self):
        """Skipped task whose dep is still failed → not reset."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.FAILED, "b": TaskStatus.SKIPPED}
        reset = reset_ready_skipped(plan, statuses)
        self.assertEqual(reset, [])
        self.assertEqual(statuses["b"], TaskStatus.SKIPPED)

    def test_no_reset_pending_tasks(self):
        """Only SKIPPED tasks are reset, not PENDING."""
        tasks = [_task("a"), _task("b", depends_on=["a"])]
        plan = _plan(tasks)
        statuses = {"a": TaskStatus.DONE, "b": TaskStatus.PENDING}
        reset = reset_ready_skipped(plan, statuses)
        self.assertEqual(reset, [])

    def test_diamond_partial_reset(self):
        """Diamond: A→{B,C}→D. A done, B skipped, C skipped, D skipped.
        B and C have deps met (A done), so they reset.
        D depends on B and C — but B and C are now PENDING, not DONE → D stays skipped."""
        tasks = [
            _task("a"),
            _task("b", depends_on=["a"]),
            _task("c", depends_on=["a"]),
            _task("d", depends_on=["b", "c"]),
        ]
        plan = _plan(tasks)
        statuses = {
            "a": TaskStatus.DONE,
            "b": TaskStatus.SKIPPED,
            "c": TaskStatus.SKIPPED,
            "d": TaskStatus.SKIPPED,
        }
        reset = reset_ready_skipped(plan, statuses)
        self.assertEqual(set(reset), {"b", "c"})
        self.assertEqual(statuses["b"], TaskStatus.PENDING)
        self.assertEqual(statuses["c"], TaskStatus.PENDING)
        self.assertEqual(statuses["d"], TaskStatus.SKIPPED)


# ============================================================
# resolve_task_model
# ============================================================


class TestResolveTaskModel(unittest.TestCase):
    """Tests for resolve_task_model."""

    def _config(self, implement: str | None = None) -> WorkflowConfig:
        return WorkflowConfig(model=ModelConfig(implement=implement))

    def test_cli_model_wins(self):
        """cli_model overrides everything."""
        task = _task("a", model="task-model")
        plan = _plan([task], default_model="plan-model")
        config = self._config(implement="config-model")
        model, source = resolve_task_model(task, plan, config, cli_model="cli-model")
        self.assertEqual(model, "cli-model")
        self.assertEqual(source, "cli")

    def test_task_model_wins_over_plan(self):
        """task.model wins over plan.defaultModel and config."""
        task = _task("a", model="task-model")
        plan = _plan([task], default_model="plan-model")
        config = self._config(implement="config-model")
        model, source = resolve_task_model(task, plan, config)
        self.assertEqual(model, "task-model")
        self.assertEqual(source, "task")

    def test_plan_default_model_wins_over_config(self):
        """plan.defaultModel wins over config.model.implement."""
        task = _task("a")
        plan = _plan([task], default_model="plan-model")
        config = self._config(implement="config-model")
        model, source = resolve_task_model(task, plan, config)
        self.assertEqual(model, "plan-model")
        self.assertEqual(source, "plan")

    def test_config_model_as_fallback(self):
        """config.model.implement used when nothing else set."""
        task = _task("a")
        plan = _plan([task])
        config = self._config(implement="config-model")
        model, source = resolve_task_model(task, plan, config)
        self.assertEqual(model, "config-model")
        self.assertEqual(source, "config")

    def test_none_when_nothing_set(self):
        """Returns (None, 'default') when nothing configured."""
        task = _task("a")
        plan = _plan([task])
        config = self._config()
        model, source = resolve_task_model(task, plan, config)
        self.assertIsNone(model)
        self.assertEqual(source, "default")

    def test_cli_model_none_falls_through(self):
        """cli_model=None doesn't count as set — falls to next level."""
        task = _task("a", model="task-model")
        plan = _plan([task])
        config = self._config()
        model, source = resolve_task_model(task, plan, config, cli_model=None)
        self.assertEqual(model, "task-model")
        self.assertEqual(source, "task")


if __name__ == "__main__":
    unittest.main()
