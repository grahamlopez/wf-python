"""Tests for wflib.record — create, load, save, atomic writes, phase transitions."""

import unittest

from wflib.record import (
    clear_active_resource,
    create_record,
    get_implementation_state,
    get_plan,
    get_total_usage,
    list_records,
    load_record,
    record_brainstorm,
    record_close,
    record_event,
    record_implementation_complete,
    record_implementation_start,
    record_plan,
    record_review,
    record_task_complete,
    record_task_start,
    save_record,
)


class TestCreateRecord(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_creates_file(self):
        """create_record writes docs/workflows/<name>.json."""

    @unittest.skip("Phase 2")
    def test_generates_workflow_id(self):
        """Created record has a non-empty workflow ID."""

    @unittest.skip("Phase 2")
    def test_initial_status_is_init(self):
        """Created record has status 'init'."""

    @unittest.skip("Phase 2")
    def test_raises_on_duplicate_name(self):
        """Raises if a record with the same name already exists."""

    @unittest.skip("Phase 2")
    def test_includes_config_snapshot(self):
        """Created record includes the provided WorkflowConfig."""


class TestLoadSaveRecord(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_round_trip(self):
        """save_record then load_record produces equivalent record."""

    @unittest.skip("Phase 2")
    def test_atomic_write(self):
        """save_record uses atomic write (tmp + rename)."""

    @unittest.skip("Phase 2")
    def test_load_missing_raises(self):
        """load_record raises FileNotFoundError for missing file."""

    @unittest.skip("Phase 2")
    def test_load_malformed_raises(self):
        """load_record raises ValueError for invalid JSON."""


class TestPhaseTransitions(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_record_brainstorm_sets_planning(self):
        """record_brainstorm sets status to 'planning'."""

    @unittest.skip("Phase 2")
    def test_record_plan_sets_implementing(self):
        """record_plan sets status to 'implementing'."""

    @unittest.skip("Phase 2")
    def test_record_implementation_complete_sets_reviewing(self):
        """record_implementation_complete sets status to 'reviewing'."""

    @unittest.skip("Phase 2")
    def test_record_close_sets_done(self):
        """record_close sets status to 'done'."""


class TestTaskTracking(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_record_task_start(self):
        """record_task_start marks task as running with timestamp."""

    @unittest.skip("Phase 2")
    def test_record_task_start_adds_active_resource(self):
        """record_task_start adds worktree to activeResources."""

    @unittest.skip("Phase 2")
    def test_record_task_complete(self):
        """record_task_complete stores TaskResult."""

    @unittest.skip("Phase 2")
    def test_clear_active_resource(self):
        """clear_active_resource removes worktree from activeResources."""


class TestEvents(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_record_event_appends(self):
        """record_event appends to implementation.events."""

    @unittest.skip("Phase 2")
    def test_event_has_timestamp(self):
        """Appended events have a timestamp."""


class TestQueryHelpers(unittest.TestCase):
    @unittest.skip("Phase 2")
    def test_get_plan_returns_plan(self):
        """get_plan extracts Plan from record with a plan phase."""

    @unittest.skip("Phase 2")
    def test_get_plan_returns_none(self):
        """get_plan returns None when no plan recorded."""

    @unittest.skip("Phase 2")
    def test_get_total_usage_aggregates(self):
        """get_total_usage sums across all phases."""


if __name__ == "__main__":
    unittest.main()
