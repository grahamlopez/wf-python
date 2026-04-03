# Address all 17 code review findings from Phase 4a review

## Context

The `wf` project is a structured AI development workflow tool. Key files:
- `wflib/scheduler.py` — DAG scheduler with `execute_plan`, `execute_single_task`, `execute_fixup` async functions and 4 pure scheduling functions
- `wflib/task_executor.py` — Per-task execution lifecycle (`run_task`, `_merge_and_cleanup`, etc.)
- `wflib/review.py` — Code review orchestration (`build_diff_context`, `run_review`, `run_auto_review`)
- `wflib/record.py` — Central state manager with `record_task_start`, `record_task_complete`, `record_event`, etc.
- `bin/wf` — CLI entry point with handlers for all subcommands
- `wflib/types.py` — Data classes including `WorkflowStatus` enum (has `BRAINSTORMING` value)
- `profiles/__init__.py` — `RunnerProfile` protocol, `get_profile`, `wf_dir` helper
- `wflib/runner.py` — Agent subprocess spawning with `spawn_headless`, `_read_agent_results`
- `tests/unit/test_scheduler.py` — Tests for the 4 pure scheduling functions

Architecture: `wflib/` is the core library. `profiles/` is harness-specific. `bin/wf` is the CLI. Core should not import from profiles at module level.

The DAG scheduling loop in `execute_plan` (lines 318-430) and `execute_fixup` (lines 582-680) are ~100 lines of duplicated concurrent logic. The review calls for extracting a shared `_run_dag_loop` function parameterized on event-recording strategy and optional callbacks. `record.py` has `record_task_start` and `record_task_complete` that handle status+timestamp+event in one call.

For finding #3, the refactor request is to make execute+review+fixup run in a single `asyncio.run()` call by creating an async pipeline function.

## Tasks (12)

### task-1: Extract shared DAG scheduling loop (findings #1, #2)

**Goal:** Extract the duplicated DAG scheduling while-loop from `execute_plan` and `execute_fixup` into a single shared async function `_run_dag_loop`. Both callers should delegate to this function. The fixup path should use `record_mod.record_task_start` and `record_mod.record_task_complete` (from record.py) instead of manually constructing and appending `ImplementationEvent` objects, eliminating the inconsistency from finding #2.

**Files:**
- `wflib/scheduler.py`
- `wflib/record.py`

**Constraints:**
- The shared function signature should be roughly: `async def _run_dag_loop(plan, impl, record, cwd, config, cli_model, on_task_start=None, on_task_complete=None, on_state_change=None)` — taking the implementation record to write to, optional callbacks, and all parameters needed by `run_task`.
- Both `execute_plan` and `execute_fixup` must use the extracted `_run_dag_loop`. No scheduling logic should remain duplicated.
- The fixup path must use `record_mod.record_task_start(record, task.id)` and `record_mod.record_task_complete(record, task_id, result)` instead of manually creating ImplementationEvent objects. Note: `record_task_start` and `record_task_complete` write to `record.implementation`, so `execute_fixup` should temporarily set `record.implementation` to the fixup_impl before calling `_run_dag_loop`, then restore it after (or pass the impl target as a parameter to the recording functions).
- Actually, the cleaner approach: have `_run_dag_loop` accept two callables `on_record_task_start(task_id)` and `on_record_task_complete(task_id, result)` that the caller provides. `execute_plan` passes lambdas that call `record_mod.record_task_start` / `record_mod.record_task_complete`. `execute_fixup` passes lambdas that do the same but targeting the fixup_impl. This avoids mutating `record.implementation`.
- The skip_dependents and reset_ready_skipped event recording should also be unified in the shared loop.
- All existing tests in test_scheduler.py must still pass.

**Acceptance Criteria:**
- The DAG scheduling while-loop appears exactly once in scheduler.py (in `_run_dag_loop`)
- `execute_plan` and `execute_fixup` both call `_run_dag_loop`
- `execute_fixup` no longer directly creates `ImplementationEvent` objects
- `python -m pytest tests/unit/test_scheduler.py` passes
- `python -c 'from wflib.scheduler import execute_plan, execute_fixup, execute_single_task'` succeeds

**Depends on:** none

### task-2: Refactor asyncio.run pipeline for execute+review (finding #3)

**Goal:** Refactor `_do_auto_review` and its callers so that the execute→review→fixup pipeline runs in a single `asyncio.run()` call instead of three sequential ones. Create an async function `_execute_and_review_pipeline` that awaits `execute_plan`, then `run_auto_review`, then `execute_fixup` in sequence. `_cmd_execute` and `_cmd_auto_review` each call `asyncio.run()` once wrapping this pipeline. Add a prominent comment explaining that `_do_auto_review` must not be called from within an existing event loop.

**Files:**
- `bin/wf`

**Constraints:**
- `_do_auto_review` should become an async function (rename to `_do_auto_review_async` or just make `_do_auto_review` async).
- `_cmd_execute` should call `asyncio.run()` exactly once, wrapping an async function that does execute_plan + optional auto-review.
- `_cmd_auto_review` should call `asyncio.run()` exactly once.
- Add a comment near the async pipeline function: `# WARNING: This function must be awaited inside asyncio.run(). Do not call from within an existing event loop — asyncio.run() will raise RuntimeError.`
- Preserve all existing behavior: auto-review trigger conditions, save_record calls, error handling, JSON output.

**Acceptance Criteria:**
- `_cmd_execute` contains exactly one `asyncio.run()` call
- `_cmd_auto_review` contains exactly one `asyncio.run()` call
- `_do_auto_review` is now async
- A warning comment exists near the pipeline function about event loop constraints
- `python -c 'import ast; ast.parse(open("bin/wf").read())'` succeeds (syntax valid)

**Depends on:** none

### task-3: Unify prompt loading functions (finding #4)

**Goal:** Replace the two different `_load_system_prompt` / `_load_prompt` functions with a single shared `load_prompt(filename)` function in a common location. Both `task_executor.py` and `review.py` should use it.

**Files:**
- `wflib/task_executor.py`
- `wflib/review.py`
- `profiles/__init__.py`

**Constraints:**
- Create the shared function in `wflib/_util.py` (which already exists for `utc_now_iso`). It should use the `wf_dir()` approach (via `profiles.wf_dir()` — but to avoid core→profiles dependency, compute the wf root as `Path(__file__).resolve().parent.parent` which is the same as what `profiles.wf_dir()` returns).
- The function should raise `FileNotFoundError` (not silently return empty string). Callers that want the silent fallback should catch the exception explicitly.
- In `task_executor.py`, wrap the call in try/except to log a warning to stderr when a prompt file is missing, then fall back to empty string. This makes the silent fallback explicit and visible.
- Remove `_load_system_prompt` from `task_executor.py` and `_load_prompt` from `review.py`.
- All imports in `review.py` should use the new shared function.

**Acceptance Criteria:**
- No function named `_load_system_prompt` exists in `task_executor.py`
- No function named `_load_prompt` exists in `review.py`
- A `load_prompt` function exists in `wflib/_util.py`
- Both `task_executor.py` and `review.py` import and use `load_prompt` from `wflib._util`
- `python -c 'from wflib._util import load_prompt'` succeeds
- `python -c 'from wflib.task_executor import run_task'` succeeds
- `python -c 'from wflib.review import run_review'` succeeds

**Depends on:** none

### task-4: Fix RunnerProfile import layering violation (finding #5)

**Goal:** Move the top-level `from profiles import RunnerProfile` in `task_executor.py` to a deferred import or string annotation, fixing the core→profiles layering violation.

**Files:**
- `wflib/task_executor.py`

**Constraints:**
- The file already has `from __future__ import annotations` so all annotations are strings by default. Simply remove the top-level `from profiles import RunnerProfile` import.
- Add `from profiles import RunnerProfile` as a deferred import inside `_merge_and_cleanup` where `RunnerProfile` is actually used as a runtime value (it's in the function signature, but with `from __future__ import annotations` that's fine — however `profile.get_tool_paths()` is called at runtime so the type needs to be available). Actually, with `from __future__ import annotations`, the type annotation is never evaluated at runtime, so the import is only needed if RunnerProfile is used as a runtime value. Check: it's only in type annotations. So just removing the top-level import is sufficient.
- Verify no runtime use of `RunnerProfile` exists (it's only in type annotations of `_merge_and_cleanup`).

**Acceptance Criteria:**
- No top-level import of `RunnerProfile` in `task_executor.py`
- `python -c 'from wflib.task_executor import run_task'` succeeds
- `python -c 'import wflib.task_executor'` succeeds

**Depends on:** none

### task-5: Remove BRAINSTORMING dead status + dead phase_order (findings #6, #14)

**Goal:** Remove the `BRAINSTORMING` value from `WorkflowStatus` enum since it's never set by any code path, and remove the unused `phase_order` variable from `_cmd_run`.

**Files:**
- `wflib/types.py`
- `bin/wf`

**Constraints:**
- Remove `BRAINSTORMING = "brainstorming"` from the `WorkflowStatus` enum in `types.py`.
- Remove the `phase_order` list (lines 1278-1285) from `_cmd_run` in `bin/wf`.
- Verify no other code references `WorkflowStatus.BRAINSTORMING` (only the phase_order list does, and it's being removed too).
- If the JSON schema file `schemas/workflow.schema.json` references `brainstorming` as a valid status, update it too.

**Acceptance Criteria:**
- `BRAINSTORMING` does not appear in `wflib/types.py`
- `phase_order` does not appear in `bin/wf`
- `python -c 'from wflib.types import WorkflowStatus; assert not hasattr(WorkflowStatus, "BRAINSTORMING")'` succeeds
- `python -c 'import ast; ast.parse(open("bin/wf").read())'` succeeds

**Depends on:** none

### task-6: Extract shared crash recovery function (finding #7)

**Goal:** Extract the crash recovery logic (iterating running tasks, checking orphaned results, cleaning worktrees, resetting to pending) into a shared function `recover_running_tasks(record, cwd)` in `wflib/scheduler.py` (or `wflib/record.py`). Both `execute_plan` and `_cmd_recover` should call this shared function.

**Files:**
- `wflib/scheduler.py`
- `bin/wf`

**Constraints:**
- Put the shared function in `wflib/scheduler.py` since it already imports worktree and runner modules.
- The function should handle: checking for orphaned results.json files, incorporating results (best-effort), resetting RUNNING tasks to PENDING, cleaning up orphaned worktrees, recording CRASH_RECOVERY events.
- The function should return a summary suitable for _cmd_recover's JSON output: `{'cleaned_worktrees': [...], 'reset_tasks': [...], 'incorporated_results': [...]}`.
- The `_cmd_recover` behavior of deleting orphaned results files after incorporation should be preserved (pass a flag or always delete — execute_plan's crash recovery should also delete after incorporation since leaving them around is a latent bug).
- Import the shared function in `bin/wf` `_cmd_recover` handler.

**Acceptance Criteria:**
- A function `recover_running_tasks` exists in `wflib/scheduler.py`
- The crash recovery block inside `execute_plan` calls `recover_running_tasks` instead of inline logic
- `_cmd_recover` in `bin/wf` calls `recover_running_tasks` instead of inline logic
- Crash recovery logic appears only once (in the shared function)
- `python -m pytest tests/unit/test_scheduler.py` passes
- `python -c 'from wflib.scheduler import recover_running_tasks'` succeeds

**Depends on:** none

### task-7: Fix diff truncation bug (finding #8)

**Goal:** Fix the UTF-8 truncation bug in `review.py` where diff text is checked by byte length but sliced by character count. Extract a helper function to eliminate the 3x repetition.

**Files:**
- `wflib/review.py`

**Constraints:**
- Create a helper function `_truncate_diff(text: str, max_bytes: int) -> str` that properly truncates: encode to bytes, slice to max_bytes, decode back (with errors='ignore' or 'replace' to handle split multi-byte chars), append the truncation notice.
- Replace all 3 instances of the inline truncation pattern (lines 74-75, 88-89, 102-103) with calls to `_truncate_diff`.
- The truncation notice should remain `\n\n... (diff truncated at 100KB)`.

**Acceptance Criteria:**
- A `_truncate_diff` function exists in `review.py`
- The inline truncation pattern (encode+check+slice) no longer appears in `build_diff_context`
- `_truncate_diff` encodes to bytes before slicing to ensure correct byte-based truncation
- `python -c 'from wflib.review import build_diff_context'` succeeds

**Depends on:** none

### task-8: Clean up os import alias and cross-module private import (finding #9)

**Goal:** Clean up the `import os as _os` alias and the `_read_agent_results` cross-module private import in `scheduler.py`. After task-6 extracts crash recovery into its own function, the deferred imports should use normal names.

**Files:**
- `wflib/scheduler.py`
- `wflib/runner.py`

**Constraints:**
- Rename `_read_agent_results` to `read_agent_results` (remove underscore prefix) in `runner.py` since it's used cross-module. Update all call sites.
- In the crash recovery function (from task-6), use `import os` (not `as _os`) for deferred imports.
- If `os` is already imported at module level in `scheduler.py`, the deferred import can be removed entirely.

**Acceptance Criteria:**
- `_os` does not appear in `scheduler.py`
- `_read_agent_results` does not appear in `scheduler.py` — it uses `read_agent_results` instead
- The function `read_agent_results` exists in `runner.py` (no leading underscore)
- `python -c 'from wflib.runner import read_agent_results'` succeeds
- `python -m pytest tests/unit/test_scheduler.py` passes

**Depends on:** task-6

### task-9: Fix args mutation in _cmd_run (finding #10)

**Goal:** Fix `_cmd_run` so it doesn't mutate `args.no_tmux` in-place. Each phase should compute its own `no_tmux` value without affecting subsequent phases.

**Files:**
- `bin/wf`

**Constraints:**
- Instead of mutating `args.no_tmux`, create a copy of args or pass phase-specific overrides. The simplest approach: use `copy.copy(args)` to create a shallow copy for each sub-handler call, setting `no_tmux` on the copy.
- Alternatively, compute `phase_no_tmux` locally and set it on a copy: `phase_args = copy.copy(args); phase_args.no_tmux = ...`
- Both brainstorm and plan phases should get their own args copy with the correct no_tmux value.
- Import `copy` at the top of the file (or use `argparse.Namespace(**vars(args))` to create a copy).

**Acceptance Criteria:**
- `_cmd_run` does not assign to `args.no_tmux`
- Each phase call uses a separate args object (or equivalent mechanism to avoid mutation)
- `python -c 'import ast; ast.parse(open("bin/wf").read())'` succeeds

**Depends on:** none

### task-10: Fix bare-mode diff capture and add comment for subprocess.run (findings #11, #17)

**Goal:** Fix `_capture_diff_stat` for bare mode (no worktrees) so it captures the task's actual changes, not just uncommitted working-tree changes. Also add an explanatory comment for why `_merge_and_cleanup` uses `subprocess.run` instead of the `git()` wrapper.

**Files:**
- `wflib/task_executor.py`

**Constraints:**
- For finding #11: When `use_worktrees=False`, the diff should show what the task changed. The current approach passes `"HEAD"` which only shows uncommitted changes. If the task committed, this returns nothing. A better approach: before spawning the agent, capture the current HEAD as `pre_task_commit`. After the agent runs, diff `pre_task_commit..HEAD` for committed changes AND `HEAD` for uncommitted changes. Pass `pre_task_commit` instead of `"HEAD"` to `_capture_diff_stat` when in bare mode.
- For finding #17: Add a comment above the `subprocess.run(["git", "rebase", "--continue"], ...)` call explaining: `# Use subprocess.run directly (not git() wrapper) to set GIT_EDITOR=true, which suppresses the editor during rebase --continue.`

**Acceptance Criteria:**
- `_capture_diff_stat` in bare mode receives a commit ref (not just `"HEAD"`) that represents the state before the task ran
- A comment exists above the `subprocess.run(["git", "rebase", "--continue"]` explaining why `git()` wrapper isn't used
- `python -c 'from wflib.task_executor import run_task'` succeeds

**Depends on:** none

### task-11: Document return type discrepancy and fix wf close branch name (findings #12, #13)

**Goal:** Add a docstring note to `extract_plan_from_messages` acknowledging the `Plan | None` return type vs spec's `dict | None`, and fix the hardcoded branch name in `_cmd_close` to derive from the record.

**Files:**
- `wflib/review.py`
- `bin/wf`

**Constraints:**
- For finding #12: Update the docstring of `extract_plan_from_messages` to note: `Returns Plan | None (spec says dict | None; Plan is preferred as callers get a validated object).`
- For finding #13: In `_cmd_close`, the branch `f"wf-{args.workflow}"` should come from a more robust source. Check if `record.workflow.worktree` or some other field stores the branch. If not, extract the branch name derivation into a shared helper or at minimum add a comment noting the coupling with `create_workflow_worktree`'s naming convention. Look at `wflib/worktree.py` for the `create_workflow_worktree` function to see what branch name it uses.

**Acceptance Criteria:**
- `extract_plan_from_messages` docstring mentions the Plan vs dict return type deviation
- The branch name in `_cmd_close` is either derived from the record/worktree module or has a clear comment about the naming convention coupling
- `python -c 'import ast; ast.parse(open("bin/wf").read())'` succeeds

**Depends on:** none

### task-12: Fix wf brainstorm and wf plan tool loading (finding #16)

**Goal:** Fix `_cmd_brainstorm` and `_cmd_plan` so they load the required tools (`record-brainstorm` and `submit-plan` respectively) from the profile's tool paths, instead of passing `tools=[]`.

**Files:**
- `bin/wf`

**Constraints:**
- In `_cmd_brainstorm`: get tool paths from `profile.get_tool_paths()`, find the `record-brainstorm` tool path, and pass it in the `tools` list to `spawn_headless`.
- In `_cmd_plan`: get tool paths from `profile.get_tool_paths()`, find the `submit-plan` tool path, and pass it in the `tools` list to `spawn_headless`.
- Follow the same pattern already used in `review.py`'s `run_auto_review` which correctly loads `submit-plan` from `profile.get_tool_paths()`.
- If the tool is not found in the profile's tool paths, proceed with `tools=[]` (graceful degradation, not a hard error) but log a warning to stderr.

**Acceptance Criteria:**
- `_cmd_brainstorm` passes the `record-brainstorm` tool path to `spawn_headless` when available
- `_cmd_plan` passes the `submit-plan` tool path to `spawn_headless` when available
- Neither handler passes `tools=[]` unconditionally
- `python -c 'import ast; ast.parse(open("bin/wf").read())'` succeeds

**Depends on:** none
