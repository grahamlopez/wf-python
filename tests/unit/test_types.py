"""Tests for wflib.types — dataclass construction, serialization, tool call extraction."""

import unittest

from wflib.types import (
    AutomationConfig,
    AutomationLevel,
    BrainstormRecord,
    CloseRecord,
    DesignDecision,
    ExecuteConfig,
    ImplementationEvent,
    ImplementationRecord,
    ModelConfig,
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
    extract_tool_call,
    plan_from_json,
    plan_to_json,
    record_from_json,
    record_to_json,
    to_camel_case,
    to_snake_case,
)


class TestEnums(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_task_status_values(self):
        """TaskStatus enum has correct string values."""

    @unittest.skip("Phase 1")
    def test_workflow_status_values(self):
        """WorkflowStatus enum has correct string values."""

    @unittest.skip("Phase 1")
    def test_automation_level_values(self):
        """AutomationLevel enum has correct string values."""


class TestDataclassConstruction(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_plan_construction(self):
        """Plan can be constructed with required fields."""

    @unittest.skip("Phase 1")
    def test_task_construction_with_defaults(self):
        """Task optional fields default correctly (skills=None, model=None)."""

    @unittest.skip("Phase 1")
    def test_usage_defaults_to_zeros(self):
        """Usage() constructs with all zeros."""

    @unittest.skip("Phase 1")
    def test_workflow_config_defaults(self):
        """WorkflowConfig() constructs with all baked-in defaults."""

    @unittest.skip("Phase 1")
    def test_task_result_defaults(self):
        """TaskResult has correct defaults for optional fields."""

    @unittest.skip("Phase 1")
    def test_implementation_record_defaults(self):
        """ImplementationRecord defaults: empty events, empty tasks, empty active_resources."""

    @unittest.skip("Phase 1")
    def test_workflow_record_optional_phases(self):
        """WorkflowRecord brainstorm/plan/implementation/close default to None."""


class TestCamelSnakeConversion(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_to_camel_case(self):
        """snake_case converts to camelCase: default_model -> defaultModel."""

    @unittest.skip("Phase 1")
    def test_to_snake_case(self):
        """camelCase converts to snake_case: defaultModel -> default_model."""

    @unittest.skip("Phase 1")
    def test_round_trip_camel_snake(self):
        """to_camel_case(to_snake_case(x)) == x for known keys."""

    @unittest.skip("Phase 1")
    def test_single_word_unchanged(self):
        """Single words pass through unchanged in both directions."""


class TestFromDict(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_plan_from_json(self):
        """plan_from_json constructs Plan from camelCase dict."""

    @unittest.skip("Phase 1")
    def test_plan_from_json_with_tasks(self):
        """plan_from_json correctly deserializes nested Task objects."""

    @unittest.skip("Phase 1")
    def test_record_from_json_minimal(self):
        """record_from_json handles a minimal record (workflow only)."""

    @unittest.skip("Phase 1")
    def test_record_from_json_full(self):
        """record_from_json handles a full record with all phases populated."""

    @unittest.skip("Phase 1")
    def test_plan_from_json_missing_required_field(self):
        """plan_from_json raises on missing required field."""


class TestToDict(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_plan_to_json(self):
        """plan_to_json produces camelCase dict from Plan."""

    @unittest.skip("Phase 1")
    def test_record_to_json_round_trip(self):
        """record_to_json -> record_from_json produces equivalent record."""

    @unittest.skip("Phase 1")
    def test_plan_to_json_omits_none_optionals(self):
        """plan_to_json omits None optional fields (skills, model)."""


class TestExtractToolCall(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_extract_report_result(self):
        """extract_tool_call finds report_result in messages."""

    @unittest.skip("Phase 1")
    def test_extract_submit_plan(self):
        """extract_tool_call finds submit_plan in messages."""

    @unittest.skip("Phase 1")
    def test_extract_returns_none_when_not_found(self):
        """extract_tool_call returns None when tool not called."""

    @unittest.skip("Phase 1")
    def test_extract_finds_last_occurrence(self):
        """extract_tool_call returns the last matching tool call, not the first."""

    @unittest.skip("Phase 1")
    def test_extract_from_empty_messages(self):
        """extract_tool_call handles empty message list."""


if __name__ == "__main__":
    unittest.main()
