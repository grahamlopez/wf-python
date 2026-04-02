"""Data classes for all structures. JSON serialization/deserialization.

Schema validation against the JSON Schema files in schemas/.
All JSON I/O uses camelCase field names; Python dataclasses use snake_case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


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

@dataclass
class ImplementationEvent:
    t: str                                     # ISO timestamp
    event: str                                 # Validated via schema enum — see ImplementationEvent in workflow.schema.json
    task: str | None = None
    detail: str | None = None                  # extra context


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


@dataclass
class WorkflowRecord:
    workflow: WorkflowMeta
    brainstorm: BrainstormRecord | None = None
    plan: PlanRecord | None = None
    implementation: ImplementationRecord | None = None
    reviews: list[ReviewRecord] = field(default_factory=list)
    close: CloseRecord | None = None


# --- Serialization ---

def record_from_json(data: dict) -> WorkflowRecord:
    """Deserialize a dict (from JSON) into a WorkflowRecord."""
    raise NotImplementedError("record_from_json: not yet implemented")


def record_to_json(record: WorkflowRecord) -> dict:
    """Serialize a WorkflowRecord to a JSON-compatible dict (camelCase keys)."""
    raise NotImplementedError("record_to_json: not yet implemented")


def plan_from_json(data: dict) -> Plan:
    """Deserialize a dict (from JSON) into a Plan."""
    raise NotImplementedError("plan_from_json: not yet implemented")


def plan_to_json(plan: Plan) -> dict:
    """Serialize a Plan to a JSON-compatible dict (camelCase keys)."""
    raise NotImplementedError("plan_to_json: not yet implemented")


def validate_schema(data: dict, component: str | None = None) -> list[str]:
    """Validate data against the JSON Schema.

    component=None validates full record, "plan"/"brainstorm"/etc. validates
    that $def. Returns list of errors; empty list = valid.
    """
    raise NotImplementedError("validate_schema: not yet implemented")


# --- Message extraction ---

def extract_tool_call(messages: list[dict], tool_name: str) -> dict | None:
    """Scan messages backwards for the last tool call matching tool_name.

    Returns the tool call's arguments dict, or None if not found.

    Looks for assistant messages containing a content block with
    type='toolCall' and name matching tool_name. Returns block['arguments'].
    """
    raise NotImplementedError("extract_tool_call: not yet implemented")
