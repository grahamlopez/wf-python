"""Tests for wflib.validate — plan validation: deps, cycles, heuristic warnings."""

import unittest

from wflib.validate import ValidationResult, validate_plan
from wflib.types import Plan, Task


class TestStructuralChecks(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_valid_plan_passes(self):
        """A well-formed plan with valid deps returns no errors."""

    @unittest.skip("Phase 1")
    def test_missing_dep_ref(self):
        """dependsOn referencing a non-existent task ID is a hard error."""

    @unittest.skip("Phase 1")
    def test_cycle_detection_simple(self):
        """A->B->A cycle is detected as a hard error."""

    @unittest.skip("Phase 1")
    def test_cycle_detection_transitive(self):
        """A->B->C->A cycle is detected."""

    @unittest.skip("Phase 1")
    def test_duplicate_ids(self):
        """Duplicate task IDs are a hard error."""

    @unittest.skip("Phase 1")
    def test_self_dependency(self):
        """A task depending on itself is a cycle error."""


class TestHeuristicWarnings(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_empty_acceptance_warns(self):
        """Tasks with zero acceptance criteria produce a warning."""

    @unittest.skip("Phase 1")
    def test_high_constraint_count_warns(self):
        """Tasks with >6 constraints produce a warning."""

    @unittest.skip("Phase 1")
    def test_empty_goal_warns(self):
        """Tasks with empty or very short goal produce a warning."""

    @unittest.skip("Phase 1")
    def test_normal_plan_no_warnings(self):
        """A well-formed plan with reasonable sizes produces no warnings."""


class TestValidationResult(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_errors_and_warnings_separate(self):
        """A plan can have warnings without errors (valid but suspect)."""

    @unittest.skip("Phase 1")
    def test_errors_mean_invalid(self):
        """A plan with errors is invalid regardless of warnings."""


if __name__ == "__main__":
    unittest.main()
