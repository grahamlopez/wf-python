# `wf` Implementation Tracker

Tracks progress across all implementation phases. See `wf-spec.md` for the full specification and `impl-strategy.md` for the phasing rationale.

---

## Phase Status

| Phase | Description | Status | Tasks | Notes |
|-------|-------------|--------|-------|-------|
| 0 | Scaffold | **complete** | 7 | Directory structure, type stubs, module stubs, schema, test infra, fixtures, placeholder tests |
| 1 | Pure Foundation | **complete** | 6 | types, validate, config, brief, render, templates + unit tests |
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

**Started:** 2026-04-02
**Completed:** 2026-04-02

**Implementation summary (219 tests passing, 0 skips in Phase 1 scope):**
- `types.py` (700 lines): Full serialization (record_from_json, record_to_json, plan_from_json, plan_to_json, extract_tool_call, validate_schema) + generic helpers (_dataclass_to_dict, _dict_to_dataclass). 60 tests.
- `validate.py` (159 lines): Structural checks (refs, cycles, duplicate IDs) + heuristic warnings (empty acceptance, constraint count, empty goal). ValidationError subclass. 31 tests.
- `config.py` (716 lines): TOML loading, deep-merge, 4-level resolution, apply_cli_overrides, set_config_value with comment preservation, show_resolved, show_with_origins. 57 tests.
- `brief.py` (102 lines): Task brief assembly with context, constraints, prior work, skills, report_result instruction. 24 tests.
- `render.py` (445 lines): Markdown rendering, usage tables, status formatting, plan rendering, execution summary, history table. 30 tests.
- `templates.py` (108 lines): Frontmatter parsing, template discovery (shipped + project override), variable substitution ($1, $@). 19 tests.

**Intentional deviations from spec:**

1. **`plan_to_json` omits None optional fields; `record_to_json` preserves them as null.** The spec doesn't explicitly distinguish, but the implementation uses `omit_none=True` for plan serialization (matching the tool-call submission format where absent = not specified) and `omit_none=False` for record serialization (matching the full record format where null is an explicit value). This is a deliberate design decision that makes both round-trip contracts work correctly.

2. **`_dict_to_dataclass` treats `X | None` fields without defaults as implicitly None when absent.** For fields like `WorkflowMeta.worktree` (typed `str | None` with no dataclass default), absent JSON keys default to `None` rather than raising. This is necessary because the JSON Schema marks these as optional (not in `required`), while the Python dataclass has no `= None` default. The spec's schema and types are slightly misaligned here; the implementation bridges them.

3. **`validate_plan` raises `ValidationError` (a new `ValueError` subclass) instead of plain `ValueError`.** The spec says "Raises ValueError on hard errors." The implementation preserves backward compatibility (it IS a ValueError) while also carrying warnings via `.result`. This is an improvement over the spec's contract — callers catching `ValueError` still work, but callers catching `ValidationError` get access to warnings even when validation fails.

4. **Skills hint text is harness-agnostic instead of pi-specific.** The spec says: `"These skills may be useful: X, Y. Load them with /skill:<name> if needed."` The implementation says: `"These skills may be useful: X, Y. Load them with the appropriate skill loading mechanism if needed."` This matches wf's harness-neutral design — `/skill:<name>` is pi-specific syntax. The implementer.md prompt (Phase 5) can add harness-specific instructions if needed.

5. **`show_resolved` doesn't display the `models` section when empty.** The merge-format dict uses internal `_aliases`/`_profiles` sub-keys for the models section; when both are empty (the default), they flatten to nothing visible. Not a functional issue — `models` config round-trips correctly through `config_to_dict`/`config_from_dict`. Cosmetic display can be improved when the help/config display is polished in Phase 4.

6. **`brief.py` does not include the `toRelative` path conversion** from the migration map's guidance. The spec's migration map says to port this from `helpers.ts`. This is a path-relativization step ensuring file hints resolve against the worktree rather than the main repo. It's more relevant once worktrees are wired up (Phase 2), and can be added then. The brief assembly is otherwise complete and correct.

7. **`brief.py` does not include the load-bearing design comments** about WHY files are hints (not inlined), WHY goals (not steps), WHY constraints are facts. The migration map says to "port the code comments verbatim as docstrings." These are important for future maintainers/agents — they should be added when `prompts/implementer.md` is ported in Phase 5, as both the brief and the implementer prompt embody the same philosophy.

8. **`types.py` keeps serialization, schema validation, and message extraction in one file (700 lines).** The review flagged this as a mixed-concern file (finding #5). Decision: keep as-is for now with clear section headers. The alternative (splitting into `serde.py` + moving `validate_schema` elsewhere) would create more files without meaningful benefit at this scale. If `types.py` grows past ~900 lines in later phases, revisit.

**Review findings addressed (13 total):**

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| 1 | `_serialize_value` camelCase-converted dict data keys | Bug | Fixed: dict keys preserved as-is. Added 4 regression tests. |
| 2 | `_config_to_merge_dict` flattened aliases+profiles causing collisions | Bug | Fixed: structured `_aliases`/`_profiles` sub-dicts. Added collision test. |
| 3 | Duplicated validation logic (`_validate_values` vs `_validate_single_key_value`) | Duplication | Fixed: shared `_VALIDATION_RULES` registry + `_coerce_string_value`. |
| 4 | `validate_schema` missing rationale comment | Clarity | Fixed: docstring explaining hand-rolled approach. |
| 5 | `types.py` mixed concerns / cross-module underscore imports | Structure | Addressed: section comment + module docstring. Kept as-is (see deviation #8). |
| 6 | `_compute_total_cost` duplicates future `get_total_usage` | Duplication risk | Added NOTE comment for Phase 2 delegation. |
| 7 | `validate_plan` raises on errors but discards warnings | Design | Fixed: `ValidationError(ValueError)` carries full `ValidationResult`. |
| 8 | Misleading test comment in `test_templates.py` | Misleading | Fixed: corrected offset explanation. |
| 9 | Missing dash/underscore tests for `set_config_value` | Test gap | Fixed: added 2 tests. |
| 10 | Verbose `_config_to_merge_dict` (5 identical patterns) | Verbosity | Fixed: extracted `_section_to_dict` helper. |
| 11 | Inline `import re` in `templates.py` | Inconsistency | Fixed: moved to module-level. |
| 12 | Brittle JSON string comparison in round-trip test | Test quality | Fixed: direct dict comparison. |
| 13 | Missing return type annotations on helpers | Type safety | Fixed: added return types to 3 functions. |

**Lessons learned:**

- **Dict key vs field name serialization must be distinct.** The generic `_serialize_value` was blindly applying camelCase to all string dict keys, corrupting data keys (task IDs, alias names) that contain underscores. The bug was masked by test fixtures using only hyphenated keys like `"task-1"`. **Always include underscored data keys in serialization test fixtures.**
- **Config merge format must separate aliases from profiles.** Flattening aliases (strings) and profiles (dicts) into one dict loses data when they share keys. The structured `_aliases`/`_profiles` format preserves both, and `_normalize_toml_dict` bridges the TOML flat format.
- **Validation logic duplication is inevitable when one path accepts native types and another accepts strings.** Unify via a shared rule registry rather than maintaining parallel code paths.
- **Phase 0's review finding #4 (`set_config_value` path param clarification) was addressed** — the implementation correctly uses `path` as the project root directory, not a dotted config path.

**Spec adjustments:** None needed. All deviations are implementation-level refinements compatible with the spec's contracts.

---

### Phase 2 — Git/IO Layer

**Planned scope:** git.py, worktree.py, record.py, log.py + integration tests

**Acceptance criteria:** All `tests/integration/` pass

**Review findings to address:** (none)

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
- **Note:** `help.py` routing/scaffolding and topic registry are already in place (Phase 0 review fixup). Remaining work is writing the actual ~800 lines of topic content.

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
