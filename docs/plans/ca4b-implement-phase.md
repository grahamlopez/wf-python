# Implement Phase 4a: Core orchestration engine + CLI handlers — scheduler, task_executor, review, and all CLI subcommand implementations

## Context


## Project: `wf` — structured AI development workflow CLI

### Architecture
- Python 3.12+, stdlib only, zero external deps
- `bin/wf` — CLI entry point (argparse, all subcommands already wired with `_not_implemented` handlers)
- `wflib/` — core library modules
- `profiles/` — runner profiles (pi, claude_code, mock — all implemented)
- `adapters/` — output parsers (all implemented)
- `tests/` — unit, integration, e2e, profile, adapter tiers

### What's Done (Phases 0–3: 367 tests passing, 0 failures)
- `types.py` (722 lines) — full dataclass serde, extract_tool_call, validate_schema
- `config.py` (731 lines) — TOML loading, merge, resolution, apply_cli_overrides
- `validate.py` (159 lines) — dependency refs, cycle detection, heuristic warnings
- `brief.py` (102 lines) — task brief assembly
- `render.py` (445 lines) — markdown rendering, usage tables, status formatting
- `templates.py` (108 lines) — frontmatter parsing, discovery, substitution
- `record.py` (370 lines) — CRUD, atomic writes, phase transitions, events, usage aggregation
- `git.py` (92 lines) — subprocess wrapper, branch/HEAD/clean helpers
- `worktree.py` (230 lines) — create/setup/merge_back/cleanup, commit_or_amend_workflow_files
- `runner.py` (322 lines) — spawn_headless, spawn_in_tmux, extract_report_result, _read_agent_results
- `tmux.py` (156 lines) — pane management, exit-code polling
- `log.py` (36 lines) — JSONL debug logging
- All profiles (pi, claude_code, mock) and adapters (pi_json_mode, pi_session, claude_stream_json)

### What Phase 4a Must Implement
1. **scheduler.py** — DAG scheduling (get_ready_tasks, skip_dependents, reset_ready_skipped, resolve_task_model, execute_plan, execute_single_task, execute_fixup)
2. **task_executor.py** — per-task lifecycle (run_task, _setup_worktree, _capture_diff_stat, _merge_and_cleanup, _preserve_results)
3. **review.py** — diff context building, review/auto-review orchestration, extract_plan_from_messages
4. **bin/wf** — replace ALL _not_implemented handlers with real implementations for all ~25 subcommands

### Phase 4b (planned later, after review of 4a)
- help.py content, completions.py, E2E tests, final integration, tracker update

### Key Patterns
- Record file at `docs/workflows/<name>.json` is the single source of truth
- All config comes from `record.workflow.config` snapshot (set at init time)
- CLI flags override config ephemerally via `apply_cli_overrides()`
- Mock profile + mock_agent.py enable E2E testing without real AI harnesses
- `run_wf()` helper in `tests/util.py` spawns `bin/wf` as subprocess
- stdout on error: `{"error": "<message>"}` JSON, exit code 1
- Atomic writes via tempfile + os.replace for all record saves


## Tasks (6)

### task-1: Implement scheduler pure functions

**Goal:** Implement the four pure scheduling functions in `wflib/scheduler.py`: `get_ready_tasks`, `skip_dependents`, `reset_ready_skipped`, and `resolve_task_model`. These are the foundation that the async execute functions call. Also add unit tests for all four functions.

**Files:**
- `wflib/scheduler.py`
- `wflib/types.py`
- `wflib/brief.py`
- `docs/plans/wf-spec.md`

**Constraints:**
- `get_ready_tasks` returns tasks sorted lexicographically by task.id (deterministic tie-breaking per spec)
- `skip_dependents` does transitive BFS closure — if A depends on B and B depends on failed C, both A and B are skipped
- `reset_ready_skipped` iterates until stable (a reset may unblock another reset)
- `resolve_task_model` precedence: cli_model > task.model > plan.defaultModel > config.model.implement > None; returns (model_name, source_string)
- All four are pure functions — no I/O, no async, no record mutation

**Acceptance Criteria:**
- All four functions implemented with correct signatures matching the existing stubs
- New test file `tests/unit/test_scheduler.py` with tests covering: empty plan, independent tasks, tasks with deps met, tasks with deps not met, diamond dependency readiness, skip_dependents transitive closure, reset_ready_skipped stabilization, all 5 levels of model resolution precedence
- `python3 -m pytest tests/unit/test_scheduler.py -v` passes
- All existing 367 tests still pass

**Depends on:** none

### task-2: Implement task_executor.py — per-task lifecycle

**Goal:** Implement the full per-task execution lifecycle in `wflib/task_executor.py`: `run_task`, `_setup_worktree`, `_capture_diff_stat`, `_merge_and_cleanup`, and `_preserve_results`. This is the workhorse that the scheduler delegates to for each task.

**Files:**
- `wflib/task_executor.py`
- `wflib/scheduler.py`
- `wflib/runner.py`
- `wflib/worktree.py`
- `wflib/brief.py`
- `wflib/record.py`
- `wflib/git.py`
- `profiles/__init__.py`
- `docs/plans/wf-spec.md`

**Constraints:**
- `run_task` follows the spec's 16-step pipeline: worktree setup → brief assembly → model resolution → profile resolution → record task_start → spawn agent → preserve results → read results → capture diff/stat → commit if dirty → merge back (with lock) → handle conflicts → record task_complete → update deps → cleanup worktree → record cleanup event
- Merge conflict auto-resolution: on conflict, spawn a resolution agent using `prompts/merge-resolver.md` as system prompt, with conflict context in the prompt. If agent resolves all files: `git add` resolved files, `git rebase --continue`, then fast-forward merge. If resolution fails: mark task failed, preserve worktree (`worktree_preserved=True`), record mergeResolveFailed event
- The merge_lock (asyncio.Lock) is held for the entire merge-and-cleanup sequence including conflict resolution
- `_preserve_results` copies results.json to `docs/workflows/.sessions/<workflow>/<task-id>.results.json`. On failure, also copies session file to `<task-id>.jsonl`
- `_capture_diff_stat` uses `git diff --name-only` and `git diff --stat` against main branch
- On agent failure (nonzero exit or error): mark task failed, call `skip_dependents`, preserve worktree and session file
- Every record mutation is followed by `save_record` (atomic write after every state change per spec)

**Acceptance Criteria:**
- All five functions implemented, `run_task` is async
- The module imports and the function signatures match the existing stubs
- No unit tests required for this task — task_executor is integration-heavy and tested via E2E later
- All existing tests still pass

**Depends on:** task-1

### task-3: Implement scheduler async execute functions

**Goal:** Implement the three async scheduling functions in `wflib/scheduler.py`: `execute_plan`, `execute_single_task`, and `execute_fixup`. These orchestrate DAG-based task execution using `task_executor.run_task`.

**Files:**
- `wflib/scheduler.py`
- `wflib/task_executor.py`
- `wflib/record.py`
- `wflib/config.py`
- `wflib/types.py`
- `wflib/render.py`
- `docs/plans/wf-spec.md`

**Constraints:**
- `execute_plan`: pool-based scheduling — tasks start as soon as deps complete, up to concurrency limit. Uses asyncio.Lock for serialized merge-back. Saves record after every state change. Fires callbacks for UI integration. Runs crash recovery at start (find running tasks, reset to pending, clean orphaned worktrees). Auto-commits record before starting (commit_or_amend_workflow_files). Records baseCommit and startedAt/completedAt.
- Concurrency tie-breaking: when multiple tasks become ready simultaneously, start in lexicographic order by task.id
- `execute_single_task`: validates deps are met (all deps must be 'done'), delegates to task_executor.run_task. Reads settings from record.workflow.config, applies cli_overrides
- `execute_fixup`: same DAG scheduler, results stored in review.fixup_implementation instead of record.implementation. Fixup model precedence: cli_overrides['fixup_model'] > config.model.fixup > normal resolve_task_model chain
- ExecutionSummary is populated with counts (done/failed/skipped/pending), duration_seconds, usage_rows (one UsageRow per task), and base_commit
- Uses `config.apply_cli_overrides()` for ephemeral CLI flag overrides

**Acceptance Criteria:**
- All three async functions implemented
- `execute_plan` handles resume (only runs pending tasks), crash recovery, and returns ExecutionSummary
- `execute_fixup` stores results in review.fixup_implementation
- All existing tests still pass

**Depends on:** task-2

### task-4: Implement review.py — diff context and review orchestration

**Goal:** Implement the review module: `build_diff_context`, `run_review`, `run_auto_review`, and `extract_plan_from_messages`.

**Files:**
- `wflib/review.py`
- `wflib/runner.py`
- `wflib/git.py`
- `wflib/types.py`
- `wflib/record.py`
- `profiles/__init__.py`
- `docs/plans/wf-spec.md`

**Constraints:**
- `build_diff_context` builds markdown from: commit log since base_commit, git diff --stat, and full git diff. Caps the full diff at 100KB. Falls back to uncommitted changes if no base_commit.
- `run_review` spawns a review agent using `prompts/reviewer.md` as system prompt, includes diff context in the prompt. Uses config.model.review as default model; cli_model overrides. Resolves profile via config.agent.profile.
- `run_auto_review` uses `prompts/reviewer-with-plan.md` prompt. After agent exits, extracts `submit_plan` tool call from messages. If found, parses into a Plan and validates it. Returns AutoReviewResult with optional fixup plan.
- `extract_plan_from_messages` delegates to `extract_tool_call(messages, 'submit_plan')` from types.py, then converts to Plan via plan_from_json
- Both run_review and run_auto_review record usage and return the review text from the agent's last assistant message text content

**Acceptance Criteria:**
- All four functions implemented
- `build_diff_context` returns markdown with commit log, stat, and diff sections
- `run_auto_review` returns AutoReviewResult with plan when agent calls submit_plan, None otherwise
- All existing tests still pass

**Depends on:** task-1

### task-5: CLI handlers — init, submit-plan, record-brainstorm, query commands, utilities

**Goal:** Replace the `_not_implemented` handler for all non-execution, non-agent-spawning CLI subcommands in `bin/wf`. These are the 'simple' commands that do record I/O, rendering, validation, and config management — no async, no subprocess spawning.

**Files:**
- `bin/wf`
- `wflib/record.py`
- `wflib/config.py`
- `wflib/validate.py`
- `wflib/brief.py`
- `wflib/render.py`
- `wflib/templates.py`
- `wflib/types.py`
- `wflib/git.py`
- `wflib/worktree.py`
- `schemas/workflow.schema.json`
- `docs/plans/wf-spec.md`

**Constraints:**
- `wf init`: resolve config, validate git repo, create record, commit via commit_or_amend_workflow_files, create workflow worktree (unless --no-worktree). stdout: JSON with workflowId, recordFile, worktree
- `wf submit-plan`: read plan JSON from stdin, validate (deps + cycles), enforce re-submission policy per spec (accept/warn/reject based on status), write to record, initialize task statuses. stdout: JSON with message, status, warnings array
- `wf record-brainstorm`: read brainstorm JSON from stdin, validate, write to record. stdout: JSON with message, status
- `wf status`: load record, render via format_status. --json outputs raw record JSON
- `wf list/history`: scan records via list_records, render via format_history_table. --json for raw JSON. --all includes done/failed
- `wf render`: load record, output render_record_markdown
- `wf validate`: read plan file, validate, print Valid or errors
- `wf brief`: load record, assemble_task_brief, print the brief
- `wf schema`: read schema file, optionally extract --component via $defs with $ref inlining
- `wf config list/get/set`: delegate to config.py functions (show_resolved, show_with_origins, set_config_value)
- `wf template list/show/render`: delegate to templates.py functions
- All error paths emit {"error": "<message>"} JSON to stdout and exit code 1
- Handle --usage flag on submit-plan and record-brainstorm (parse usage JSON from the flag value)

**Acceptance Criteria:**
- All listed subcommands have real implementations (no _not_implemented)
- `wf init test --cwd <tmpdir> --no-worktree` creates a record file and exits 0
- `echo '<plan-json>' | wf submit-plan test --cwd <tmpdir>` writes plan to record
- `wf status test --cwd <tmpdir>` prints formatted status text
- `wf schema` outputs valid JSON
- `wf schema --component plan` outputs the Plan sub-schema with inlined $refs
- All existing tests still pass

**Depends on:** none

### task-6: CLI handlers — execute, execute-task, review, auto-review, close, recover, run, brainstorm, plan

**Goal:** Replace the `_not_implemented` handler for all execution and agent-spawning CLI subcommands in `bin/wf`. These commands involve async orchestration, subprocess spawning, and the full workflow lifecycle.

**Files:**
- `bin/wf`
- `wflib/scheduler.py`
- `wflib/task_executor.py`
- `wflib/review.py`
- `wflib/record.py`
- `wflib/config.py`
- `wflib/worktree.py`
- `wflib/git.py`
- `wflib/runner.py`
- `wflib/render.py`
- `docs/plans/wf-spec.md`

**Constraints:**
- `wf execute`: load record, apply CLI overrides, run asyncio.run(execute_plan(...)). stdout: JSON with counts, duration, usageRows
- `wf execute-task`: load record, validate task exists, run asyncio.run(execute_single_task(...)). stdout: JSON TaskResult
- `wf review`: load record, run asyncio.run(run_review(...)), append ReviewRecord. stdout: review text
- `wf auto-review`: load record, run asyncio.run(run_auto_review(...)), if fixup plan: run asyncio.run(execute_fixup(...)). stdout: JSON with reviewText, findingsActionable, fixupCounts
- `wf close`: clean up .sessions/ dir (log .jsonl deletions), commit changes, merge workflow worktree via close_workflow_worktree. On conflict: spawn resolution agent. On clean: cleanup worktree, write close record. Bare mode (no worktree): just commit and set done. stdout: JSON with mergeResult, finalCommit, diffStat
- `wf recover`: load record, find running tasks, check for orphaned results in .sessions/, clean orphaned worktrees from activeResources, reset running→pending, append crashRecovery events. stdout: JSON summary
- `wf run`: read workflow.status, walk through phases (brainstorm→plan→execute→review→close) based on automation levels. Resume from current phase. Block on each phase. Show unified progress output.
- `wf brainstorm/plan`: spawn agent with appropriate prompt and tool, extract tool call from messages, record results. Handle tmux vs headless based on config.
- All commands use `apply_cli_overrides` for ephemeral flag overrides
- All error paths emit {"error": "<message>"} JSON to stdout and exit code 1

**Acceptance Criteria:**
- All listed subcommands have real implementations
- `wf execute test --cwd <dir> --profile mock --no-tmux --no-worktrees` runs the scheduler
- `wf recover test --cwd <dir>` handles crash cleanup
- `wf close test --cwd <dir>` performs merge and cleanup
- All existing tests still pass

**Depends on:** task-3, task-4, task-5
