"""Tests for wflib.brief — task brief assembly from plan + completed results."""

import unittest

from wflib.brief import assemble_task_brief, _render_prior_work
from wflib.types import Plan, Task, TaskResult, TaskStatus, Usage


def _make_task(**overrides) -> Task:
    """Create a Task with sensible defaults, overridden by kwargs."""
    defaults = dict(
        id="task-1",
        title="Do the thing",
        goal="Implement the feature.",
        files=["src/foo.py", "tests/test_foo.py"],
        constraints=["Must not break existing API"],
        acceptance=["All tests pass", "No regressions"],
        depends_on=[],
        skills=None,
        model=None,
    )
    defaults.update(overrides)
    return Task(**defaults)


def _make_plan(tasks: list[Task] | None = None, **overrides) -> Plan:
    """Create a Plan with sensible defaults."""
    defaults = dict(
        goal="Refactor the codebase",
        context="This is a Python 3.12+ CLI tool for structured workflows.",
        tasks=tasks or [],
        default_model=None,
    )
    defaults.update(overrides)
    return Plan(**defaults)


def _make_result(**overrides) -> TaskResult:
    """Create a TaskResult with sensible defaults."""
    defaults = dict(
        status=TaskStatus.DONE,
        summary="Completed the work successfully.",
        diff_stat=" 2 files changed, 50 insertions(+), 10 deletions(-)",
        notes="",
    )
    defaults.update(overrides)
    return TaskResult(**defaults)


class TestAssembleTaskBrief(unittest.TestCase):
    def test_includes_context(self):
        """Brief includes the plan's context section."""
        task = _make_task()
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("## Context", brief)
        self.assertIn(plan.context, brief)

    def test_includes_file_hints(self):
        """Brief includes the task's files as starting hints."""
        task = _make_task(files=["src/alpha.py", "src/beta.py"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("## Relevant Files", brief)
        self.assertIn("`src/alpha.py`", brief)
        self.assertIn("`src/beta.py`", brief)

    def test_includes_constraints(self):
        """Brief includes the task's constraints."""
        task = _make_task(constraints=["No external deps", "Stdlib only"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("## Constraints", brief)
        self.assertIn("No external deps", brief)
        self.assertIn("Stdlib only", brief)

    def test_includes_acceptance_criteria(self):
        """Brief includes the task's acceptance criteria."""
        task = _make_task(acceptance=["Tests pass", "Coverage > 90%"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("## Done When", brief)
        self.assertIn("Tests pass", brief)
        self.assertIn("Coverage > 90%", brief)

    def test_includes_goal(self):
        """Brief includes the task's goal."""
        task = _make_task(goal="Rewrite the parser for correctness.")
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("## Goal", brief)
        self.assertIn("Rewrite the parser for correctness.", brief)

    def test_includes_prior_work_summary(self):
        """Brief includes summaries from completed dependency tasks."""
        dep_result = _make_result(
            summary="Extracted token module with visitor-based validation.",
        )
        task = _make_task(depends_on=["task-0"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {"task-0": dep_result})
        self.assertIn("## Prior Work", brief)
        self.assertIn("task-0", brief)
        self.assertIn("Extracted token module with visitor-based validation.", brief)

    def test_prior_work_includes_diff_stat(self):
        """Prior work section includes diff stats from completed deps."""
        dep_result = _make_result(
            diff_stat=" 3 files changed, 120 insertions(+), 45 deletions(-)",
        )
        task = _make_task(depends_on=["task-0"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {"task-0": dep_result})
        self.assertIn("3 files changed, 120 insertions(+), 45 deletions(-)", brief)

    def test_no_prior_work_when_no_deps(self):
        """Brief omits prior work section when task has no dependencies."""
        task = _make_task(depends_on=[])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertNotIn("## Prior Work", brief)

    def test_includes_skills_hint(self):
        """Brief includes skill name hints when task.skills is set."""
        task = _make_task(skills=["debugging", "refactoring"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("## Skills", brief)
        self.assertIn(
            "These skills may be useful: debugging, refactoring. "
            "Load them with the appropriate skill loading mechanism if needed.",
            brief,
        )

    def test_ends_with_report_result_instruction(self):
        """Brief ends with instruction to call report_result."""
        task = _make_task()
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertIn("report_result", brief)
        # The report_result section should be at the end
        last_h2_pos = brief.rfind("## ")
        self.assertIn("report_result", brief[last_h2_pos:])

    def test_excludes_other_tasks(self):
        """Brief does not include information about unrelated tasks."""
        task_a = _make_task(id="task-a", title="Task A", goal="Do A")
        task_b = _make_task(id="task-b", title="Task B", goal="Do B")
        task_c = _make_task(id="task-c", title="Target task", goal="Do C", depends_on=[])
        plan = _make_plan(tasks=[task_a, task_b, task_c])
        brief = assemble_task_brief(task_c, plan, {})
        # Should not mention other tasks
        self.assertNotIn("Task A", brief)
        self.assertNotIn("Task B", brief)
        self.assertNotIn("task-a", brief)
        self.assertNotIn("task-b", brief)
        # Should include its own info
        self.assertIn("Target task", brief)
        self.assertIn("Do C", brief)

    def test_title_in_heading(self):
        """Brief starts with the task title as an H1 heading."""
        task = _make_task(title="Extract token module")
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertTrue(brief.startswith("# Task: Extract token module"))

    def test_prior_work_only_done_deps(self):
        """Prior work only includes completed (done) dependencies, not failed/pending."""
        done_result = _make_result(summary="This was done.")
        failed_result = _make_result(status=TaskStatus.FAILED, summary="This failed.")
        pending_result = _make_result(status=TaskStatus.PENDING, summary="Still pending.")
        task = _make_task(depends_on=["dep-done", "dep-failed", "dep-pending"])
        plan = _make_plan(tasks=[task])
        results = {
            "dep-done": done_result,
            "dep-failed": failed_result,
            "dep-pending": pending_result,
        }
        brief = assemble_task_brief(task, plan, results)
        self.assertIn("dep-done", brief)
        self.assertIn("This was done.", brief)
        self.assertNotIn("dep-failed", brief)
        self.assertNotIn("This failed.", brief)
        self.assertNotIn("dep-pending", brief)
        self.assertNotIn("Still pending.", brief)

    def test_no_skills_section_when_skills_none(self):
        """Brief omits skills section when task.skills is None."""
        task = _make_task(skills=None)
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertNotIn("## Skills", brief)

    def test_no_skills_section_when_skills_empty(self):
        """Brief omits skills section when task.skills is empty list."""
        task = _make_task(skills=[])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertNotIn("## Skills", brief)

    def test_prior_work_includes_notes(self):
        """Prior work section includes notes from completed deps when present."""
        dep_result = _make_result(
            summary="Did the thing.",
            notes="Watch out for edge case in parser.",
        )
        task = _make_task(depends_on=["task-0"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {"task-0": dep_result})
        self.assertIn("Watch out for edge case in parser.", brief)

    def test_section_order(self):
        """Brief sections appear in the correct order."""
        dep_result = _make_result(summary="Prior work done.")
        task = _make_task(
            depends_on=["dep-1"],
            skills=["debugging"],
        )
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {"dep-1": dep_result})

        # Find positions of each section heading
        ctx_pos = brief.index("## Context")
        files_pos = brief.index("## Relevant Files")
        constraints_pos = brief.index("## Constraints")
        prior_pos = brief.index("## Prior Work")
        skills_pos = brief.index("## Skills")
        goal_pos = brief.index("## Goal")
        done_pos = brief.index("## Done When")
        report_pos = brief.index("## When You Are Done")

        self.assertLess(ctx_pos, files_pos)
        self.assertLess(files_pos, constraints_pos)
        self.assertLess(constraints_pos, prior_pos)
        self.assertLess(prior_pos, skills_pos)
        self.assertLess(skills_pos, goal_pos)
        self.assertLess(goal_pos, done_pos)
        self.assertLess(done_pos, report_pos)

    def test_multiple_deps_all_included(self):
        """Multiple completed dependencies are all included in prior work."""
        results = {
            "dep-1": _make_result(summary="First dep done."),
            "dep-2": _make_result(summary="Second dep done."),
        }
        task = _make_task(depends_on=["dep-1", "dep-2"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, results)
        self.assertIn("dep-1", brief)
        self.assertIn("First dep done.", brief)
        self.assertIn("dep-2", brief)
        self.assertIn("Second dep done.", brief)

    def test_dep_not_in_results_is_skipped(self):
        """Dependencies not present in results dict are silently skipped."""
        task = _make_task(depends_on=["dep-missing"])
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        # Should not crash, and should not have prior work section
        self.assertNotIn("## Prior Work", brief)

    def test_brief_ends_with_newline(self):
        """Brief text ends with a trailing newline."""
        task = _make_task()
        plan = _make_plan(tasks=[task])
        brief = assemble_task_brief(task, plan, {})
        self.assertTrue(brief.endswith("\n"))


class TestRenderPriorWork(unittest.TestCase):
    def test_empty_when_no_deps(self):
        """Returns empty string when task has no dependencies."""
        task = _make_task(depends_on=[])
        result = _render_prior_work(task, {})
        self.assertEqual(result, "")

    def test_empty_when_no_done_deps(self):
        """Returns empty string when no dependencies are done."""
        task = _make_task(depends_on=["dep-1"])
        results = {"dep-1": _make_result(status=TaskStatus.FAILED)}
        result = _render_prior_work(task, results)
        self.assertEqual(result, "")

    def test_formats_completed_dep(self):
        """Formats a completed dependency with summary and diff stat."""
        task = _make_task(depends_on=["dep-1"])
        dep = _make_result(
            summary="Implemented the module.",
            diff_stat=" 2 files changed, 30 insertions(+), 5 deletions(-)",
        )
        result = _render_prior_work(task, {"dep-1": dep})
        self.assertIn("dep-1", result)
        self.assertIn("Implemented the module.", result)
        self.assertIn("2 files changed", result)

    def test_no_diff_stat_omitted(self):
        """Diff stat block is omitted when diff_stat is None."""
        task = _make_task(depends_on=["dep-1"])
        dep = _make_result(summary="Done.", diff_stat=None)
        result = _render_prior_work(task, {"dep-1": dep})
        self.assertIn("Done.", result)
        self.assertNotIn("```", result)


if __name__ == "__main__":
    unittest.main()
