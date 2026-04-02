# Address all 5 code review findings from Phase 2 review

## Context

Phase 2 code review found 5 issues across wflib/record.py, wflib/worktree.py, and tests/integration/. All are small, independent fixes. The codebase has 288 passing tests and 133 skipped (Phase 3+). No fix should break existing tests.

## Tasks (3)

### task-1: Fix record.py: use _now_iso() and strengthen record_event signature

**Goal:** Address findings 4 and 5. (1) Replace the inline timestamp formatting in create_record with a call to _now_iso(). (2) Change record_event's event parameter from str to ImplementationEventType so invalid values are caught at the call site, not inside a cast. If any callers in tests pass raw strings, update them to use the enum.

**Files:**
- `wflib/record.py`
- `tests/integration/test_record.py`

**Constraints:**
- create_record must use _now_iso() for created_at instead of duplicating the datetime formatting
- record_event signature should accept ImplementationEventType directly, not str — remove the ImplementationEventType(event) cast inside the body
- Update the docstring to reflect the new type
- Fix any test call sites that pass raw strings to record_event

**Acceptance Criteria:**
- python3 -m pytest tests/ --tb=short passes with same counts (288 passed, 133 skipped)
- grep confirms no duplicate datetime formatting in create_record

**Depends on:** none

### task-2: Fix worktree.py: no-commits fallback and document mid-rebase intent

**Goal:** Address findings 2 and 3. (1) In commit_or_amend_workflow_files, handle the case where git log -1 fails (brand-new repo with no commits) by falling back to a fresh commit instead of raising RuntimeError. (2) In merge_back, add a clear code comment explaining that the rebase is intentionally left in-progress on conflict so the caller (task_executor) can spawn a resolution agent.

**Files:**
- `wflib/worktree.py`
- `tests/integration/test_worktree.py`

**Constraints:**
- commit_or_amend_workflow_files: if git log -1 fails (no commits), treat as 'no previous workflow commit' and do a fresh commit
- merge_back: add a comment block above the early return explaining the intentional mid-rebase state — reference task_executor._merge_and_cleanup as the consumer
- Do NOT change merge_back behavior — only add documentation

**Acceptance Criteria:**
- python3 -m pytest tests/ --tb=short passes with same counts (288 passed, 133 skipped)
- commit_or_amend_workflow_files works on a repo with no prior commits (add a test case)

**Depends on:** none

### task-3: Extract shared init_repo helper for integration tests

**Goal:** Address finding 1. Extract the duplicated init_repo helper from test_git.py and test_worktree.py into a shared module at tests/integration/helpers.py. Update both test files to import from the shared module. The shared version should support the with_commit parameter (from test_git.py's version).

**Files:**
- `tests/integration/test_git.py`
- `tests/integration/test_worktree.py`

**Constraints:**
- Create tests/integration/helpers.py with the shared init_repo function
- The shared init_repo must support with_commit=True (default) parameter from test_git.py's version
- Remove the local init_repo definitions from both test files and replace with imports from helpers
- Do not change any test logic — only the helper location

**Acceptance Criteria:**
- python3 -m pytest tests/ --tb=short passes with same counts (288 passed, 133 skipped)
- grep -rn 'def init_repo' tests/integration/ shows only one definition in helpers.py

**Depends on:** none
