# Address code review findings: fix immediate Phase 0 issues and update implementation tracker with deferred items

## Context

This is the `wf` CLI tool project. Phase 0 (scaffold) is complete. A code review identified 13 findings — some fixable now as small mechanical edits, others deferred to later phases. The project has stub modules (all raising NotImplementedError), a JSON schema, E2E fixtures, and placeholder tests. Key files: `tests/e2e/mock_agent.py`, `wflib/types.py`, `wflib/config.py`, `wflib/scheduler.py`, `wflib/task_executor.py`, `bin/wf`, `tests/e2e/fixtures/crash-recovery/expected/record.json`, `docs/plans/implementation-tracker.md`.

## Tasks (2)

### task-1: Fix immediate Phase 0 code review findings

**Goal:** Apply 10 small fixes from the code review. All are mechanical edits — guard clauses, comments, imports, cleanup.

**Files:**
- `tests/e2e/mock_agent.py`
- `wflib/types.py`
- `wflib/config.py`
- `wflib/scheduler.py`
- `wflib/task_executor.py`
- `bin/wf`
- `tests/e2e/fixtures/crash-recovery/expected/record.json`

**Constraints:**
- Finding #1: In `tests/e2e/mock_agent.py` line 26, guard `os.makedirs` — if `os.path.dirname(op['path'])` returns empty string, skip the makedirs call
- Finding #3: In `wflib/types.py`, add a comment on `ImplementationEvent.event` field: `# Validated via schema enum — see ImplementationEvent in workflow.schema.json`
- Finding #4: In `wflib/config.py`, add a clarifying comment on `set_config_value` explaining that `path` is the project root directory (used to locate `.wf/config.toml` for project scope), not a dotted config path or file path
- Finding #6: In `tests/e2e/fixtures/crash-recovery/expected/record.json`, add a top-level `_comment` field explaining that this models a crash where ALL tasks were running (none had completed), so all reset to pending
- Finding #7: In `wflib/scheduler.py`, add a comment above `from wflib.render import UsageRow` explaining this cross-module import is spec-intentional — ExecutionSummary requires UsageRow per spec
- Finding #8: In `wflib/scheduler.py`, add `from wflib.types import ReviewRecord` so the forward reference string `'ReviewRecord'` in `execute_fixup` resolves. Remove the string quotes around ReviewRecord in the function signature
- Finding #9: In `wflib/task_executor.py`, add `from profiles import RunnerProfile` so the forward reference string `'RunnerProfile'` resolves. Remove string quotes around RunnerProfile in the function signature. Check all functions in the file for the same pattern
- Finding #11: Create a minimal `README.md` at repo root with just a project title and one-line description: `# wf` / `Structured AI development workflows.`
- Finding #12: Remove all `__pycache__` directories from disk: `find . -name __pycache__ -exec rm -rf {} +`
- Finding #13: In `bin/wf`, change the no-args case comment and error message to be more specific — use `{"error": "not implemented: wf with no arguments should show help topics"}` instead of the generic `_not_implemented` call

**Acceptance Criteria:**
- `python3 -m pytest tests/ --co -q` succeeds (collection works, no import errors)
- `python3 -c "from wflib import types, config, scheduler, task_executor"` succeeds
- `bin/wf --help` still shows all subcommands
- No `__pycache__` directories exist on disk
- `README.md` exists at repo root
- The crash-recovery expected/record.json is still valid JSON

**Depends on:** none

### task-2: Update implementation tracker with deferred review findings

**Goal:** Add deferred code review findings to the appropriate phase sections in `docs/plans/implementation-tracker.md`. Three items need to be recorded: (1) Missing directories for Phase 5, (2) Profile duplication for Phase 3, (3) E2E test unittest/pytest mismatch for Phase 4. Also add all 13 findings to a new 'Deferred Items' section so nothing is lost.

**Files:**
- `docs/plans/implementation-tracker.md`

**Constraints:**
- Add a note under Phase 1's section mentioning Finding #3 (ImplementationEvent.event should become a proper Enum or get validated) and Finding #4 (set_config_value path param needs clear implementation)
- Add a note under Phase 3's section mentioning Finding #5 (extract shared `_wf_dir` to base, provide shared `_effective_map_for` helper in profiles/__init__.py) and Finding #9 (RunnerProfile import was fixed but the implementation needs to wire it up properly)
- Add a note under Phase 4's section mentioning Finding #8 (ReviewRecord import fixed but execute_fixup needs real implementation), Finding #10 (E2E tests are unittest.TestCase but conftest provides pytest fixtures — need to reconcile by converting E2E tests to pytest functions or wrapping fixtures), Finding #6 (crash-recovery fixture comment added, but test setup must create pre-crash state with all tasks running), Finding #7 (scheduler→render import comment added, implement accordingly), Finding #13 (no-args case in bin/wf needs help topics implementation)
- Add a note under Phase 5's section mentioning Finding #2 (create tools/, tools/pi_extensions/, prompts/, templates/ directories — templates/ is needed by wflib/templates.py's SHIPPED_DIR)
- Replace the empty 'Deferred Items' section with a summary table of all 13 findings, their severity, which were fixed in Phase 0 cleanup, and which are deferred to which phase
- Do NOT modify any Python files or anything outside implementation-tracker.md

**Acceptance Criteria:**
- implementation-tracker.md has notes in Phase 1, 3, 4, and 5 sections referencing specific review findings
- The Deferred Items section contains a complete table of all 13 findings with their disposition (fixed or deferred+phase)
- No Python files were modified

**Depends on:** none
