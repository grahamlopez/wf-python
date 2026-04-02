"""Tests for wflib.brief — task brief assembly from plan + completed results."""

import unittest

from wflib.brief import assemble_task_brief
from wflib.types import Plan, Task, TaskResult, TaskStatus, Usage


class TestAssembleTaskBrief(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_includes_context(self):
        """Brief includes the plan's context section."""

    @unittest.skip("Phase 1")
    def test_includes_file_hints(self):
        """Brief includes the task's files as starting hints."""

    @unittest.skip("Phase 1")
    def test_includes_constraints(self):
        """Brief includes the task's constraints."""

    @unittest.skip("Phase 1")
    def test_includes_acceptance_criteria(self):
        """Brief includes the task's acceptance criteria."""

    @unittest.skip("Phase 1")
    def test_includes_goal(self):
        """Brief includes the task's goal."""

    @unittest.skip("Phase 1")
    def test_includes_prior_work_summary(self):
        """Brief includes summaries from completed dependency tasks."""

    @unittest.skip("Phase 1")
    def test_prior_work_includes_diff_stat(self):
        """Prior work section includes diff stats from completed deps."""

    @unittest.skip("Phase 1")
    def test_no_prior_work_when_no_deps(self):
        """Brief omits prior work section when task has no dependencies."""

    @unittest.skip("Phase 1")
    def test_includes_skills_hint(self):
        """Brief includes skill name hints when task.skills is set."""

    @unittest.skip("Phase 1")
    def test_ends_with_report_result_instruction(self):
        """Brief ends with instruction to call report_result."""

    @unittest.skip("Phase 1")
    def test_excludes_other_tasks(self):
        """Brief does not include information about unrelated tasks."""


if __name__ == "__main__":
    unittest.main()
