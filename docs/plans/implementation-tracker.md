# `wf` Implementation Tracker

Tracks progress across all implementation phases. See `wf-spec.md` for the full specification and `impl-strategy.md` for the phasing rationale.

---

## Phase Status

| Phase | Description | Status | Tasks | Notes |
|-------|-------------|--------|-------|-------|
| 0 | Scaffold | **complete** | 7 | Directory structure, type stubs, module stubs, schema, test infra, fixtures, placeholder tests |
| 1 | Pure Foundation | **complete** | 6 | types, validate, config, brief, render, templates + unit tests |
| 2 | Git/IO Layer | **complete** | 7 | git, worktree, record, log + integration tests |
| 3 | Profiles + Runner | **complete** | 11 | profiles, adapters, runner, tmux + profile/adapter tests |
| 4a | Orchestration + CLI (core) | **partial** | 6+4 | scheduler, task_executor, review, CLI handlers |
| 4b | Orchestration + CLI (validation) | not started | — | E2E tests, help content, completions, deferred items |
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

**Started:** 2026-04-02
**Completed:** 2026-04-02

**Implementation summary (python3 -m pytest tests/ --tb=short: 288 passed, 133 skipped):**
- `git.py`: subprocess wrapper + repo status helpers (branch/HEAD, dirty status, file parsing).
- `log.py`: JSONL debug logger with best-effort writes and status snapshot helper.
- `record.py`: record CRUD + atomic writes, query helpers, phase transitions/event tracking, usage aggregation.
- `worktree.py`: task/workflow worktree lifecycle, commit/amend helpers, merge/rebase handling with conflict reporting.
- Integration tests: `test_git.py`, `test_record.py`, `test_worktree.py` now run with zero Phase 2 skips.

**Intentional deviations from spec:**

1. **`toRelative` path conversion deferred to Phase 4.** Phase 1 deviation #6 noted this should be added "once worktrees are wired up (Phase 2)." However, the path-relativization is a brief-assembly concern wired up by `task_executor.py`, not a worktree primitive. Deferred to Phase 4 (noted in Phase 4's tracking section).

2. **`commit_or_amend_workflow_files` amend detection is broader than spec.** The spec says "amends if last commit is `[workflow-init]`". The implementation amends if the last commit message starts with `[workflow` (any workflow-prefixed commit). This is intentionally broader — it also amends `[workflow] name: update record` commits from previous `commit_or_amend_workflow_files` calls, which is the correct behavior for the repeated-save pattern during execution (each record save amends the same commit rather than creating a new one).

**Lessons learned:**
- Worktree cleanup and branch removal must be idempotent to keep repeated runs safe in temp repos.
- Rebase-first merge flows need explicit conflict reporting to keep the caller in control of recovery steps.
- Excluding `docs/workflows/` from task commits prevents record churn while task worktrees iterate.
- **Test skeleton coverage != implementation coverage.** The Phase 0 test skeletons only covered the "happy path" functions. Several important functions (`list_records`, `record_review`, `record_implementation_start`, `get_implementation_state`) have no dedicated integration tests. These will get exercised by E2E tests in Phase 4 but lack isolated unit-level coverage. Future Phase 0 scaffolds should include test stubs for every public function.

**Spec adjustments:** None needed. Deviation #5 (broader amend detection) is a deliberate improvement compatible with the spec's intent.

---

### Phase 3 — Profiles + Runner

**Planned scope:** Profile protocol + registry, pi.py, claude_code.py, mock.py, all adapters, runner.py, tmux.py + profile/adapter tests

**Acceptance criteria:** All `tests/unit/test_profiles.py`, `tests/profile/`, `tests/adapter/` pass; all `tests/integration/test_tmux.py` pass; `runner.py` extraction functions (`extract_report_result`, `extract_summary_fallback`, `_read_agent_results`) pass

**Pre-planning readiness notes:**
- 290 passed, 133 skipped (all Phase 3+). Foundation is solid.
- `resolve_alias` and `get_profile` in `profiles/__init__.py` are still `NotImplementedError` — implement first since everything depends on them.
- Adapter tests need recorded output fixtures. Real pi `--mode json` output captured (NDJSON with `session`, `agent_start`, `message_start`, `message_end`, `turn_end`, `agent_end` events; usage in `message_end` with `cost` sub-object; model/provider on message objects). Session `.jsonl` format also captured (NDJSON with `{type: "message", message: {...}}` entries). Claude Code `stream-json` will need synthetic fixtures (no live harness available).
- `runner.py` is in scope — the extraction functions (`extract_report_result`, `extract_summary_fallback`, `_read_agent_results`) and `spawn_headless` are needed by Phase 4's task executor. `spawn_in_tmux` depends on `tmux.py`.
- Phase 0 test skeletons exist for all target files: 26 profile tests, 17 adapter tests, 8 tmux tests + 10 profile integration tests.

**Planned deviations from spec (approved before execution):**

1. **Synthetic inline test fixtures instead of committed recorded real output.** The spec says profile/adapter tests should use "actual pi `--mode json` stdout and session `.jsonl` files from real runs, committed as fixtures." The plan uses synthetic but structurally accurate NDJSON fixtures defined inline in the test files instead. Reason: real pi session data includes massive encrypted content blobs (tool call IDs, signatures) that are 10KB+ per entry — unwieldy as fixture files and opaque to readers. Synthetic fixtures that match the structural format are more maintainable, self-documenting, and test the same parsing logic. If format drift becomes a concern, real captured fixtures can be added later as a supplementary test layer.

2. **New `tests/unit/test_runner.py` not in spec's test structure.** The spec doesn't list a dedicated runner unit test file — it tests runner through profile/adapter tests and E2E tests. The plan adds `tests/unit/test_runner.py` for the three pure extraction functions (`extract_report_result`, `extract_summary_fallback`, `_read_agent_results`). Reason: these are pure functions with clear input/output contracts that benefit from isolated unit testing, especially the fallback and error handling paths.

3. **Runner durability copying (`docs/workflows/.sessions/`) deferred to Phase 4.** The spec puts the "copy results to `docs/workflows/.sessions/` for durability" step inside `runner.py`'s `spawn_headless`/`spawn_in_tmux`. The plan has the runner focused on subprocess lifecycle only — producing results locally. The durability copy is handled by `task_executor._preserve_results` in Phase 4, which knows the workflow name and session paths. Reason: the runner is profile-driven and workflow-agnostic; durability is a workflow-level concern. This keeps a cleaner boundary.

**Review findings to address:**
- **Finding #9:** `RunnerProfile` import was fixed in Phase 0 cleanup, but the real implementation in `task_executor.py` needs to wire up the profile protocol properly

**Resolved early:**
- **Finding #5:** Shared `_wf_dir` helper added to `profiles/__init__.py`, profiles now delegate to it

**Started:** 2026-04-02
**Completed:** 2026-04-02

**Implementation summary (python3 -m pytest tests/ --tb=short: 367 passed, 65 skipped):**
- `profiles/__init__.py` (100 lines): resolve_alias, get_profile with lazy imports.
- `profiles/pi.py` (143 lines): Full model resolution, headless command construction, tmux wrapper generation, adapter delegation.
- `profiles/claude_code.py` (120 lines): Headless command with MCP config, model resolution with unavailable-model error messages.
- `profiles/mock.py` (55 lines): Alias-only model resolution, mock_agent.py invocation.
- `adapters/pi_json_mode.py` (75 lines): NDJSON parser for pi --mode json, usage accumulation from message_end/cost sub-objects.
- `adapters/pi_session.py` (120 lines): Session .jsonl parser with results_file short-circuit, usage accumulation.
- `adapters/claude_stream_json.py` (130 lines): Stream-json NDJSON parser, tool_use→toolCall mapping, Claude usage field name translation.
- `wflib/runner.py` (225 lines): AgentResult dataclass, extract_report_result, extract_summary_fallback, _read_agent_results, spawn_headless, spawn_in_tmux.
- `wflib/tmux.py` (120 lines): is_tmux_available, shell_escape, pane management, exit-code polling with pane-gone fallback.
- New test file: `tests/unit/test_runner.py` (8 tests for extraction functions).

**Intentional deviations from spec:**

1. **`pi_session.parse` signature: `results_file` is `str | None = None` (optional) instead of required `str`.** The spec and Phase 0 stub have `parse(session_dir: str, results_file: str)`. The implementation makes `results_file` optional because the session parser should work standalone (just session_dir) without requiring a results file path. When called from the Pi profile's tmux wrapper, results_file is always provided. When called for testing or inspection, session_dir alone is sufficient.

2. **`pi_session.py` accumulates `turns` from `usage.turns` field instead of counting assistant messages.** The spec says turns should be counted as "count assistant message_end events" (for JSON mode) but doesn't specify the session adapter's counting method. The implementation accumulates from the usage dict's `turns` field if present (pi may populate this), which can be zero if pi's session format doesn't include it. Should be revisited if turn counts come out wrong in practice — easy to add an assistant-message count fallback.

3. **`runner.py` uses `WF_RESULTS_PATH` env var to locate results.json, falling back to `cwd/results.json`.** The spec's mock_agent example uses `WF_RESULTS_PATH` as a required env var. The runner implementation sets it in the subprocess env (for mock agent compatibility) and uses it as the default location. This is a mild divergence from the spec which has the runner writing to `docs/workflows/.sessions/` (deferred to Phase 4 per planned deviation #3).

4. **`spawn_headless` writes the profile's parsed results to results.json even for non-mock profiles.** The spec has the runner producing results.json via the adapter as an intermediary. The implementation writes the adapter's parsed output as results.json, then reads it back via `_read_agent_results`. This is a slightly round-about path (parse → write → read) but provides a uniform code path and ensures results.json always exists for crash recovery. The mock profile's `parse_headless_output` returns `{}`, so the runner only writes if the parsed result is non-empty or no results file exists yet — avoiding overwriting mock agent's direct results.json.

5. **`spawn_in_tmux` cleans up temp files in `finally` block, including the wrapper script and prompt files.** The spec says the profile's wrapper script must produce results_file before writing exit-code file, and temp cleanup happens after. The implementation follows this ordering (wait_for_exit_code_file blocks until wrapper is done, then reads results), but also cleans individual temp files in addition to the TemporaryDirectory cleanup. Defensive double-cleanup; no functional difference.

**Post-execution bug fix:**

- **`pane_exists` used `display-message -t <pane_id> -p` which returns rc=0 even for non-existent panes.** This caused `test_pane_exists_for_gone_pane` to fail and `test_fallback_on_pane_gone` to hang indefinitely (infinite polling loop). Fixed by switching to `list-panes -t <pane_id>` which reliably returns rc=1 for non-existent panes. Root cause: tmux's `display-message -p` without a format string falls back to the current pane context rather than erroring on an invalid target.

**Lessons learned:**
- **Tmux command behavior is version-dependent and not always intuitive.** `display-message -t <pane_id> -p` returns success even for dead panes in some tmux versions. Always verify tmux command semantics with actual pane lifecycle testing, not just the man page.
- **Synthetic test fixtures require structural accuracy.** The inline NDJSON fixtures need to match the real format closely (e.g., pi's `cost` sub-object within `usage`, Claude's `input_tokens` vs `input` naming). Captured a real pi `--mode json` interaction during planning to ensure fixture accuracy.
- **Runner result extraction should be pure functions testable independently.** Separating `extract_report_result`, `extract_summary_fallback`, and `_read_agent_results` from the spawning logic (task-7 before task-8) paid off — the extraction pipeline has 8 focused unit tests that don't need subprocess mocking.

**Spec adjustments:** None needed. All deviations are implementation-level refinements compatible with the spec's contracts.

---

### Phase 4 — Orchestration + CLI (split into 4a/4b)

**Split rationale:** The original Phase 4 plan was ~13 tasks spanning core engine, CLI, E2E tests, help content, and completions. During planning, we split it into two sub-phases:

- **Phase 4a (core):** scheduler, task_executor, review, all CLI handlers — where all hard design decisions live (scheduler semantics, merge conflict resolution, task lifecycle, CLI wiring). 6 tasks.
- **Phase 4b (validation):** E2E tests, help content (~800 lines), completions, deferred items, tracker update — exercises and documents what 4a built. Planned just-in-time after 4a is reviewed.

This split improves review quality: 4a gets thorough review before 4b builds on top of it. If 4a's review surfaces issues, 4b tasks would need to change anyway. The split aligns with the dependency graph — all 4b tasks depend on the last 4a task.

---

### Phase 4a — Orchestration + CLI (core)

**Planned scope:** scheduler.py (pure functions + async execute), task_executor.py, review.py, bin/wf (all CLI handlers)

**Acceptance criteria:** All existing 367 tests still pass, all CLI subcommands have real implementations (no `_not_implemented` remaining), scheduler pure functions have unit tests

**Review findings to address:**
- **Finding #8:** `ReviewRecord` import was fixed in Phase 0, but `execute_fixup` is still a stub — needs real implementation
- **Finding #7:** `scheduler.py` → `render.py` cross-module import comment added in Phase 0 — implement `ExecutionSummary` with `UsageRow` integration per spec

**Resolved early:**
- **Finding #13:** `bin/wf` now aliases no-args to `wf help topics` and `wf help` routes to the help module

**Started:** 2026-04-03
**Completed:** — (in progress)

**First execution (6 tasks, $4.45):** 4 of 6 tasks produced no file changes. Only task-3 (scheduler async) and task-4 (review.py) delivered working code. Task-3 over-delivered by also implementing the 4 pure functions that task-1 was supposed to do. Tasks 1, 2, 5, 6 read context but produced no output (model: gpt-5.2-codex via bedrock-claude-opus-4-6 routing).

**What was delivered:**
- `scheduler.py` (649 lines): All 4 pure functions (get_ready_tasks, skip_dependents, reset_ready_skipped, resolve_task_model) + all 3 async functions (execute_plan, execute_single_task, execute_fixup) + helpers (_build_statuses, _build_summary). Task-3 compensated for task-1's failure.
- `review.py` (268 lines): build_diff_context, run_review, run_auto_review, extract_plan_from_messages. Uses asyncio.to_thread to wrap synchronous spawn_headless.

**What was NOT delivered (requiring supplementary plan):**
- `task_executor.py` — still all 5 NotImplementedError stubs
- `bin/wf` — all 29 CLI handlers still _not_implemented
- `tests/unit/test_scheduler.py` — not created

**Deviations found in delivered code:**
1. **`execute_plan` calls `record_task_start` before `run_task`** — the spec's 16-step pipeline has task_start as step 5 inside run_task. The scheduler pre-empted this. Supplementary plan's task_executor implementation must NOT duplicate the call.
2. **`execute_fixup` doesn't record events** — updates task statuses but doesn't append taskStart/taskComplete events to fixup_impl.events. Fixed in supplementary task-4.
3. **Crash recovery doesn't check `.sessions/` for orphaned results** — spec says to incorporate orphaned results.json files. Only resets running tasks and cleans worktrees. Fixed in supplementary task-4.
4. **`review.py` uses `asyncio.to_thread`** — wraps synchronous spawn_headless instead of native async. Acceptable, not a bug.

**Supplementary plan (4 tasks):** Filed to complete the 4 failed tasks plus fix deviations. task-1: task_executor.py, task-2: CLI simple handlers, task-3: CLI exec handlers, task-4: scheduler tests + deviation fixes.

**Lessons learned:**
- **Silent agent failures are dangerous.** 4 of 6 tasks reported success with no file changes. The planner accepted these as done. Need to treat "completed with no file changes" warnings seriously — they almost certainly mean the agent didn't do its work.
- **Over-scoped context reading.** The failed tasks spent their turns reading context files but never produced output. The model (routed through bedrock) may have hit output limits or simply run out of turns after reading.

**Spec adjustments:** None needed.

---

### Phase 4b — Orchestration + CLI (validation)

**Planned scope (tentative — planned just-in-time after 4a review):** E2E tests (39 skipped stubs → real assertions), help.py (~800 lines of topic content), completions.py (generate_bash/zsh/fish, dynamic complete), brief.py toRelative path conversion, tracker update

**Acceptance criteria:** All `tests/e2e/` pass, `wf help` works, all Phase 4 skips removed, total tests >= 432

**Review findings deferred from 4a:**
- **Finding #10:** E2E tests use `unittest.TestCase` but `conftest.py` provides pytest fixtures — reconcile by converting to pytest functions
- **Finding #6:** crash-recovery fixture setup must create pre-crash state with all tasks running, verify all reset to pending
- **Note:** `help.py` routing/scaffolding and topic registry are already in place. Remaining work is writing the actual ~800 lines of topic content.
- **Deferred from Phase 2:** `brief.py` `toRelative` path conversion (Phase 1 deviation #6). Should be wired up when `task_executor.py` assembles briefs with worktree paths.

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
