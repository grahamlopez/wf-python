"""E2E tests — failure scenarios: task failure, merge conflicts."""

import unittest


class TestTaskFailure(unittest.TestCase):
    """Task-2 fails (exitCode 1), task-3 depends on task-2."""

    @unittest.skip("Phase 4")
    def test_failed_task_status(self):
        """task-2 status is 'failed'."""

    @unittest.skip("Phase 4")
    def test_dependent_skipped(self):
        """task-3 status is 'skipped' (depends on failed task-2)."""

    @unittest.skip("Phase 4")
    def test_independent_tasks_done(self):
        """task-1 and task-4 (independent) reach 'done'."""

    @unittest.skip("Phase 4")
    def test_skip_dependents_event(self):
        """skipDependents event appears in timeline."""


class TestMergeConflict(unittest.TestCase):
    """Two parallel tasks edit the same line — auto-resolution succeeds."""

    @unittest.skip("Phase 4")
    def test_both_tasks_done(self):
        """Both tasks reach 'done' after resolution."""

    @unittest.skip("Phase 4")
    def test_merge_resolve_events(self):
        """mergeResolveStart and mergeResolveComplete events in timeline."""

    @unittest.skip("Phase 4")
    def test_final_file_content(self):
        """The conflicted file has the resolved content."""


class TestMergeConflictUnresolvable(unittest.TestCase):
    """Resolution agent fails — task marked failed, worktree preserved."""

    @unittest.skip("Phase 4")
    def test_task_failed(self):
        """The conflicting task is marked 'failed'."""

    @unittest.skip("Phase 4")
    def test_worktree_preserved(self):
        """worktreePreserved is True for the failed task."""

    @unittest.skip("Phase 4")
    def test_merge_resolve_failed_event(self):
        """mergeResolveFailed event in timeline."""

    @unittest.skip("Phase 4")
    def test_conflict_files_recorded(self):
        """Conflict file names are recorded in the error field."""


if __name__ == "__main__":
    unittest.main()
