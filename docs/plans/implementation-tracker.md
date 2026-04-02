# `wf` Implementation Tracker

Tracks progress across all implementation phases. See `wf-spec.md` for the full specification and `impl-strategy.md` for the phasing rationale.

---

## Phase Status

| Phase | Description | Status | Tasks | Notes |
|-------|-------------|--------|-------|-------|
| 0 | Scaffold | **submitted** | 7 | Directory structure, type stubs, module stubs, schema, test infra, fixtures, placeholder tests |
| 1 | Pure Foundation | not started | — | types, validate, config, brief, render, templates + unit tests |
| 2 | Git/IO Layer | not started | — | git, worktree, record, log + integration tests |
| 3 | Profiles + Runner | not started | — | profiles, adapters, runner, tmux + profile/adapter tests |
| 4 | Orchestration + CLI | not started | — | scheduler, task_executor, review, CLI, help, completions + E2E tests |
| 5 | Tools + Prompts + Pi Wrapper | not started | — | pi extensions, MCP server, prompts, templates, pi wrapper |

---

## Phase Log

### Phase 0 — Scaffold

**Planned scope:**
- Full directory tree per spec (all dirs, all `__init__.py`)
- `bin/wf` — shebang + minimal argparse skeleton
- `schemas/workflow.schema.json` — complete with all `$defs`
- `wflib/types.py` — all dataclasses fully defined, `from_dict`/`to_dict` as NotImplementedError stubs
- `tests/conftest.py` — tmp git repo fixture, mock-agent-on-PATH fixture
- `tests/e2e/mock_agent.py` — deterministic mock from spec
- `tests/e2e/fixtures/` — all fixture directories with `plan.json`, `scenario.json`, `expected/` stubs
- Placeholder test files for each module (importable, all fail/skip)

**Acceptance criteria:**
- `python3 -m pytest tests/` runs — imports succeed, all tests skip or fail (red baseline)
- `bin/wf --help` prints usage
- `python3 -c "from wflib import types"` succeeds

**Started:** 2026-04-02
**Completed:** —

**Intentional deviations (approved):**

1. **`pytest.ini` added** — Not in the original spec or strategy docs. Provides test runner configuration (`testpaths = tests`). Minor convenience addition.
2. **Module stubs for all ~20 modules (task-5)** — The strategy doc only specifies `types.py` stubs. We expanded Phase 0 to create minimal stub files (function signatures raising `NotImplementedError`, fully-defined dataclasses) for every Python module in `wflib/`, `profiles/`, and `adapters/`. This is required to satisfy the "imports succeed, zero import errors" acceptance criterion — placeholder tests in task-7 import from their target modules at the top level as an import-chain verification.
3. **All 9 E2E fixtures created** — Strategy says "at least `simple-split/`, `diamond-deps/`, `task-failure/`" (3 minimum). Owner directed "keep everything together in phase 0 — all tests should run (red)."
4. **`unittest.skip` chosen over `pytest.mark.skip`** — Both listed as options in the strategy doc. Chose `unittest.skip` because the spec says "No external test dependencies" and tests should be runnable via `python3 -m unittest discover tests/`. `pytest.mark.skip` would require pytest to be installed for the import to succeed.

**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 1 — Pure Foundation

**Planned scope:** types.py (full impl), validate.py, config.py, brief.py, render.py, templates.py + all unit tests

**Acceptance criteria:** All `tests/unit/` pass

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 2 — Git/IO Layer

**Planned scope:** git.py, worktree.py, record.py, log.py + integration tests

**Acceptance criteria:** All `tests/integration/` pass

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 3 — Profiles + Runner

**Planned scope:** Profile protocol + registry, pi.py, claude_code.py, mock.py, all adapters, runner.py, tmux.py + profile/adapter tests

**Acceptance criteria:** All `tests/unit/test_profiles.py`, `tests/profile/`, `tests/adapter/` pass

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 4 — Orchestration + CLI

**Planned scope:** scheduler.py, task_executor.py, review.py, bin/wf (full argparse), help.py, completions.py + E2E tests

**Acceptance criteria:** All `tests/e2e/` pass, `wf help` works

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 5 — Tools + Prompts + Pi Wrapper

**Planned scope:** Pi tool extensions (TS), MCP server, all system prompts, shipped templates, pi wrapper index.ts

**Acceptance criteria:** Tools validate-and-return, prompts ported, wrapper delegates to CLI

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

## Spec Adjustments

Issues discovered during implementation that required changes to the spec or deviations from it.

_(none yet)_

---

## Deferred Items

Items identified during implementation that are out of scope for the current phase but should be addressed later.

_(none yet)_
