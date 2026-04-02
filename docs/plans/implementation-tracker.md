# `wf` Implementation Tracker

Tracks progress across all implementation phases. See `wf-spec.md` for the full specification and `impl-strategy.md` for the phasing rationale.

---

## Phase Status

| Phase | Description | Status | Tasks | Notes |
|-------|-------------|--------|-------|-------|
| 0 | Scaffold | **complete** | 7 | Directory structure, type stubs, module stubs, schema, test infra, fixtures, placeholder tests |
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
**Completed:** 2026-04-02

**Intentional deviations (approved):**

1. **`pytest.ini` added** — Not in the original spec or strategy docs. Provides test runner configuration (`testpaths = tests`). Minor convenience addition.
2. **Module stubs for all ~20 modules (task-5)** — The strategy doc only specifies `types.py` stubs. We expanded Phase 0 to create minimal stub files (function signatures raising `NotImplementedError`, fully-defined dataclasses) for every Python module in `wflib/`, `profiles/`, and `adapters/`. This is required to satisfy the "imports succeed, zero import errors" acceptance criterion — placeholder tests in task-7 import from their target modules at the top level as an import-chain verification.
3. **All 9 E2E fixtures created** — Strategy says "at least `simple-split/`, `diamond-deps/`, `task-failure/`" (3 minimum). Owner directed "keep everything together in phase 0 — all tests should run (red)."
4. **`unittest.skip` chosen over `pytest.mark.skip`** — Both listed as options in the strategy doc. Chose `unittest.skip` because the spec says "No external test dependencies" and tests should be runnable via `python3 -m unittest discover tests/`. `pytest.mark.skip` would require pytest to be installed for the import to succeed.

**Lessons learned:**

- **Missing `.gitignore` caused merge conflicts.** Subagents ran Python to verify their work, generating `__pycache__/` directories that got committed. These binary files then conflicted during worktree merge-back. Fix: added `.gitignore` excluding `__pycache__/`, `*.pyc`, `.pytest_cache/`. This should be part of any Phase 0 scaffold in future projects.
- **Fixture repo test files get collected by pytest.** The mini Python projects inside `tests/e2e/fixtures/*/repo/tests/` were picked up by pytest's test discovery, causing import errors (their `from src.app import ...` doesn't resolve). Fix: added `norecursedirs = tests/e2e/fixtures` to `pytest.ini`.
- **task-4 merge conflict required manual resolution.** The conflict was entirely in `.pyc` files, not source code. After adding `.gitignore` and cleaning the cache files from both sides, the task-4 source files were copied directly to main. The orphaned worktree was cleaned up.
- **conftest.py correctly uses pytest.** The `tests/e2e/conftest.py` imports pytest for fixtures (`@pytest.fixture`, `monkeypatch`). This is expected — conftest files are pytest-specific infrastructure. The stdlib compatibility constraint (unittest.skip, unittest.TestCase) applies to the test files themselves, not to conftest.
- **Post-review fixes landed early.** Added required repo directories (`prompts/`, `templates/`, `tools/`), implemented help-topic aliasing, added `ImplementationEventType` validation, unified `_wf_dir` helper, and corrected CLI arg parsing in `tests/util.py`.

**Spec adjustments:** None needed.

---

### Phase 1 — Pure Foundation

**Planned scope:** types.py (full impl), validate.py, config.py, brief.py, render.py, templates.py + all unit tests

**Acceptance criteria:** All `tests/unit/` pass

**Review findings to address:**
- **Finding #4:** `set_config_value` `path` param needs clear implementation — `path` is the project root directory used to locate `.wf/config.toml`, not a dotted config path or file path

**Resolved early:**
- **Finding #3:** `ImplementationEvent.event` now uses `ImplementationEventType` with runtime validation (implemented ahead of Phase 1)

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

**Review findings to address:**
- **Finding #9:** `RunnerProfile` import was fixed in Phase 0 cleanup, but the real implementation in `task_executor.py` needs to wire up the profile protocol properly

**Resolved early:**
- **Finding #5:** Shared `_wf_dir` helper added to `profiles/__init__.py`, profiles now delegate to it

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 4 — Orchestration + CLI

**Planned scope:** scheduler.py, task_executor.py, review.py, bin/wf (full argparse), help.py, completions.py + E2E tests

**Acceptance criteria:** All `tests/e2e/` pass, `wf help` works

**Review findings to address:**
- **Finding #8:** `ReviewRecord` import was fixed in Phase 0, but `execute_fixup` is still a stub — needs real implementation
- **Finding #10:** E2E tests use `unittest.TestCase` but `conftest.py` provides pytest fixtures (`@pytest.fixture`, `monkeypatch`) — need to reconcile by converting E2E tests to pytest functions or wrapping fixtures for unittest compatibility
- **Finding #6:** crash-recovery fixture `_comment` added in Phase 0, but the E2E test setup must actually create pre-crash state where all tasks were running (none completed), then verify all reset to pending
- **Finding #7:** `scheduler.py` → `render.py` cross-module import comment added in Phase 0 — implement `ExecutionSummary` with `UsageRow` integration per spec

**Resolved early:**
- **Finding #13:** `bin/wf` now aliases no-args to `wf help topics` and `wf help` routes to the help module

**Started:** —
**Completed:** —
**Lessons learned:** —
**Spec adjustments:** —

---

### Phase 5 — Tools + Prompts + Pi Wrapper

**Planned scope:** Pi tool extensions (TS), MCP server, all system prompts, shipped templates, pi wrapper index.ts

**Acceptance criteria:** Tools validate-and-return, prompts ported, wrapper delegates to CLI

**Review findings to address:**
- (none)

**Resolved early:**
- **Finding #2:** Created `tools/`, `tools/pi_extensions/`, `prompts/`, `templates/` directories with placeholder files

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

Items from the Phase 0 code review are tracked in the per-phase `Review findings to address` sections above. Three minor items were fixed immediately in Phase 0 cleanup: `os.makedirs` guard in mock_agent.py (#1), `README.md` creation (#11), and `__pycache__` cleanup (#12).
