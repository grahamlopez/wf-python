"""Data classes for all structures. JSON serialization/deserialization.

Schema validation against the JSON Schema files in schemas/.
All JSON I/O uses camelCase field names; Python dataclasses use snake_case.

This module is the dependency root — no other wflib module is imported here.
Serialization helpers (_dataclass_to_dict, _dict_to_dataclass) are used by
config.py and other modules for their own serialization needs.
"""

from __future__ import annotations

import json
import re
from dataclasses import MISSING, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import get_args, get_origin, get_type_hints


# --- camelCase / snake_case conversion helpers ---

def to_camel_case(key: str) -> str:
    """Convert a snake_case key to camelCase."""
    return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), key)


def to_snake_case(key: str) -> str:
    """Convert a camelCase key to snake_case."""
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', key).lower()


# --- Core plan types ---

@dataclass
class Task:
    id: str
    title: str
    goal: str
    files: list[str]
    constraints: list[str]
    acceptance: list[str]
    depends_on: list[str]
    skills: list[str] | None = None
    model: str | None = None


@dataclass
class Plan:
    goal: str
    context: str
    tasks: list[Task]
    default_model: str | None = None


# --- Usage tracking (same shape everywhere) ---

@dataclass
class Usage:
    model: str | None = None       # harness-reported model string, NOT normalized.
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    turns: int = 0


# --- Implementer result (tool-based, deterministic extraction) ---

@dataclass
class ReportResult:
    summary: str                               # what was accomplished (1-2 sentences)
    notes: str                                 # difficulties, surprises, things caller should know


# --- Task execution ---

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    status: TaskStatus
    started_at: str | None = None
    completed_at: str | None = None
    exit_code: int | None = None
    brief: str | None = None                   # full assembled prompt sent to subagent
    summary: str = ""                          # from report_result tool call (or fallback)
    files_changed: list[str] = field(default_factory=list)  # from git, not agent-reported
    diff_stat: str | None = None               # from git diff --stat in task worktree
    notes: str = ""                            # from report_result tool call (or empty)
    error: str | None = None                   # full error text, never truncated
    worktree_path: str | None = None           # where the task worktree was/is
    worktree_preserved: bool = False           # True if worktree kept for inspection
    session_file: str | None = None            # path to preserved session on failure
    usage: Usage = field(default_factory=Usage)


# --- Brainstorm ---

@dataclass
class DesignDecision:
    decision: str
    rationale: str


@dataclass
class BrainstormRecord:
    recorded_at: str
    motivation: str
    solution: str
    design_decisions: list[DesignDecision]
    usage: Usage


# --- Implementation ---

class ImplementationEventType(Enum):
    TASK_START = "taskStart"
    TASK_COMPLETE = "taskComplete"
    MERGE_START = "mergeStart"
    MERGE_COMPLETE = "mergeComplete"
    MERGE_FAILED = "mergeFailed"
    MERGE_RESOLVE_START = "mergeResolveStart"
    MERGE_RESOLVE_COMPLETE = "mergeResolveComplete"
    MERGE_RESOLVE_FAILED = "mergeResolveFailed"
    WORKTREE_CLEANUP = "worktreeCleanup"
    SKIP_DEPENDENTS = "skipDependents"
    CRASH_RECOVERY = "crashRecovery"
    ERROR = "error"


@dataclass
class ImplementationEvent:
    t: str                                     # ISO timestamp
    event: ImplementationEventType             # Validated via schema enum — see ImplementationEvent in workflow.schema.json
    task: str | None = None
    detail: str | None = None                  # extra context

    def __post_init__(self) -> None:
        if isinstance(self.event, ImplementationEventType):
            return
        if isinstance(self.event, str):
            try:
                self.event = ImplementationEventType(self.event)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid ImplementationEvent.event: {self.event}"
                ) from exc
        else:
            raise TypeError(
                "ImplementationEvent.event must be an ImplementationEventType or str"
            )


@dataclass
class ImplementationRecord:
    started_at: str | None = None
    completed_at: str | None = None
    base_commit: str | None = None
    active_resources: dict[str, str] = field(default_factory=dict)
    events: list[ImplementationEvent] = field(default_factory=list)
    tasks: dict[str, TaskResult] = field(default_factory=dict)


# --- Review ---

@dataclass
class ReviewRecord:
    recorded_at: str
    base_commit: str | None
    review_text: str
    findings_actionable: bool
    usage: Usage
    fixup_plan: Plan | None = None
    fixup_implementation: ImplementationRecord | None = None


# --- Workflow (top-level) ---

class WorkflowStatus(Enum):
    INIT = "init"
    BRAINSTORMING = "brainstorming"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    REVIEWING = "reviewing"
    CLOSING = "closing"
    DONE = "done"
    FAILED = "failed"


class AutomationLevel(Enum):
    INTERACTIVE = "interactive"    # user drives, confirms transitions
    SUPERVISED = "supervised"      # automatic but visible (tmux), user can intervene
    AUTOMATIC = "automatic"        # headless, no user interaction


@dataclass
class ModelConfig:
    brainstorm: str | None = None
    plan: str | None = None
    implement: str | None = None       # default for tasks; individual tasks can override
    review: str | None = None
    fixup: str | None = None
    close: str | None = None


@dataclass
class AutomationConfig:
    brainstorm: AutomationLevel = AutomationLevel.INTERACTIVE
    plan: AutomationLevel = AutomationLevel.INTERACTIVE
    implement: AutomationLevel = AutomationLevel.SUPERVISED
    review: AutomationLevel = AutomationLevel.AUTOMATIC
    close: AutomationLevel = AutomationLevel.AUTOMATIC


@dataclass
class ExecuteConfig:
    concurrency: int = 4
    worktrees: bool = True
    auto_review: bool = True


@dataclass
class UIConfig:
    auto_close: int = 30               # seconds; 0 = disabled
    tmux: bool = True


@dataclass
class AgentConfig:
    profile: str = "pi"             # runner profile name
    cmd: str | None = None           # override binary path


@dataclass
class ModelsConfig:
    """Model name aliases and per-profile harness mappings.

    aliases: user-defined shorthands -> canonical names.
    profiles: per-profile canonical -> harness-specific overrides.
    """
    aliases: dict[str, str] = field(default_factory=dict)
    profiles: dict[str, dict[str, str | None]] = field(default_factory=dict)


@dataclass
class WorkflowConfig:
    """Fully-resolved configuration snapshot. Captured at wf init time by
    merging: baked-in defaults < user config < project config < init flags.
    Stored in the record. All subsequent commands read from here.
    CLI flags on individual commands override for that invocation only."""
    model: ModelConfig = field(default_factory=ModelConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    execute: ExecuteConfig = field(default_factory=ExecuteConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)


@dataclass
class WorkflowMeta:
    id: str
    name: str
    created_at: str
    status: WorkflowStatus
    project: str
    source_branch: str
    source_commit: str
    worktree: str | None               # None = bare mode (main repo)
    config: WorkflowConfig = field(default_factory=WorkflowConfig)


@dataclass
class PlanRecord:
    recorded_at: str
    goal: str
    context: str
    default_model: str | None
    tasks: list[Task]
    usage: Usage


@dataclass
class CloseRecord:
    recorded_at: str
    merge_result: str                   # "clean" | "conflicted" | "failed"
    final_commit: str | None
    diff_stat: str


CURRENT_SCHEMA_VERSION = 1


@dataclass
class WorkflowRecord:
    workflow: WorkflowMeta
    schema_version: int = CURRENT_SCHEMA_VERSION
    brainstorm: BrainstormRecord | None = None
    plan: PlanRecord | None = None
    implementation: ImplementationRecord | None = None
    reviews: list[ReviewRecord] = field(default_factory=list)
    close: CloseRecord | None = None


# --- Public serialization API (used by config.py and other modules) ---

# Map of Python dataclass types to their enum fields for deserialization
_ENUM_TYPES = {
    TaskStatus,
    WorkflowStatus,
    AutomationLevel,
    ImplementationEventType,
}


def _is_optional(type_hint) -> bool:
    """Check if a type hint is X | None (Union[X, None])."""
    origin = get_origin(type_hint)
    if origin is type(int | str):  # types.UnionType for X | Y syntax
        args = get_args(type_hint)
        return type(None) in args
    return False


def _unwrap_optional(type_hint) -> type:
    """Get the inner type from X | None."""
    args = get_args(type_hint)
    non_none = [a for a in args if a is not type(None)]
    return non_none[0] if len(non_none) == 1 else type_hint


def _is_dataclass_type(cls) -> bool:
    """Check if a class is a dataclass."""
    return hasattr(cls, '__dataclass_fields__')


def _get_list_item_type(type_hint) -> type | None:
    """Get the item type from list[X]. Returns None if not a list type."""
    origin = get_origin(type_hint)
    if origin is list:
        args = get_args(type_hint)
        return args[0] if args else None
    return None


def _get_dict_types(type_hint) -> tuple[type, type] | None:
    """Get (key_type, value_type) from dict[K, V]. Returns None if not a dict."""
    origin = get_origin(type_hint)
    if origin is dict:
        args = get_args(type_hint)
        return (args[0], args[1]) if len(args) == 2 else None
    return None


def _dataclass_to_dict(obj, *, omit_none: bool = False) -> dict:
    """Serialize a dataclass instance to a camelCase dict.

    Handles nested dataclasses, enums, lists, dicts, and optional fields.
    When omit_none=False (default), None values are included as null.
    When omit_none=True, None optional fields are omitted from output.
    """
    if not _is_dataclass_type(type(obj)):
        raise TypeError(f"Expected a dataclass instance, got {type(obj)}")

    result = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        camel_key = to_camel_case(f.name)
        if omit_none and value is None:
            continue
        result[camel_key] = _serialize_value(value, omit_none=omit_none)
    return result


def _serialize_value(value, *, omit_none: bool = False):
    """Serialize a single value for JSON output."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if _is_dataclass_type(type(value)):
        return _dataclass_to_dict(value, omit_none=omit_none)
    if isinstance(value, list):
        return [_serialize_value(item, omit_none=omit_none) for item in value]
    if isinstance(value, dict):
        # Dict keys are data keys (task IDs, model aliases, profile names),
        # NOT field names — never apply camelCase conversion to them.
        # Field-name conversion is handled by _dataclass_to_dict.
        return {
            k: _serialize_value(v, omit_none=omit_none)
            for k, v in value.items()
        }
    return value


def _dict_to_dataclass(cls, data: dict):
    """Deserialize a camelCase dict into a dataclass instance.

    Handles nested dataclasses, enums, lists, dicts, and optional fields.
    Raises ValueError with clear messages on missing required fields.
    """
    if not _is_dataclass_type(cls):
        raise TypeError(f"Expected a dataclass type, got {cls}")

    hints = get_type_hints(cls)
    kwargs = {}

    for f in fields(cls):
        camel_key = to_camel_case(f.name)
        hint = hints[f.name]

        if camel_key in data:
            raw = data[camel_key]
            kwargs[f.name] = _deserialize_value(raw, hint)
        elif f.name in data:
            # Also accept snake_case keys (internal usage)
            raw = data[f.name]
            kwargs[f.name] = _deserialize_value(raw, hint)
        else:
            # Field not in data — check if it has a default or is nullable
            if _is_optional(hint):
                # Nullable fields default to None when absent
                kwargs[f.name] = None
            elif f.default is MISSING and f.default_factory is MISSING:
                # Truly required field with no default
                raise ValueError(
                    f"Missing required field '{camel_key}' for {cls.__name__}"
                )
            # Has a default value or default_factory — let dataclass handle it

    return cls(**kwargs)


def _deserialize_value(raw, hint):
    """Deserialize a single value according to its type hint."""
    # Handle Optional/nullable
    if _is_optional(hint):
        if raw is None:
            return None
        hint = _unwrap_optional(hint)

    if raw is None:
        return None

    # Enum types
    for enum_cls in _ENUM_TYPES:
        if hint is enum_cls:
            return enum_cls(raw)

    # Dataclass types
    if _is_dataclass_type(hint):
        if isinstance(raw, dict):
            return _dict_to_dataclass(hint, raw)
        return raw

    # list[X]
    item_type = _get_list_item_type(hint)
    if item_type is not None:
        if not isinstance(raw, list):
            return raw
        return [_deserialize_value(item, item_type) for item in raw]

    # dict[K, V]
    dict_types = _get_dict_types(hint)
    if dict_types is not None:
        if not isinstance(raw, dict):
            return raw
        key_type, val_type = dict_types
        result = {}
        for k, v in raw.items():
            # Dict keys are data keys (task IDs, alias names, profile names),
            # not dataclass field names — preserve them exactly as provided.
            # Only dataclass field names go through camelCase/snake_case conversion.
            py_key = k
            result[py_key] = _deserialize_value(v, val_type)
        return result

    # Primitive types (str, int, float, bool)
    return raw


# --- Serialization ---

def record_from_json(data: dict) -> WorkflowRecord:
    """Deserialize a dict (from JSON) into a WorkflowRecord.
    Reads schemaVersion from the record. If absent, assumes version 1.
    If the version is higher than CURRENT_SCHEMA_VERSION, raises with
    a clear message directing the user to upgrade wf.
    Ignores unknown top-level keys (forward-compatibility for records
    written by newer wf versions that this version can still partially read).
    """
    version = data.get("schemaVersion", 1)
    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Record schema version {version} is newer than supported "
            f"version {CURRENT_SCHEMA_VERSION}. Please upgrade wf."
        )

    # Filter to known fields only (forward-compat: ignore unknown top-level keys)
    known_fields = {to_camel_case(f.name) for f in fields(WorkflowRecord)}
    filtered = {k: v for k, v in data.items() if k in known_fields}

    return _dict_to_dataclass(WorkflowRecord, filtered)


def record_to_json(record: WorkflowRecord) -> dict:
    """Serialize a WorkflowRecord to a JSON-compatible dict (camelCase keys).
    Always writes schemaVersion as the first key.
    """
    d = _dataclass_to_dict(record)
    # Ensure schemaVersion is the first key
    result = {"schemaVersion": d.pop("schemaVersion", CURRENT_SCHEMA_VERSION)}
    result.update(d)
    return result


def plan_from_json(data: dict) -> Plan:
    """Deserialize a dict (from JSON) into a Plan."""
    errors = validate_schema(data, "plan")
    if errors:
        raise ValueError("Schema validation failed: " + "; ".join(errors))
    return _dict_to_dataclass(Plan, data)


def plan_to_json(plan: Plan) -> dict:
    """Serialize a Plan to a JSON-compatible dict (camelCase keys).
    Omits None optional fields (e.g. skills, model, defaultModel) for
    compatibility with the tool-call submission format.
    """
    return _dataclass_to_dict(plan, omit_none=True)


def validate_schema(data: dict, component: str | None = None) -> list[str]:
    """Validate data against the JSON Schema.

    Hand-rolled to avoid jsonschema dependency (which pulls in 4 transitive
    deps including a compiled Rust extension). Covers structural validation
    (required keys, types, refs, arrays, enums) — NOT full JSON Schema
    compliance. Sufficient for the tool-call validation use case.

    component=None validates full record, "plan"/"brainstorm"/etc. validates
    that $def. Returns list of errors; empty list = valid.
    """
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "workflow.schema.json"
    with open(schema_path) as f:
        full_schema = json.load(f)

    # Determine which schema/def to validate against
    component_map = {
        "plan": "Plan",
        "brainstorm": "Brainstorm",
        "task": "Task",
        "report-result": "ReportResult",
        "usage": "Usage",
    }

    if component is None:
        schema_def = full_schema
    else:
        def_name = component_map.get(component)
        if def_name is None:
            return [f"Unknown component: {component}"]
        defs = full_schema.get("$defs", {})
        schema_def = defs.get(def_name)
        if schema_def is None:
            return [f"Schema definition not found: {def_name}"]

    return _validate_against_schema(data, schema_def, full_schema.get("$defs", {}), "")


def _validate_against_schema(
    data, schema: dict, defs: dict, path: str
) -> list[str]:
    """Basic structural validation against a JSON Schema definition.

    Checks: required keys, correct types, array minItems, $ref resolution.
    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    # Resolve $ref
    if "$ref" in schema:
        ref = schema["$ref"]
        # Expected format: #/$defs/TypeName
        if ref.startswith("#/$defs/"):
            def_name = ref[len("#/$defs/"):]
            schema = defs.get(def_name, {})
        else:
            return errors  # Can't resolve, skip

    # Handle oneOf (nullable types)
    if "oneOf" in schema:
        if data is None:
            # Check if null is allowed
            if any(s.get("type") == "null" for s in schema["oneOf"]):
                return errors
            errors.append(f"{path or 'root'}: null not allowed")
            return errors
        # Try non-null schemas
        for sub in schema["oneOf"]:
            if sub.get("type") != "null":
                sub_errors = _validate_against_schema(data, sub, defs, path)
                if not sub_errors:
                    return []
        # If we got here, none matched. Use the first non-null errors.
        for sub in schema["oneOf"]:
            if sub.get("type") != "null":
                return _validate_against_schema(data, sub, defs, path)
        return errors

    expected_type = schema.get("type")

    # Type checking
    if expected_type == "object":
        if not isinstance(data, dict):
            errors.append(f"{path or 'root'}: expected object, got {type(data).__name__}")
            return errors

        # Check required fields
        for req in schema.get("required", []):
            if req not in data:
                prefix = f"{path}." if path else ""
                errors.append(f"{prefix}{req}: required field missing")

        # Validate properties
        props = schema.get("properties", {})
        for key, prop_schema in props.items():
            if key in data:
                child_path = f"{path}.{key}" if path else key
                errors.extend(
                    _validate_against_schema(data[key], prop_schema, defs, child_path)
                )

        additional = schema.get("additionalProperties", True)
        if additional is not True:
            for key, value in data.items():
                if key in props:
                    continue
                child_path = f"{path}.{key}" if path else key
                if additional is False:
                    errors.append(f"{child_path}: additional properties not allowed")
                elif isinstance(additional, dict):
                    errors.extend(
                        _validate_against_schema(value, additional, defs, child_path)
                    )

    elif expected_type == "array":
        if not isinstance(data, list):
            errors.append(f"{path or 'root'}: expected array, got {type(data).__name__}")
            return errors
        min_items = schema.get("minItems")
        if min_items is not None and len(data) < min_items:
            errors.append(
                f"{path or 'root'}: array must have at least {min_items} item(s), got {len(data)}"
            )
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                child_path = f"{path}[{i}]" if path else f"[{i}]"
                errors.extend(
                    _validate_against_schema(item, item_schema, defs, child_path)
                )

    elif expected_type == "string":
        if not isinstance(data, str):
            errors.append(f"{path or 'root'}: expected string, got {type(data).__name__}")
        # Check enum constraint
        enum_values = schema.get("enum")
        if enum_values is not None and data not in enum_values:
            errors.append(f"{path or 'root'}: value '{data}' not in {enum_values}")

    elif expected_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errors.append(f"{path or 'root'}: expected integer, got {type(data).__name__}")

    elif expected_type == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errors.append(f"{path or 'root'}: expected number, got {type(data).__name__}")

    elif expected_type == "boolean":
        if not isinstance(data, bool):
            errors.append(f"{path or 'root'}: expected boolean, got {type(data).__name__}")

    return errors


# --- Message extraction ---

def extract_tool_call(messages: list[dict], tool_name: str) -> dict | None:
    """Scan messages backwards for the last tool call matching tool_name.

    Returns the tool call's arguments dict, or None if not found.

    Looks for assistant messages containing a content block with
    type='toolCall' and name matching tool_name. Returns block['arguments'].
    """
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "toolCall"
                and block.get("name") == tool_name
            ):
                return block.get("arguments")
    return None
