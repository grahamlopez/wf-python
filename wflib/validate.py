"""Pure validation. No I/O.

Combines structural checks (deps, cycles) with mechanical heuristic checks
derived from the task-decomposition skill.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wflib.types import Plan


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)     # hard errors — plan is invalid
    warnings: list[str] = field(default_factory=list)   # heuristic warnings — plan is valid but suspect


def validate_plan(plan: Plan) -> ValidationResult:
    """Full validation: structural checks + heuristic checks.
    Raises ValueError on hard errors.
    Returns ValidationResult for callers who want warnings too.
    """
    raise NotImplementedError("validate_plan: not yet implemented")


# --- Structural checks (hard errors) ---

def _check_refs(plan: Plan) -> list[str]:
    """Every dependsOn ID exists in plan.tasks."""
    raise NotImplementedError("_check_refs: not yet implemented")


def _check_cycles(plan: Plan) -> list[str]:
    """DFS cycle detection on the dependency graph."""
    raise NotImplementedError("_check_cycles: not yet implemented")


# --- Heuristic checks (warnings) ---

def _check_empty_acceptance(plan: Plan) -> list[str]:
    """Warn if any task has zero acceptance criteria."""
    raise NotImplementedError("_check_empty_acceptance: not yet implemented")


def _check_constraint_count(plan: Plan, threshold: int = 6) -> list[str]:
    """Warn if any task has more than `threshold` constraints."""
    raise NotImplementedError("_check_constraint_count: not yet implemented")


def _check_empty_goal(plan: Plan) -> list[str]:
    """Warn if any task has an empty or very short goal."""
    raise NotImplementedError("_check_empty_goal: not yet implemented")


def _check_duplicate_ids(plan: Plan) -> list[str]:
    """Hard error: task IDs must be unique."""
    raise NotImplementedError("_check_duplicate_ids: not yet implemented")
