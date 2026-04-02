# Phase 0 scaffold: create the complete project skeleton so that all tests can be collected and run (red baseline) with zero import errors

## Context

We are building `wf`, an agentic developer workflow orchestration CLI tool. The full spec is at `docs/plans/wf-spec.md` (~4600 lines). The implementation strategy is at `docs/plans/impl-strategy.md`. The implementation tracker is at `docs/plans/implementation-tracker.md`. The repo currently contains only these docs — no source code exists yet.

This is Phase 0 of 6. Its sole purpose is to create the project skeleton so that `python3 -m pytest tests/` runs with zero import errors and all tests either skip or fail (the red baseline). No functional implementation — just directory structure, type definitions, module stubs, test infrastructure, E2E fixtures, and placeholder tests.

Key spec conventions: Python 3.12+ stdlib only, snake_case in Python, camelCase in JSON, all JSON I/O through `wflib/types.py`, `#!/usr/bin/env python3` shebang for bin/wf.

INTENTIONAL DEVIATIONS FROM SPEC/STRATEGY (approved by project owner — do not flag as errors):
1. `pytest.ini` is added for test runner configuration — not in the original spec or strategy docs.
2. Task 5 (module stubs for all ~20 modules) expands Phase 0 scope beyond the strategy doc, which only specifies `types.py` stubs. This is required to satisfy the "imports succeed, zero import errors" criterion when placeholder tests import from all modules.
3. All 9 E2E fixture directories are created instead of the strategy's minimum of 3. Owner directed "keep everything together in phase 0."
4. `unittest.skip` is used instead of `pytest.mark.skip` for stdlib compatibility per the spec's "No external test dependencies" requirement. Both are listed as options in the strategy doc.

## Tasks (7)

### task-1: Project skeleton + CLI entry point

**Goal:** Create the complete directory structure, all __init__.py package files, bin/wf with full argparse skeleton registering every subcommand and its flags, and pytest.ini. After this task, `python3 bin/wf --help` shows all subcommands and `import wflib; import profiles; import adapters` succeeds.

**Files:**
- `docs/plans/wf-spec.md`

**Constraints:**
- bin/wf must use `#!/usr/bin/env python3` shebang and `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` to add repo root to sys.path
- Every subcommand from the spec's Complete CLI Reference section must be registered in argparse with its flags — each handler just prints `{"error": "not implemented"}` to stdout and exits 1
- __init__.py files are minimal (empty or docstring only) — no functional code, no imports
- Create ALL directories from the spec's Repository Structure: bin/, schemas/, prompts/, templates/, tools/, tools/pi_extensions/, wflib/, profiles/, adapters/, tests/unit/, tests/integration/, tests/e2e/, tests/e2e/fixtures/ (with all 9 fixture subdirectories: simple-split, linear-chain, diamond-deps, task-failure, merge-conflict, merge-conflict-unresolvable, review-fixup, crash-recovery, full-lifecycle), tests/profile/, tests/adapter/

**Acceptance Criteria:**
- python3 bin/wf --help shows all subcommands (init, run, brainstorm, plan, record-brainstorm, submit-plan, execute, execute-task, review, auto-review, close, status, list, history, render, validate, brief, recover, schema, config, template, completions, help)
- python3 bin/wf init --help shows init-specific flags (--cwd, --no-worktree, --set)
- python3 -c "import wflib; import profiles; import adapters" succeeds
- pytest.ini exists with testpaths = tests

**Depends on:** none

### task-2: JSON Schema

**Goal:** Create the complete schemas/workflow.schema.json with root schema validating the full workflow record and all $defs for every data structure in the spec. The schema is the published contract for external consumers.

**Files:**
- `docs/plans/wf-spec.md`

**Constraints:**
- All JSON field names use camelCase per the spec's JSON Naming Convention section (dependsOn, defaultModel, filesChanged, diffStat, sourceCommit, sourceBranch, baseCommit, createdAt, etc.)
- Root schema describes the complete workflow record file structure as shown in the spec's Full Structure JSON example
- Every $def must be self-consistent and use $ref to reference other $defs where types are shared (e.g., Plan references Task, ReviewRecord references Plan and ImplementationRecord)
- Include all $defs: Plan, Task, Brainstorm, DesignDecision, ReportResult, Usage, TaskResult, TaskStatus, ImplementationEvent, ImplementationRecord, ReviewRecord, WorkflowMeta, WorkflowConfig, ModelConfig, AutomationConfig, ExecuteConfig, UIConfig, AgentConfig, ModelsConfig, PlanRecord, CloseRecord, WorkflowRecord, BrainstormRecord, WorkflowStatus, AutomationLevel

**Acceptance Criteria:**
- python3 -c "import json; s=json.load(open('schemas/workflow.schema.json')); assert len(s['$defs']) >= 24, f'Only {len(s[chr(36)+"defs"])} defs found'" succeeds
- All field names in the schema match the camelCase names used in the spec's record file example
- Enum $defs (TaskStatus, WorkflowStatus, AutomationLevel) use the exact string values from the spec

**Depends on:** task-1

### task-3: Type definitions in wflib/types.py

**Goal:** Create all dataclasses, enums, and stub serialization functions in wflib/types.py exactly matching the spec's wflib/types.py section. Every type is importable and constructable with defaults. Stub functions raise NotImplementedError.

**Files:**
- `docs/plans/wf-spec.md`

**Constraints:**
- Every dataclass from the spec's types.py section must be present with correct fields, types, and defaults: Task, Plan, Usage, ReportResult, TaskResult, DesignDecision, BrainstormRecord, ImplementationEvent, ImplementationRecord, ReviewRecord, WorkflowMeta, PlanRecord, CloseRecord, WorkflowRecord, ModelConfig, AutomationConfig, ExecuteConfig, UIConfig, AgentConfig, ModelsConfig, WorkflowConfig
- All three enums with exact string values: TaskStatus (pending/running/done/failed/skipped), WorkflowStatus (init/brainstorming/planning/implementing/reviewing/closing/done/failed), AutomationLevel (interactive/supervised/automatic)
- Implement the camelCase-to-snake_case and snake_case-to-camelCase conversion helpers described in the spec's JSON Naming Convention section
- Stub functions (record_from_json, record_to_json, plan_from_json, plan_to_json, validate_schema, extract_tool_call) must raise NotImplementedError with descriptive messages

**Acceptance Criteria:**
- from wflib.types import Plan, Task, WorkflowRecord, TaskStatus, WorkflowStatus, AutomationLevel, Usage, ReportResult, TaskResult, WorkflowConfig — all succeed
- Plan(goal='test', context='ctx', tasks=[]) constructs without error; WorkflowConfig() constructs with all defaults; Usage() constructs with zeros
- TaskStatus.PENDING.value == 'pending' and WorkflowStatus.IMPLEMENTING.value == 'implementing'
- Calling record_from_json({}) raises NotImplementedError

**Depends on:** task-1

### task-4: Test infrastructure

**Goal:** Create the shared test fixtures (conftest files), the subprocess helper (tests/util.py), and the deterministic mock agent for E2E tests. After this task, pytest can collect tests and the mock agent is a valid executable script.

**Files:**
- `docs/plans/wf-spec.md`

**Constraints:**
- tests/conftest.py must ensure sys.path includes the repo root so that `import wflib`, `import profiles`, `import adapters` work from any test file
- tests/e2e/conftest.py must provide a `project_from_fixture` fixture matching the spec: copies fixture's repo/ to tmpdir, runs git init + git add -A + git commit, makes mock_agent.py executable, sets WF_TEST_SCENARIO and WF_RESULTS_PATH env vars
- tests/e2e/mock_agent.py must match the spec's mock agent code: reads WF_TEST_SCENARIO env var, matches brief content against scenario entries, performs scripted file operations, writes results.json to WF_RESULTS_PATH, uses #!/usr/bin/env python3 shebang
- tests/util.py must provide a run_wf() function that spawns bin/wf as a subprocess with configurable cwd, stdin, env vars, and returns an object with stdout, stderr, returncode attributes

**Acceptance Criteria:**
- python3 -m pytest tests/ --collect-only runs without conftest load errors
- python3 -c "import ast; ast.parse(open('tests/e2e/mock_agent.py').read())" succeeds
- python3 -c "from tests.util import run_wf" succeeds

**Depends on:** task-1

### task-5: Module stubs for all Python modules

**Goal:** Create minimal stub files for every Python module in wflib/, profiles/, and adapters/ (excluding types.py which already has full stubs). Each module has its public function/class signatures from the spec, all raising NotImplementedError. Dataclasses defined in these modules are fully defined with fields. Import chains between modules work.

**Files:**
- `docs/plans/wf-spec.md`
- `docs/plans/implementation-tracker.md`

**Constraints:**
- Every public function and class listed in the spec for each module must have a stub — read each module's section in the spec carefully for the complete API surface
- All stubs raise NotImplementedError (not pass) so callers can distinguish 'not implemented' from 'silently does nothing'
- Dataclasses in non-types modules (ValidationResult in validate.py, GitResult in git.py, WorktreeInfo/MergeResult/WorkflowCloseResult in worktree.py, AgentResult in runner.py, ExecutionSummary in scheduler.py, ReviewResult/AutoReviewResult in review.py, UsageRow in render.py, Template in templates.py) must be fully defined with fields and defaults — these are data containers, not stubs
- Import chains must work: modules that import from wflib.types (most of them) or from each other (e.g., profiles/pi.py imports from adapters/, profiles/__init__.py references ModelsConfig from wflib.types) must have correct import statements
- profiles/__init__.py must contain: RunnerProfile Protocol class with all methods from the spec, BUILTIN_ALIASES dict, resolve_alias function stub, get_profile function stub

**Acceptance Criteria:**
- All modules importable: from wflib.config import resolve_config; from wflib.git import git, GitResult; from wflib.worktree import WorktreeInfo, MergeResult; from profiles import get_profile, RunnerProfile; from profiles.pi import PiProfile; from adapters.pi_json_mode import parse
- Stub functions raise NotImplementedError: e.g., calling resolve_config('.') raises NotImplementedError
- Dataclasses constructable: GitResult(ok=True, stdout='', stderr=''), ValidationResult(errors=[], warnings=[]), WorktreeInfo(path='/tmp', branch='test', main_branch='main')
- Import chain from profiles.pi works: PiProfile class exists and its methods raise NotImplementedError

**Depends on:** task-1, task-3

### task-6: E2E fixture data

**Goal:** Create all 9 E2E test fixture directories with structurally correct and scenario-appropriate plan.json, scenario.json, repo/ files, and expected/ stubs. Each fixture matches its scenario description from the spec's 'Scenarios Worth Encoding' table.

**Files:**
- `docs/plans/wf-spec.md`

**Constraints:**
- plan.json files must use camelCase field names matching $defs/Plan: goal, context, defaultModel, tasks with id/title/goal/files/constraints/acceptance/dependsOn/model/skills
- scenario.json files must match the mock agent contract from the spec: {"tasks": [{"match": "...", "operations": [...], "report_result": {"summary": "...", "notes": "..."}, "exit_code": 0}]}
- repo/ directories should be minimal but realistic — a small Python project (2-3 source files) that makes the scenario plausible
- expected/record.json should contain only the fields the test will assert on (partial match), expected/files.json lists files that should exist after execution, expected/git.json has branch/commit expectations
- Fixture content must be self-consistent: task IDs in scenario.json match plan.json, file operations in scenario.json reference files in repo/, dependency graphs match the scenario description

**Acceptance Criteria:**
- All plan.json files are valid JSON with correct Plan schema shape
- All scenario.json files are valid JSON with correct mock agent format
- All 9 fixture directories contain repo/, plan.json, scenario.json, and expected/ with record.json, files.json, git.json
- python3 -c "import json, glob; [json.load(open(f)) for f in glob.glob('tests/e2e/fixtures/*/plan.json')]" succeeds

**Depends on:** task-1

### task-7: Placeholder test files

**Goal:** Create all 22 test files with meaningful test method names matching the spec's test descriptions. Each file imports from its target module at the top level (verifying the import chain). All tests use unittest.skip. After this task, `python3 -m pytest tests/` runs with zero import errors, all tests skip, and total collected test count exceeds 50.

**Files:**
- `docs/plans/wf-spec.md`
- `docs/plans/implementation-tracker.md`

**Constraints:**
- Each test file must import from its target module at the top level (e.g., test_config.py does `from wflib.config import resolve_config`) — this is the import-chain verification that justifies the module stubs in task 5
- Use unittest.TestCase as the base class and unittest.skip for skip decorators — NOT pytest.mark.skip — for stdlib compatibility per the spec's 'No external test dependencies' requirement
- Test method names must be descriptive of what they will test in later phases, matching the spec's test descriptions (e.g., test_cycle_detection_raises_error, test_brief_includes_prior_work_summary, test_diamond_deps_ordering)
- E2E test files should have test methods for each scenario in the spec's fixture table (test_simple_split, test_linear_chain, test_diamond_deps, etc.)
- Each test file must have at minimum 3 test methods to ensure meaningful coverage skeleton — total across all 22 files must exceed 50

**Acceptance Criteria:**
- python3 -m pytest tests/ --collect-only discovers all 22 test files with zero import errors
- python3 -m pytest tests/ runs with all tests skipped, zero failures, zero errors
- python3 -m unittest discover tests/ also runs without errors (stdlib compatibility)
- Total collected test count exceeds 50

**Depends on:** task-4, task-5
