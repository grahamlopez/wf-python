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
    # Structural checks (hard errors) first
    errors: list[str] = []
    errors.extend(_check_duplicate_ids(plan))
    errors.extend(_check_refs(plan))
    errors.extend(_check_cycles(plan))

    # Heuristic checks (warnings)
    warnings: list[str] = []
    warnings.extend(_check_empty_acceptance(plan))
    warnings.extend(_check_constraint_count(plan))
    warnings.extend(_check_empty_goal(plan))

    result = ValidationResult(errors=errors, warnings=warnings)

    if errors:
        raise ValueError(
            f"Plan validation failed with {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    return result


# --- Structural checks (hard errors) ---

def _check_refs(plan: Plan) -> list[str]:
    """Every dependsOn ID exists in plan.tasks."""
    task_ids = {t.id for t in plan.tasks}
    errors = []
    for task in plan.tasks:
        for dep_id in task.depends_on:
            if dep_id not in task_ids:
                errors.append(
                    f"Task '{task.id}' depends on '{dep_id}' which does not exist"
                )
    return errors


def _check_cycles(plan: Plan) -> list[str]:
    """DFS cycle detection on the dependency graph."""
    # Build adjacency: task -> list of tasks it depends on
    graph: dict[str, list[str]] = {}
    task_ids = {t.id for t in plan.tasks}
    for task in plan.tasks:
        # Only include deps that actually exist (avoid KeyError; _check_refs catches missing)
        graph[task.id] = [d for d in task.depends_on if d in task_ids]

    errors = []
    # States: 0 = unvisited, 1 = in current path, 2 = fully visited
    state: dict[str, int] = {tid: 0 for tid in graph}
    path: list[str] = []

    def dfs(node: str) -> None:
        state[node] = 1
        path.append(node)
        for dep in graph[node]:
            if state[dep] == 1:
                # Found a cycle - extract the cycle from path
                cycle_start = path.index(dep)
                cycle = path[cycle_start:]
                cycle_str = " -> ".join(cycle + [cycle[0]])
                errors.append(f"Dependency cycle detected: {cycle_str}")
            elif state[dep] == 0:
                dfs(dep)
        path.pop()
        state[node] = 2

    for tid in graph:
        if state[tid] == 0:
            dfs(tid)

    return errors


# --- Heuristic checks (warnings) ---

def _check_empty_acceptance(plan: Plan) -> list[str]:
    """Warn if any task has zero acceptance criteria."""
    warnings = []
    for task in plan.tasks:
        if not task.acceptance:
            warnings.append(
                f"Task '{task.id}' has no acceptance criteria"
            )
    return warnings


def _check_constraint_count(plan: Plan, threshold: int = 6) -> list[str]:
    """Warn if any task has more than `threshold` constraints."""
    warnings = []
    for task in plan.tasks:
        if len(task.constraints) > threshold:
            warnings.append(
                f"Task '{task.id}' has {len(task.constraints)} constraints "
                f"(threshold: {threshold})"
            )
    return warnings


def _check_empty_goal(plan: Plan) -> list[str]:
    """Warn if any task has an empty or very short goal."""
    warnings = []
    for task in plan.tasks:
        if len(task.goal.strip()) < 10:
            warnings.append(
                f"Task '{task.id}' has an empty or very short goal"
            )
    return warnings


def _check_duplicate_ids(plan: Plan) -> list[str]:
    """Hard error: task IDs must be unique."""
    errors = []
    seen: set[str] = set()
    for task in plan.tasks:
        if task.id in seen:
            errors.append(f"Duplicate task ID: '{task.id}'")
        seen.add(task.id)
    return errors
