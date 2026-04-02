# `wf` - Complete Project Sketch

External CLI tool for structured AI development workflows - like git for version control or tmux for terminal multiplexing. Every phase of the workflow lifecycle is drivable from a bare terminal. Zero Python dependencies - stdlib only.

Harness wrappers (pi, Cursor, etc.) provide a richer UX (inline modes, live UI, per-turn usage tracking) but are never required. The CLI is the primary interface; harness integration is a convenience add-on.

A **workflow** is a single instance of the full development lifecycle: init → brainstorm → plan → implement → review → close. Each workflow produces two artifacts: changes to the project codebase, and a **record file** that captures the data and metadata of every phase. Both are committed to version control.

---

## V1 Scope Decisions

The following scope and platform decisions apply to v1. They are referenced throughout the sketch.

**Phases:** All phases are first-class in v1 — init, brainstorm, plan, execute, review, close. Brainstorm is fully supported including `wf brainstorm` as a spawned agent session with a well-crafted `prompts/brainstorm.md` system prompt. Planned future extensions to the brainstorm phase are a primary motivator for this tool.

**Harnesses:** Pi and mock profiles are fully functional in v1. The Claude Code profile ships as a documented skeleton with `NotImplementedError` on tmux and session parsing methods — a clear extension point, not a gap.

**Platform:** POSIX-only (Linux, macOS). No Windows support. `os.replace` atomicity, git worktree symlinks, tmux, `#!/usr/bin/env python3` shebangs, and bash wrapper scripts all assume POSIX.

**External tools:**

| Tool | Required? | Behavior when absent |
|------|-----------|---------------------|
| `python3` ≥ 3.12 | **Required** | Hard fail with version check at startup |
| `git` ≥ 2.20 | **Required** | Hard fail at `wf init` |
| `tmux` ≥ 3.0 | **Optional** | If `config.ui.tmux` is true but tmux is not found, warn to stderr and fall back to headless mode. Never hard fail on missing tmux. |
| Agent binary (`pi`, `claude`, etc.) | **Required for its profile** | Hard fail with clear message if the configured profile's binary is not on PATH |

**Error output:** All commands emit `{"error": "<message>"}` JSON to stdout on exit code 1. Exit code 2 (bad arguments) uses argparse-style usage errors on stderr.

**Config validation:** Unknown keys and invalid values in config files are hard errors. `wf init` and `wf config set` refuse to proceed. No forward-compatibility leniency — err on the side of safety and least surprise.

**Legacy coexistence:** No migration from the legacy planner's `docs/plans/`, `.state.json`, or `.plan-init-*.json` files. The old planner and `wf` coexist — they use different directories. No converter tool is provided.

**Merge conflict resolution during execution:** When a task worktree merge-back hits a conflict, `wf` automatically spawns a conflict resolution agent (using `prompts/merge-resolver.md`) before marking the task as failed. Only if the agent fails to resolve all conflicts is the task marked `failed` with the worktree preserved. This automatic resolution is a primary motivator for this tool.

**Concurrency tie-breaking:** When multiple tasks become ready simultaneously and the concurrency limit is reached, tasks are queued in lexicographic order by `task.id`. Deterministic and simple; no priority system in v1.

---

## Repository Structure

```
wf/
├── bin/
│   └── wf                            # #!/usr/bin/env python3 - CLI entry point
│
├── schemas/
│   └── workflow.schema.json           # Single JSON Schema - full record + $defs for Plan, Brainstorm, Task, etc.
│
├── prompts/
│   ├── brainstorm.md                 # System prompt for brainstorm phase
│   ├── planning-context.md           # Injected when agent enters planning mode
│   ├── implementer.md                # System prompt for implementation subagents
│   ├── reviewer.md                   # System prompt for code review subagents
│   ├── reviewer-with-plan.md         # System prompt for auto-review (review + submit_plan)
│   └── merge-resolver.md             # System prompt for conflict resolution agents
│
├── templates/
│   ├── brainstorm.md                 # Reusable: iterative brainstorming with pros/cons
│   ├── check-implementation.md       # Reusable: quality check recent work
│   ├── execute-plan-step.md          # Reusable: implement a single plan step
│   └── write-plan-to-file.md         # Reusable: write plan to docs/plans/
│
├── profiles/
│   ├── __init__.py                    # Profile interface (RunnerProfile protocol) + registry
│   ├── pi.py                         # Pi runner profile (default)
│   ├── claude_code.py                # Claude Code runner profile
│   └── mock.py                       # Mock profile for E2E tests
│
├── adapters/
│   ├── __init__.py
│   ├── pi_json_mode.py               # Parser: pi --mode json stdout → results dict
│   ├── pi_session.py                 # Parser: pi session .jsonl → results dict
│   └── claude_stream_json.py         # Parser: claude --output-format stream-json → results dict
│
├── tools/
│   ├── mcp_server.py                 # MCP server exposing report_result, submit_plan, record_brainstorm
│   │                                 #   (for Claude Code and other MCP-based harnesses)
│   └── pi_extensions/                # Pi-native tool extensions (TypeScript)
│       ├── report-result-tool.ts
│       ├── submit-plan-tool.ts
│       └── record-brainstorm-tool.ts
│
├── wflib/
│   ├── __init__.py
│   ├── types.py                      # Data classes + JSON schema validation + message extraction
│   ├── config.py                     # Configuration loading, merging, resolution (TOML)
│   ├── record.py                     # Workflow record file I/O (the central state)
│   ├── validate.py                   # Plan validation (deps, cycles)
│   ├── brief.py                      # Deterministic task brief assembly
│   ├── scheduler.py                  # DAG scheduler (asyncio, pool-based)
│   ├── task_executor.py              # Per-task lifecycle: worktree → brief → spawn → merge → cleanup
│   ├── runner.py                     # Agent subprocess spawning (profile-driven, headless + tmux)
│   ├── tmux.py                       # Tmux pane/window management
│   ├── git.py                        # Git wrapper
│   ├── worktree.py                   # Worktree create / setup / merge / cleanup
│   ├── review.py                     # Diff context building + review orchestration
│   ├── render.py                     # Markdown + usage table + status rendering
│   ├── templates.py                  # Template discovery, loading, rendering
│   ├── completions.py                # Shell completion script generation + dynamic completion callback
│   └── log.py                        # Debug logging
│
├── tests/
│   ├── unit/
│   │   ├── test_types.py
│   │   ├── test_config.py
│   │   ├── test_validate.py
│   │   ├── test_brief.py
│   │   ├── test_render.py
│   │   ├── test_templates.py
│   │   ├── test_completions.py
│   │   ├── test_profiles.py
│   │   └── test_help.py
│   ├── integration/
│   │   ├── test_record.py
│   │   ├── test_worktree.py
│   │   ├── test_git.py
│   │   └── test_tmux.py
│   ├── e2e/
│   │   ├── mock_agent.py
│   │   ├── conftest.py
│   │   ├── test_happy_path.py
│   │   ├── test_failures.py
│   │   ├── test_recovery.py
│   │   ├── test_review.py
│   │   └── fixtures/
│   │       ├── simple-split/
│   │       ├── linear-chain/
│   │       ├── diamond-deps/
│   │       ├── task-failure/
│   │       ├── merge-conflict/
│   │       ├── merge-conflict-unresolvable/
│   │       ├── review-fixup/
│   │       ├── crash-recovery/
│   │       └── full-lifecycle/
│   ├── profile/
│   │   ├── test_pi_profile.py
│   │   └── test_claude_code_profile.py
│   └── adapter/
│       ├── test_pi_json_mode.py
│       ├── test_pi_session.py
│       └── test_claude_stream_json.py
│
└── README.md
```

---

## Technology Choices & Dependencies

### Why Python

The `wf` codebase is ~2500 lines of glue: dataclasses, JSON I/O, subprocess orchestration, DAG scheduling, git/tmux wrappers, and text rendering. Python's stdlib covers every one of these with purpose-built modules. There is no compile step, no bundler, no runtime to manage - `#!/usr/bin/env python3` and it runs. Requires Python 3.12+.

The pi wrapper extension remains TypeScript (it's a pi extension, it has to be). The two-language split is clean: Python owns all workflow logic, TypeScript owns only harness-specific UI/events.

### Zero External Dependencies

**`wf` uses only Python stdlib. No pip install, no venv, no vendored packages.**

Every need maps to a stdlib module:

| Need | Stdlib module | Notes |
|------|--------------|-------|
| DAG scheduling | `graphlib.TopologicalSorter` (3.9+) | Incremental parallel mode: `prepare()` → `get_ready()` → `done()` → `get_ready()`. Exactly the pool-based scheduler this sketch describes. `skip_dependents` / `reset_ready_skipped` still need manual implementation (TopologicalSorter doesn't handle failure propagation), but core readiness tracking is built in. |
| Async subprocess | `asyncio.create_subprocess_exec` | Full stdout/stderr capture, concurrent spawning, `asyncio.wait_for()` for timeouts. Sufficient for managing tmux + headless agent processes. |
| Data types | `dataclasses` | Maps 1:1 to every type in `types.py`. Optional fields, defaults, `field(default_factory=...)` for mutable defaults. |
| JSON I/O | `json` | Record file read/write, schema extraction, CLI output. |
| CLI | `argparse` | Subcommands, flags, help text. Covers the full `wf` CLI surface. |
| Enums | `enum.Enum` | `TaskStatus`, `WorkflowStatus`, `AutomationLevel`. |
| Path handling | `pathlib` | Cleaner than the TS `path.resolve`/`path.relative` equivalents. |
| Subprocess (sync) | `subprocess` | Git and tmux commands via `subprocess.run()`. |
| Temp files | `tempfile` | Wrapper scripts, agent prompt files, atomic writes. |
| Atomic writes | `tempfile` + `os.replace` | Write to `NamedTemporaryFile`, `os.replace()` is atomic on POSIX. |
| Config parsing | `tomllib` (3.11+) | TOML config file reading. Read-only (users edit config files directly or via `wf config set`). |
| Regex | `re` | Summary fallback extraction, frontmatter parsing. |

### Why Not `jsonschema`

The `jsonschema` package (Python's main JSON Schema validator) pulls in 4 transitive deps: `attrs`, `jsonschema-specifications`, `referencing`, and `rpds-py`. The last one is a compiled Rust extension - unvendorable, platform-specific, kills the zero-dep story.

But we don't need it. The JSON Schema files in `schemas/` serve **two distinct purposes**, and neither requires a validation library:

1. **Tool registration contracts** - `wf schema --component plan` outputs `$defs/Plan` for harness wrappers to register tools. This is JSON file reading + `$ref` inlining: pure dict manipulation, ~40 lines.

2. **Runtime input validation** - when `wf submit-plan` receives JSON from stdin, the dataclass constructors ARE the validation. `Plan.from_dict(data)` either succeeds or raises with a clear error. A thin validation layer (~80-100 lines in `types.py`) checks required keys exist, values have the right types, and arrays meet minimum lengths before construction, producing good error messages.

This is the better design anyway: the dataclasses are the runtime source of truth (they do validation, construction, serialization), and the JSON Schema file is the published contract for external consumers (tool registration, harness wrappers). Both are hand-maintained to describe the same structures. Drift risk is low because the schema is small and stable, and the E2E tests exercise the full round-trip (tool call → schema validation → dataclass construction → record file → schema-compliant output). No divergence risk between a schema file and a separate validation library's interpretation of it.

### Why TOML for Configuration

Configuration files (`~/.config/wf/config.toml`, `.wf/config.toml`) use TOML. Python 3.11+ includes `tomllib` in stdlib (read-only), so this adds zero external dependencies. TOML is the right fit because:

- **Human-editable** - config files are primarily hand-edited. TOML is cleaner than JSON (comments, no trailing comma issues, no quoting keys). INI can't represent the nested structure needed for per-phase settings.
- **Read-only is sufficient** - `tomllib` only reads TOML, but that's all we need. Users edit config files directly (or `wf config set` does targeted string manipulation on simple `key = value` lines). The record file stores the resolved snapshot as JSON - no TOML writing needed.
- **Proven pattern** - `pyproject.toml` established TOML as Python's config format. Users expect it.

The alternative would be JSON config files (fully stdlib), but JSON without comments is hostile for config that users are meant to customize. TOML with `tomllib` is the better tradeoff.

For `wf config set`, writing is simple string manipulation - find the `[section]` header, find or append the `key = value` line. The config structure is flat within sections (no nested tables, no arrays of tables), so this is ~30 lines of code, not a TOML serializer.

### Why Not PyYAML

Template frontmatter is trivially simple - just `key: value` pairs between `---` delimiters:

```yaml
---
description: Quality check a recent implementation
---
```

No nested YAML, no lists, no anchors. ~10 lines of string splitting in `templates.py`:

```python
def parse_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith('---\n'):
        return {}, content
    end = content.find('\n---\n', 4)
    if end == -1:
        return {}, content
    meta = {}
    for line in content[4:end].split('\n'):
        k, _, v = line.partition(':')
        if v:
            meta[k.strip()] = v.strip()
    return meta, content[end + 5:]
```

A YAML library would be pure overhead for this.

### How `graphlib.TopologicalSorter` Maps to the Scheduler

The current TS scheduler implements pool-based DAG execution with manual readiness tracking (`getReadyTasks`, `skipDependents`, `resetReadySkipped`). Python's stdlib `TopologicalSorter` handles the core scheduling natively:

```python
from graphlib import TopologicalSorter

# Build graph: node -> set of predecessors
graph = {t.id: set(t.depends_on) for t in plan.tasks}
ts = TopologicalSorter(graph)
ts.prepare()

while ts.is_active():
    for task_id in ts.get_ready():       # returns newly-unblocked tasks
        # spawn up to concurrency limit
        ...
    # when a task completes:
    ts.done(completed_task_id)            # unlocks dependents automatically
```

The failure-handling logic (`skip_dependents` with transitive BFS closure, `reset_ready_skipped` iterating until stable) still needs manual implementation - `TopologicalSorter` doesn't model failure. But the happy-path scheduling ("which tasks are ready given what's done") is one stdlib call.

### Install Flow

```
wf/
├── bin/wf              # #!/usr/bin/env python3 - CLI entry point
├── wflib/              # the library (pure Python, stdlib only)
├── profiles/           # runner profiles (one per harness: pi, claude-code, mock)
├── adapters/           # output format parsers (shared across profiles)
├── tools/              # subagent tool implementations (MCP server + pi extensions)
├── schemas/            # JSON Schema files (read-only contracts)
├── prompts/            # system prompts (markdown)
└── templates/          # shipped default templates (markdown)
```

Install: clone/copy the `wf/` directory + symlink `bin/wf` onto `$PATH`. No `pip install`, no `venv`, no `setup.py`, no `pyproject.toml`. The `#!/usr/bin/env python3` shebang finds Python 3.12+.

### What Lives Where

All workflow logic in the `wf/` repository works without pi, Cursor, or any specific agent harness installed. The CLI drives the full lifecycle: `wf init` → `wf brainstorm` → `wf plan` → `wf execute` → `wf review` → `wf close`.

Harness-specific wrapper code lives where each harness expects it - maintained in-place, not tracked in the `wf` repo. For pi, that's `~/.pi/agent/extensions/wf/`. For Cursor, it would be wherever Cursor loads custom tool configs. Each wrapper is a small amount of glue code (~300 lines for pi) that calls the `wf` CLI and reads record files.

| Artifact | Lives in `wf/` repo | Lives in harness location |
|----------|---------------------|---------------------------|
| CLI (`bin/wf`) | ✓ | |
| Core library (`wflib/`) | ✓ | |
| Runner profiles (`profiles/`) | ✓ | |
| Output adapters (`adapters/`) | ✓ | |
| Subagent tools (`tools/`) | ✓ (MCP server + pi extensions) | |
| JSON Schema (`schemas/`) | ✓ | |
| System prompts (`prompts/`) | ✓ | |
| Templates (`templates/`) | ✓ | |
| Pi wrapper extension (`index.ts`) | | `~/.pi/agent/extensions/wf/` |
| Cursor wrapper | | wherever Cursor expects it |

**Runner profiles, adapters, and tools are the designated harness-specific zones within the core `wf` repo.** Each profile (`profiles/pi.py`, `profiles/claude_code.py`) encodes everything needed to drive one agent harness: command construction, output format selection, and tool loading mechanism. Adapters (`adapters/`) are pure output parsers - shared across profiles where formats overlap. Tools (`tools/`) provide the subagent-side implementations: pi extensions (TypeScript, loaded via `-e`) and an MCP server (Python, for Claude Code and other MCP-based harnesses). All three ship with `wf` because the runner needs them at execution time.

**The only harness-specific code that lives outside the `wf` repo** is each harness's UI wrapper. For pi, that's `~/.pi/agent/extensions/wf/index.ts` - commands, event hooks, status bar, widget, autocompletions, **and tool handlers for inline sessions**. This is still UI glue (no workflow logic, no subprocess management): the tool handlers simply pipe `submit_plan` / `record_brainstorm` tool calls to the `wf` CLI and return its response. All validation and record writes remain in the CLI. For another harness, the equivalent code would live wherever that harness expects custom integrations.

The `wf` repo is "harness-agnostic" in the sense that all workflow logic (scheduling, worktrees, merging, record management, brief assembly, validation, rendering) has zero harness knowledge. The runner calls `profile.build_headless_cmd()` and `profile.parse_headless_output()` - it never imports pi-specific or claude-specific code directly. Adding a new harness means adding one profile file, one adapter (if the output format is new), and one tool loading mechanism (if neither pi extensions nor MCP fit).

### Testing

Tests use `unittest` (stdlib). Run with `python3 -m pytest tests/` if pytest is available, or `python3 -m unittest discover tests/` with zero deps. No external test dependencies.

Three tiers: unit tests for pure functions, integration tests for git/filesystem operations, and end-to-end tests that run full workflows against mini fake projects using a mock agent. The E2E tier is the most important - it's where scheduling, state transitions, merging, recovery, and the review cycle get tested as a system.

#### Test Structure

```
tests/
├── unit/                    # Pure function tests - no I/O, no subprocess
│   ├── test_types.py        # Dataclass construction, serialization, extract_tool_call
│   ├── test_config.py       # Config loading, merging, resolution, precedence chain
│   ├── test_validate.py     # Dep refs, cycle detection
│   ├── test_brief.py        # Brief assembly from plan + results
│   ├── test_render.py       # Markdown rendering, usage tables, status formatting
│   ├── test_templates.py    # Frontmatter parsing, variable substitution, discovery
│   ├── test_completions.py  # Generated script content, dynamic completion output
│   ├── test_profiles.py     # Profile interface compliance, command construction, model resolution, tool paths
│   └── test_help.py         # Help topic lookup, prefix matching, content checks
│
├── integration/             # Tests that touch git and filesystem, but not agents
│   ├── test_record.py       # Create, load, save, atomic writes, phase transitions
│   ├── test_worktree.py     # Create, symlink, commit, merge-back, cleanup
│   └── test_git.py          # Wrapper sanity: is_clean, get_branch, get_head
│
├── e2e/                     # Full workflow tests with mock agent
│   ├── mock_agent.py        # Deterministic agent binary (see below)
│   ├── conftest.py          # Fixtures: project setup, mock-agent on PATH
│   ├── test_happy_path.py   # Simple split, linear chain, diamond deps, full lifecycle
│   ├── test_failures.py     # Task failure + skip, merge conflict + auto-resolution, worktree preserved
│   ├── test_recovery.py     # Crash recovery, resume midway
│   ├── test_review.py       # Auto-review with fixup plan, review with no issues
│   └── fixtures/            # Mini fake projects (see below)
│       ├── simple-split/
│       ├── linear-chain/
│       ├── diamond-deps/
│       ├── task-failure/
│       ├── merge-conflict/
│       ├── merge-conflict-unresolvable/
│       ├── review-fixup/
│       ├── crash-recovery/
│       └── full-lifecycle/
│
├── profile/                 # Profile integration tests with recorded harness output
│   ├── test_pi_profile.py   # Command construction + recorded output through pi adapters
│   └── test_claude_code_profile.py  # Command construction + recorded output through claude adapter
│
└── adapter/                 # Adapter unit tests with recorded output fixtures
    ├── test_pi_json_mode.py # Feed recorded pi --mode json stdout, verify results dict
    ├── test_pi_session.py   # Feed recorded session .jsonl, verify results dict
    └── test_claude_stream_json.py  # Feed recorded stream-json output, verify results dict
```

#### Unit Tests

The pure-function modules (`validate.py`, `brief.py`, `types.py`, `config.py`, `render.py`, `templates.py`, `completions.py`, `help.py`) are straightforward to test - data in, data out, no mocking needed. These tests run in milliseconds and catch regressions in plan validation, brief content, tool call extraction, and rendering.

#### Integration Tests

The git/filesystem modules (`record.py`, `worktree.py`, `git.py`) need real git repos. Each test creates a temporary repo in `tmp_path`, runs operations, and asserts on git state (branches, commits, file contents, working tree cleanliness). These tests use real git but no agent subprocesses.

Key scenarios for worktree integration tests: create + merge-back with clean rebase, merge-back with conflict (verify `MergeResult.conflicts` populated and `resolution_attempted` / `resolution_succeeded` fields set), commit exclusion of `docs/workflows/` directory, `.worktree-setup` hook execution, symlink creation for `node_modules`/`.venv`/etc.

Key scenarios for record integration tests: atomic write survives simulated crash (write, verify tmp doesn't linger), concurrent-safe with single writer (verify `os.replace` semantics), round-trip fidelity (create → save → load → compare).

#### End-to-End Tests

The E2E tier runs full `wf` CLI workflows against mini fake projects. The critical enablers:

1. **`--profile mock`** - swaps the real agent profile for a deterministic mock profile
2. **`results.json` contract** - the mock just writes that file + makes file changes; no need to emulate a real agent harness
3. **`--no-tmux`** - strips away tmux infrastructure for focused logic tests
4. **Record file as assertion surface** - every state transition is captured in one file
5. **Git state as assertion surface** - commits, branches, file contents

##### The Mock Agent

A Python script that reads a scenario file (via `WF_TEST_SCENARIO` env var), matches the current task from the prompt/brief content, executes scripted file operations, and writes `results.json` in the location `wf` expects.

```python
#!/usr/bin/env python3
"""mock-agent - deterministic agent for E2E tests.

Reads a scenario file mapping task briefs → file operations + results.
The scenario file is a JSON array of entries, each with:
  - match: string to find in the brief (identifies which task this is)
  - operations: [{type: "write", path: "...", content: "..."},
                 {type: "delete", path: "..."}]
  - report_result: {summary: "...", notes: "..."}
  - exit_code: int (default 0)
"""
import sys, json, os

scenario = json.load(open(os.environ["WF_TEST_SCENARIO"]))
brief = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
results_path = os.environ["WF_RESULTS_PATH"]  # where wf expects results.json

for entry in scenario["tasks"]:
    if entry["match"] in brief:
        # Execute scripted file operations in cwd
        for op in entry.get("operations", []):
            if op["type"] == "write":
                os.makedirs(os.path.dirname(op["path"]), exist_ok=True)
                with open(op["path"], "w") as f:
                    f.write(op["content"])
            elif op["type"] == "delete":
                os.remove(op["path"])

        # Write results.json
        results = {
            "exitCode": entry.get("exit_code", 0),
            "messages": [{"role": "assistant", "content": [
                {"type": "toolCall", "name": "report_result",
                 "arguments": entry["report_result"]}
            ]}],
            "usage": {"input": 1000, "output": 500, "cacheRead": 0,
                      "cacheWrite": 0, "cost": 0.01, "turns": 1},
            "model": "mock", "provider": "mock"
        }
        with open(results_path, "w") as f:
            json.dump(results, f)

        sys.exit(entry.get("exit_code", 0))

# No match - simulate agent that didn't understand its task
results = {"exitCode": 1, "messages": [], "usage": {"input": 0, "output": 0,
           "cacheRead": 0, "cacheWrite": 0, "cost": 0, "turns": 0}}
with open(results_path, "w") as f:
    json.dump(results, f)
sys.exit(1)
```

The mock operates at the `results.json` level, not the agent CLI level. It does not need to emulate pi's `--mode json` output, session files, or flag conventions - those are the profile's and adapter's concern, tested separately in `tests/profile/` and `tests/adapter/`. The mock profile (`profiles/mock.py`) wraps this script and presents it through the standard `RunnerProfile` interface, so the runner and scheduler are completely unaware they're running against a mock. This keeps E2E tests focused on workflow engine correctness.

##### Mini Fake Projects (Fixtures)

Each fixture is a small, self-contained scenario:

```
fixtures/simple-split/
├── repo/                    # Files to initialize the git repo with
│   └── src/
│       └── monolith.py      # "the codebase" - just enough to be real
├── plan.json                # Pre-built plan to feed to wf submit-plan
├── scenario.json            # Mock agent script: per-task operations + results
└── expected/                # Assertions
    ├── record.json          # Partial match against final record state
    ├── files.json           # Which files exist with what content after execution
    └── git.json             # Expected branch state, commit count, commit messages
```

The `conftest.py` fixture sets up each test:
1. Copy `repo/` to a temp directory
2. `git init` + `git add -A` + `git commit`
3. Make `mock_agent.py` executable and set env vars
4. Return the project path

The test function then drives the CLI:
1. `wf init <name> --cwd <project> --no-worktree`
2. `cat plan.json | wf submit-plan <name> --cwd <project>`
3. `wf execute <name> --cwd <project> --profile mock --no-tmux`
4. Assert on the record file and git state

##### Scenarios Worth Encoding

| Fixture | What it tests | Key assertions |
|---------|--------------|----------------|
| **simple-split** | 2 independent tasks, both succeed | Both tasks `done`, files from both present, 2 task commits in git log |
| **linear-chain** | A→B→C sequential deps | Execution order matches deps, B's brief includes A's summary, C's brief includes A+B |
| **diamond-deps** | A→{B,C}→D | D runs only after both B and C are `done`, never starts early |
| **task-failure** | Task-2 fails (exitCode 1), task-3 depends on task-2 | task-2 `failed`, task-3 `skipped`, task-1 (independent) `done`, task-4 (independent) `done` |
| **failure-recovery** | Re-execute after task-failure, task-2 now succeeds | task-2 flips to `done`, task-3 un-skips and runs, all tasks `done` |
| **merge-conflict** | Two parallel tasks edit the same line | One merges clean, the other triggers auto-resolution agent. Mock resolves successfully, both tasks `done`, `mergeResolveStart` + `mergeResolveComplete` events in timeline |
| **merge-conflict-unresolvable** | Two parallel tasks make incompatible changes | Resolution agent fails to resolve, task `failed` with worktree preserved, `mergeResolveFailed` event, conflict files recorded |
| **review-fixup** | Mock reviewer calls `submit_plan` with fixup tasks | `reviews[0].fixupPlan` populated, fixup tasks executed, `reviews[0].fixupImplementation.tasks` all `done` |
| **review-clean** | Mock reviewer finds no issues, does NOT call `submit_plan` | `reviews[0].findingsActionable` is `false`, no fixup plan |
| **crash-recovery** | Record pre-populated with tasks stuck in `running` + `activeResources` | `wf recover` resets to `pending`, cleans orphaned worktrees, appends `crashRecovery` event |
| **resume-midway** | Record with 3/5 tasks `done`, 2 still `pending` | Only 2 tasks execute, final record has all 5 `done` |
| **model-resolution** | Plan has `defaultModel`, one task overrides, execute with `--model` flag | Each task's brief contains the correct model per precedence chain |
| **config-resolution** | Init with user + project config + `--set` overrides | Record's `workflow.config` matches expected merge result; execution uses snapshotted settings |
| **full-lifecycle** | Init → submit-plan → execute → auto-review (no issues) → close | Record walks through every status: `init`→`implementing`→`reviewing`→`done`, close has `mergeResult: clean` |
| **worktree-isolation** | Execute with worktrees enabled | Task changes happen in worktrees, merge back to main, worktrees cleaned up, `activeResources` empty after |

##### Fixture Design Principles

Keep projects minimal - a fixture's `repo/` should have just enough files to exercise the scenario. A 3-file Python project is plenty. The point is testing `wf`'s orchestration, not compiling real software.

Keep plans small - 2-5 tasks per fixture. Enough to test the scheduling pattern, not so many that the scenario is hard to reason about.

Make scenario.json self-documenting - each entry's `match` string ties it to a specific task ID or title in the plan, and its `operations` list shows exactly what "the agent did." A reader can understand the full scenario from this one file.

Assertions check the record file and git state, not intermediate artifacts. The record file captures the complete workflow history; git captures the actual code changes. Between the two, every observable outcome is covered.

##### E2E Test Example

```python
def test_diamond_deps(project_from_fixture):
    """A→{B,C}→D: D must wait for both B and C."""
    project = project_from_fixture("diamond-deps")

    # Submit plan
    run_wf(f"init test --cwd {project} --no-worktree")
    run_wf(f"submit-plan test --cwd {project}",
           stdin=open(project / "_fixtures/plan.json"))

    # Execute with mock agent
    result = run_wf(
        f"execute test --cwd {project} --profile mock --no-tmux --no-worktrees",
        env={"WF_TEST_SCENARIO": str(project / "_fixtures/scenario.json")}
    )
    assert result.returncode == 0

    # Load final record
    record = json.loads((project / "docs/workflows/test.json").read_text())
    tasks = record["implementation"]["tasks"]

    # All tasks succeeded
    for tid in ["task-1", "task-2", "task-3", "task-4"]:
        assert tasks[tid]["status"] == "done"

    # D (task-4) started after both B (task-2) and C (task-3) completed
    events = record["implementation"]["events"]
    task4_start = next(e for e in events if e["event"] == "taskStart" and e["task"] == "task-4")
    task2_done = next(e for e in events if e["event"] == "taskComplete" and e["task"] == "task-2")
    task3_done = next(e for e in events if e["event"] == "taskComplete" and e["task"] == "task-3")
    assert task4_start["t"] > task2_done["t"]
    assert task4_start["t"] > task3_done["t"]
```

#### Profile Tests

Each runner profile is tested for **interface compliance and command construction**. Unit tests in `tests/unit/test_profiles.py` verify that every profile:

- Implements the full `RunnerProfile` protocol
- Produces correct CLI argument lists for headless and tmux modes (`build_headless_cmd`, `build_tmux_wrapper`)
- Resolves tool extension/MCP paths correctly (`get_tool_paths`)
- Selects the correct adapter for its output format
- Resolves model names deterministically (`resolve_model`): shorthands, canonical names, harness-specific translations, passthrough for unknown names, clear errors for unavailable models
- Lists supported models (`list_models`)

These are pure-function tests - they assert on the returned command lists, paths, and model strings without spawning any processes. They catch regressions like a missing flag, a wrong extension path, or a model name that resolves to the wrong harness identifier.

Integration tests in `tests/profile/` go further: feed recorded real output through the profile's adapter and verify the extracted `results.json` matches expectations. For example, `test_pi_profile.py` captures actual pi `--mode json` stdout and session `.jsonl` files from real runs, commits them as fixtures, and verifies the pi profile's adapter produces correct results. `test_claude_code_profile.py` does the same with recorded `--output-format stream-json` output.

These tests are isolated from the E2E tier. If a harness's output format changes, only the profile, its adapter, and their tests need updating - nothing in `wflib/` is affected.

#### Adapter Tests

The output adapters (`adapters/pi_json_mode.py`, `adapters/pi_session.py`, `adapters/claude_stream_json.py`) are also tested independently in `tests/adapter/` with recorded fixtures. This is useful for adapters shared across profiles and for verifying the parsing logic in isolation from command construction.

#### What About Tmux?

Tmux is excluded from E2E tests (`--no-tmux` always). Tmux adds real process management complexity - pane creation, polling, exit-code file detection, pane existence fallback - that is orthogonal to workflow correctness. Test tmux integration separately with focused integration tests in `tests/integration/test_tmux.py` that verify: pane creation, execution window reuse, exit-code file polling, pane-gone fallback detection. These can use `tmux` directly in a test tmux server (`tmux -L test-server`) to avoid interfering with the user's session.

---

## The Workflow Record File

Single canonical source of truth per workflow. Lives at `docs/workflows/<name>.json` in the project repo. Grows as phases complete. Replaces all scattered state files from the legacy planner (`docs/plans/<id>.json`, `<id>.state.json`, `.plan-init-*.json`, `~/.pi/plan-history.jsonl`).

Used for: audit, resume, error recovery, debugging, cost tracking, history. Any part of the system reads this one file to understand the workflow's current state.

### Full Structure

```json
{
  "schemaVersion": 1,
  "workflow": {
    "id": "a1b2",
    "name": "auth-refactor",
    "createdAt": "2026-04-01T10:00:00Z",
    "status": "implementing",
    "project": "/home/user/myproject",
    "sourceBranch": "main",
    "sourceCommit": "abc1234def5678",
    "worktree": "/home/user/myproject-wf-auth-refactor",
    "config": {
      "model": {
        "brainstorm": "claude-sonnet-4-5",
        "plan": "claude-sonnet-4-5",
        "implement": "claude-sonnet-4-5",
        "review": "claude-sonnet-4-5",
        "fixup": "claude-sonnet-4-5",
        "close": "claude-sonnet-4-5"
      },
      "automation": {
        "brainstorm": "interactive",
        "plan": "interactive",
        "implement": "supervised",
        "review": "automatic",
        "close": "automatic"
      },
      "execute": {
        "concurrency": 4,
        "worktrees": true,
        "autoReview": true
      },
      "ui": {
        "autoClose": 30,
        "tmux": true
      },
      "agent": {
        "profile": "pi",
        "cmd": null
      },
      "models": {
        "aliases": {"fast": "claude-haiku-4-5", "default": "claude-sonnet-4-5"},
        "profiles": {}
      }
    }
  },

  "brainstorm": {
    "recordedAt": "2026-04-01T10:30:00Z",
    "motivation": "Auth module is 2000 lines, mixes JWT validation and session management. Every change risks breaking both.",
    "solution": "Split into three modules: token (JWT), session (cookie/session store), middleware (Express integration). Clean interfaces between them.",
    "designDecisions": [
      {
        "decision": "Use visitor pattern for token validation",
        "rationale": "Multiple token types (JWT, API key, service token) need different validation logic. Visitor lets us add types without modifying the validator core."
      },
      {
        "decision": "Session module owns the Redis connection",
        "rationale": "Currently shared global. Isolating it in session module makes testing possible and removes hidden coupling."
      }
    ],
    "usage": {
      "model": "claude-sonnet-4-5",
      "input": 45000,
      "output": 8000,
      "cacheRead": 12000,
      "cacheWrite": 5000,
      "cost": 0.082,
      "turns": 4
    }
  },

  "plan": {
    "recordedAt": "2026-04-01T11:00:00Z",
    "goal": "Split auth module into token, session, and middleware",
    "context": "Express app, TypeScript strict mode, existing tests in tests/auth/. The auth.ts file is the main target - everything else imports from it.",
    "defaultModel": "claude-sonnet-4-5",
    "tasks": [
      {
        "id": "task-1",
        "title": "Extract token module",
        "goal": "Move all JWT and token validation logic from auth.ts into a new src/token.ts module with clean exports.",
        "files": ["src/auth.ts", "tests/auth/token.test.ts"],
        "constraints": ["Use visitor pattern for token type dispatch", "Preserve all existing public function signatures as re-exports from auth.ts during migration"],
        "acceptance": ["tsc compiles", "All existing token tests pass", "src/token.ts exists with Token type exports"],
        "dependsOn": [],
        "model": null,
        "skills": null
      }
    ],
    "usage": {
      "model": "claude-sonnet-4-5",
      "input": 32000,
      "output": 6000,
      "cacheRead": 8000,
      "cacheWrite": 3000,
      "cost": 0.055,
      "turns": 3
    }
  },

  "implementation": {
    "startedAt": "2026-04-01T11:05:00Z",
    "completedAt": "2026-04-01T11:42:00Z",
    "baseCommit": "def5678abc1234",
    "activeResources": {},
    "events": [
      {"t": "2026-04-01T11:05:00Z", "event": "taskStart", "task": "task-1", "worktree": "/home/user/myproject-wf-a1b2-task-1"},
      {"t": "2026-04-01T11:18:00Z", "event": "taskComplete", "task": "task-1", "status": "done"},
      {"t": "2026-04-01T11:18:01Z", "event": "mergeStart", "task": "task-1"},
      {"t": "2026-04-01T11:18:03Z", "event": "mergeComplete", "task": "task-1"},
      {"t": "2026-04-01T11:18:04Z", "event": "worktreeCleanup", "task": "task-1"}
    ],
    "tasks": {
      "task-1": {
        "status": "done",
        "startedAt": "2026-04-01T11:05:00Z",
        "completedAt": "2026-04-01T11:18:00Z",
        "exitCode": 0,
        "brief": "# Task: Extract token module\n\n## Context\nExpress app, TypeScript strict mode...\n\n## Goal\nMove all JWT and token validation logic...",
        "summary": "Extracted token module with visitor-based validation. All tests pass.",
        "filesChanged": ["src/token.ts", "src/auth.ts", "tests/auth/token.test.ts"],
        "diffStat": " 3 files changed, 120 insertions(+), 45 deletions(-)",
        "notes": "",
        "error": null,
        "worktreePath": null,
        "worktreePreserved": false,
        "sessionFile": null,
        "usage": {
          "model": "claude-sonnet-4-5",
          "input": 23000,
          "output": 5400,
          "cacheRead": 8200,
          "cacheWrite": 3100,
          "cost": 0.045,
          "turns": 3
        }
      }
    }
  },

  "reviews": [
    {
      "recordedAt": "2026-04-01T11:45:00Z",
      "baseCommit": "def5678abc1234",
      "reviewText": "Found 2 issues: (1) token.ts duplicates the error formatting logic from auth.ts instead of extracting shared utility, (2) missing JSDoc on exported Token type.",
      "findingsActionable": true,
      "usage": {
        "model": "claude-sonnet-4-5",
        "input": 28000,
        "output": 4200,
        "cacheRead": 10000,
        "cacheWrite": 2800,
        "cost": 0.038,
        "turns": 2
      },
      "fixupPlan": {
        "goal": "Address review findings: extract shared error formatter, add JSDoc",
        "context": "...",
        "tasks": []
      },
      "fixupImplementation": {
        "startedAt": "2026-04-01T11:48:00Z",
        "completedAt": "2026-04-01T11:55:00Z",
        "baseCommit": "...",
        "tasks": {}
      }
    }
  ],

  "close": {
    "recordedAt": "2026-04-01T12:00:00Z",
    "mergeResult": "clean",
    "finalCommit": "ghi9012abc3456",
    "diffStat": " 12 files changed, 340 insertions(+), 180 deletions(-)"
  }
}
```

### Design Choices

**`schemaVersion`** is a required integer at the root of every record. Written as the first key in JSON output. Enables future schema migrations: `record_from_json` checks the version and rejects records from newer `wf` versions with a clear upgrade message. Records without the field are assumed to be version 1.

**Forward-compatibility policy.** The root record schema and `$defs/WorkflowRecord` do NOT set `additionalProperties: false` — unknown top-level keys are tolerated. This allows records written by a newer `wf` version (with new sections like a future `phases` or `council` field) to be loaded by an older version without error. The Python loader (`record_from_json`) ignores unknown keys. Sub-schemas (`Plan`, `Task`, `Brainstorm`, `ReportResult`, etc.) DO use `additionalProperties: false` because they are tool registration contracts — strict validation catches malformed LLM tool calls.

**`reviews` is an array.** A review may find issues, those get fixed, and you may review again. Each cycle is an entry. Fixup plan + implementation nest inside the review entry that produced them.

**`workflow.status`** tracks the current phase: `init`, `brainstorming`, `planning`, `implementing`, `reviewing`, `closing`, `done`, `failed`. Resume/recovery reads this to know where to pick up.

**`workflow.config`** is a fully-resolved configuration snapshot, captured at `wf init` time. It contains every setting the workflow will use across all phases - models, automation levels, execution parameters, UI preferences, runner profile. This snapshot is assembled by merging five precedence levels (lowest to highest):

1. **Baked-in defaults** - hardcoded in `wf` source code
2. **User config** - `~/.config/wf/config.toml`
3. **Project config** - `.wf/config.toml` in the project repo
4. **Init-time overrides** - `--set key=value` flags on `wf init`

The snapshot is computed once and written into the record. All subsequent commands (`wf execute`, `wf review`, `wf run`, etc.) read settings from `workflow.config` rather than re-resolving the config chain. This means a workflow is self-contained - changing your user or project config after init does not alter an in-progress workflow's behavior. The workflow runs with the settings it was initialized with.

CLI flags on individual commands (`wf execute --concurrency 2`, `wf brainstorm --model claude-opus-4`) still override the snapshot for that invocation only - they do not modify the record. This is the fifth and highest precedence level, and it's ephemeral.

The automation levels within `workflow.config.automation` control the level of human involvement per phase:
- `interactive` - user drives the conversation (tmux session with agent, user types messages)
- `supervised` - runs automatically but visible (tmux panes), user can intervene
- `automatic` - runs headlessly, no user interaction needed

For brainstorm and plan phases: `interactive` maps to `wf brainstorm`/`wf plan` in tmux mode (default), `automatic` maps to headless mode (`--no-tmux`) with a `--prompt`. In a harness wrapper, `interactive` maps to inline mode toggles (`/wf brainstorm`, `/wf plan`).

**`workflow.worktree`** is `null` when running directly in the main repo ("bare mode"). All worktree-dependent operations (task worktrees, merge-back) still work - they branch from the main repo instead.

**Timestamps on everything.** Each phase records when it was captured. Duration is derivable.

**Usage follows the same shape everywhere** - brainstorm, planning, each task, each review. Consistent and aggregatable.

### What This Replaces

| Legacy file | Now in record |
|-------------|---------------|
| `docs/plans/<id>.json` | `record.plan` |
| `docs/plans/<id>.md` | Rendered on demand from `record.plan` via `wf render` |
| `docs/plans/<id>.state.json` | `record.implementation.tasks` |
| `docs/plans/.plan-init-<name>.json` | `record.workflow` (sourceBranch, sourceCommit, worktree) |
| `~/.pi/plan-history.jsonl` | Each record IS the history; `wf history` scans all records |

**No migration tooling.** The legacy planner (`docs/plans/`, `.state.json`, `.plan-init-*.json`, `~/.pi/plan-history.jsonl`) and `wf` (`docs/workflows/`) coexist — they use different directories and do not interfere. No converter is provided. Existing plans managed by the legacy planner continue to work with the legacy planner.

---

## Schema

### `schemas/workflow.schema.json`

Single JSON Schema file. The published contract for all data structures — used by harness wrappers for tool registration and by `wf schema` for external consumers. The root schema describes the full workflow record. Sub-schemas live in `$defs` and are extractable via `wf schema --component`. Runtime validation is done by the Python dataclasses in `types.py`, not by this schema file.

**Root** - validates the complete record file (`docs/workflows/<name>.json`).

**`$defs/Plan`** - used by harness wrappers to register the `submit_plan` tool.

```
Plan:
  goal: string                      # One-sentence summary
  context: string                   # Architectural context shared across tasks
  defaultModel?: string             # Default model for all tasks
  tasks: Task[]                     # At least one
```

**`$defs/Task`** - referenced by Plan.

```
Task:
  id: string                        # e.g. "task-1"
  title: string                     # Short descriptive title
  goal: string                      # Desired outcome
  files: string[]                   # Starting file hints
  constraints: string[]             # Architectural decisions as facts
  acceptance: string[]              # Testable completion criteria
  dependsOn: string[]               # Task IDs (empty = independent)
  skills?: string[]                 # Skill name hints (see note below)
  model?: string                    # Model override
```

**`skills` is a hint-only field.** `wf` includes skill names in the task brief as text ("These skills may be useful: X, Y. Load them with /skill:<name> if needed."). Harnesses that support skill loading (pi) benefit from this hint; the subagent can voluntarily load the skill. Harnesses without a skill mechanism (Claude Code) ignore it — the hint is inert text. A future enhancement could have `wf` inline skill content into the brief when skill files are discoverable (e.g. from a configured skills directory), but this is out of scope for v1.

**`$defs/Brainstorm`** - used by harness wrappers to register the `record_brainstorm` tool.

```
Brainstorm:
  motivation: string                # Problem statement - what and why
  solution: string                  # High-level approach
  designDecisions: DesignDecision[] # Key choices made

DesignDecision:
  decision: string                  # What was decided
  rationale: string                 # Why
```

**`$defs/ReportResult`** - used by harness wrappers to register the `report_result` tool for implementation subagents.

```
ReportResult:
  summary: string                   # What was accomplished (1-2 sentences)
  notes: string                     # Difficulties, surprises, things caller should know. Empty string if nothing.
```

`filesChanged` and `diffStat` are deliberately absent - they are derived from git by the scheduler after the agent exits, not self-reported by the agent. Git is authoritative; the agent is not.

**Why `report_result` is a tool, not a text format.** The legacy planner asked implementers to end with `## Summary` / `## Files Changed` / `## Notes` and parsed it with regex. This was fragile: LLMs don't always follow formatting instructions precisely, the regex had to handle variations, and the fallback ("last 500 chars") was lossy. Making it a tool call gives us:

- **Schema validation** - the tool enforces the structure. The agent either calls the tool correctly or doesn't call it at all. No "almost right" parsing.
- **Same pattern as `submit_plan`** - proven to work reliably. Extraction scans messages for tool call content blocks, not regex on free text.
- **Simpler prompt** - "call `report_result` when done" is a more natural instruction for an agent than "format your output as markdown with these exact headers."
- **`filesChanged` removed from agent responsibility** - git knows what changed authoritatively. The agent's self-report was always approximate (missed files, wrong paths). Now it's derived from `git diff --name-only` in the worktree.
- **Clean degradation** - if the agent crashes or forgets, `extract_summary_fallback` grabs the last 500 chars. The caller knows this is the degraded path (no `ReportResult` found) and can flag it.
- **`filesChanged` / `diffStat` are always available** - since `wf init` requires a git repository, git is always present during execution. `filesChanged` is derived from `git diff --name-only` and `diffStat` from `git diff --stat` in the task worktree (or against the base commit in serial mode). These are never empty under normal operation. They would only be empty if a task made no changes (legitimate) or if git commands fail (recorded as an event, non-fatal).

**`$defs/Usage`**, **`$defs/TaskResult`**, **`$defs/ImplementationEvent`**, **`$defs/ReviewRecord`**, etc. - shared definitions referenced throughout.

Harness wrappers that can resolve `$ref` pull sub-schemas directly from the file. For wrappers that can't, the CLI extracts components on demand:

```
wf schema                          # full record schema
wf schema --component plan         # just $defs/Plan (standalone, refs inlined)
wf schema --component brainstorm   # just $defs/Brainstorm
wf schema --component task         # just $defs/Task
wf schema --component report-result # just $defs/ReportResult
```

---

## Prompts

Plain markdown files in `wf/prompts/`. Each is a complete **system prompt** or **context injection** for a specific role. Harness wrappers read these and inject them however their harness handles system prompts. These are distinct from **templates** (in `wf/templates/`) which are user-invokable conversation fragments with variable substitution - see the Templates section below.

| File | Role | Current source |
|------|------|---------------|
| `brainstorm.md` | Guides brainstorming conversation toward structured output. Prompts the agent to call `record_brainstorm` when conclusions are reached. | New (no existing inline source) |
| `planning-context.md` | Injected when agent enters planning mode. Guidelines for good plans, call `submit_plan`. | `before_agent_start` handler in `index.ts` |
| `implementer.md` | System prompt for implementation subagents. Read files, follow constraints, meet acceptance criteria. Call `report_result` tool when done. | `IMPLEMENTER_PROMPT` in `runner.ts` |
| `reviewer.md` | System prompt for code review subagents. Agent-centric review criteria. | `CODE_REVIEW_PROMPT` in `code-review.ts` |
| `reviewer-with-plan.md` | System prompt for auto-review. Review + call `submit_plan` if issues found. | `REVIEWER_SYSTEM_PROMPT` in `auto-review.ts` |
| `merge-resolver.md` | System prompt for conflict resolution agents. Used during task execution (automatic merge-back conflict resolution) and `wf close` (workflow merge resolution). Read markers, resolve, stage. | `MERGE_RESOLUTION_PROMPT` in `plan-lifecycle.ts` |

---

### JSON Naming Convention

All JSON — tool payloads, record files, CLI output, schema files — uses **camelCase** field names: `defaultModel`, `dependsOn`, `filesChanged`, `diffStat`, `sourceCommit`, `sourceBranch`, `baseCommit`, `createdAt`, etc.

Python dataclasses use **snake_case** internally (`default_model`, `depends_on`, `files_changed`). The `from_dict()` / `to_dict()` methods in `types.py` handle the mapping. This is a ~10-line helper (convert keys with `re.sub(r'_([a-z])', lambda m: m.group(1).upper(), key)` and its inverse).

Rationale:
- **Backward compatible** — the existing `submit_plan` tool uses camelCase (`defaultModel`, `dependsOn`). LLMs already produce this format. Changing it would break existing plans and muscle memory.
- **One convention per format** — JSON is camelCase everywhere, Python is snake_case everywhere. No per-field guessing.
- **Record files contain plans as-submitted** — the plan portion of the record is the tool payload verbatim. Having `dependsOn` in the plan but `depends_on` in `implementation` would be jarring.

---

## `wflib/types.py`

Data classes for all structures. JSON serialization/deserialization. Schema validation against the JSON Schema files in `schemas/`.

```python
# --- Core plan types ---

@dataclass
class Task:
    id: str
    title: str
    goal: str
    files: list[str]
    constraints: list[str]
    acceptance: list[str]
    depends_on: list[str]
    skills: list[str] | None = None
    model: str | None = None

@dataclass
class Plan:
    goal: str
    context: str
    tasks: list[Task]
    default_model: str | None = None

# --- Usage tracking (same shape everywhere) ---

@dataclass
class Usage:
    model: str | None = None       # harness-reported model string, NOT normalized.
                                    # May be harness-specific (e.g. "openai/gpt-4o"
                                    # for pi) or canonical (e.g. "claude-sonnet-4-5").
                                    # This is an audit field, not a lookup key.
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    turns: int = 0

# --- Implementer result (tool-based, deterministic extraction) ---

@dataclass
class ReportResult:
    summary: str                               # what was accomplished (1-2 sentences)
    notes: str                                 # difficulties, surprises, things caller should know

# --- Task execution ---

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskResult:
    status: TaskStatus
    started_at: str | None = None
    completed_at: str | None = None
    exit_code: int | None = None
    brief: str | None = None                   # full assembled prompt sent to subagent
    summary: str = ""                            # from report_result tool call (or fallback)
    files_changed: list[str] = field(default_factory=list)  # from git, not agent-reported
    diff_stat: str | None = None                 # from git diff --stat in task worktree
    notes: str = ""                              # from report_result tool call (or empty)
    error: str | None = None                   # full error text, never truncated
    worktree_path: str | None = None           # where the task worktree was/is
    worktree_preserved: bool = False            # True if worktree kept for inspection
    session_file: str | None = None            # path to preserved session on failure
    usage: Usage = field(default_factory=Usage)

# --- Brainstorm ---

@dataclass
class DesignDecision:
    decision: str
    rationale: str

@dataclass
class BrainstormRecord:
    recorded_at: str
    motivation: str
    solution: str
    design_decisions: list[DesignDecision]
    usage: Usage

# --- Implementation ---

@dataclass
class ImplementationEvent:
    t: str                                     # ISO timestamp
    event: str                                 # Closed enum for v1:
                                               #   taskStart, taskComplete,
                                               #   mergeStart, mergeComplete, mergeFailed,
                                               #   mergeResolveStart, mergeResolveComplete, mergeResolveFailed,
                                               #   worktreeCleanup, skipDependents,
                                               #   crashRecovery, error
    task: str | None = None
    detail: str | None = None                  # extra context (worktree path, conflict files, etc.)

@dataclass
class ImplementationRecord:
    started_at: str | None = None
    completed_at: str | None = None
    base_commit: str | None = None
    active_resources: dict[str, str] = field(default_factory=dict)
        # task_id -> worktree_path for live worktrees. Updated on create, cleared on cleanup.
        # After a crash, wf execute reads this to clean up orphans before resuming.
    events: list[ImplementationEvent] = field(default_factory=list)
        # Lightweight operational timeline. Major events only - not every debug line.
        # Enables timeline reconstruction for investigating failures.
    tasks: dict[str, TaskResult] = field(default_factory=dict)

# --- Review ---

@dataclass
class ReviewRecord:
    recorded_at: str
    base_commit: str | None
    review_text: str
    findings_actionable: bool
    usage: Usage
    fixup_plan: Plan | None = None
    fixup_implementation: ImplementationRecord | None = None

# --- Workflow (top-level) ---

class WorkflowStatus(Enum):
    INIT = "init"
    BRAINSTORMING = "brainstorming"
    PLANNING = "planning"
    IMPLEMENTING = "implementing"
    REVIEWING = "reviewing"
    CLOSING = "closing"
    DONE = "done"
    FAILED = "failed"

class AutomationLevel(Enum):
    INTERACTIVE = "interactive"    # user drives, confirms transitions
    SUPERVISED = "supervised"      # automatic but visible (tmux), user can intervene
    AUTOMATIC = "automatic"        # headless, no user interaction

@dataclass
class ModelConfig:
    brainstorm: str | None = None
    plan: str | None = None
    implement: str | None = None       # default for tasks; individual tasks can still override
    review: str | None = None
    fixup: str | None = None
    close: str | None = None

@dataclass
class AutomationConfig:
    brainstorm: AutomationLevel = AutomationLevel.INTERACTIVE
    plan: AutomationLevel = AutomationLevel.INTERACTIVE
    implement: AutomationLevel = AutomationLevel.SUPERVISED
    review: AutomationLevel = AutomationLevel.AUTOMATIC
    close: AutomationLevel = AutomationLevel.AUTOMATIC

@dataclass
class ExecuteConfig:
    concurrency: int = 4
    worktrees: bool = True
    auto_review: bool = True

@dataclass
class UIConfig:
    auto_close: int = 30               # seconds; 0 = disabled
    tmux: bool = True

@dataclass
class AgentConfig:
    profile: str = "pi"             # runner profile name ("pi", "claude-code", "mock")
    cmd: str | None = None           # override binary path (default: derived from profile)

@dataclass
class ModelsConfig:
    """Model name aliases and per-profile harness mappings.

    aliases: user-defined shorthands → canonical names.
      e.g. {"fast": "claude-haiku-4-5", "default": "claude-sonnet-4-5"}
      Merged on top of built-in aliases (sonnet, opus, haiku).

    profiles: per-profile canonical → harness-specific overrides.
      e.g. {"pi": {"gpt-4o": "openai/gpt-4o"}, "claude-code": {}}
      Merged on top of each profile's built-in MODEL_MAP.
    """
    aliases: dict[str, str] = field(default_factory=dict)
    profiles: dict[str, dict[str, str | None]] = field(default_factory=dict)

@dataclass
class WorkflowConfig:
    """Fully-resolved configuration snapshot. Captured at wf init time by
    merging: baked-in defaults < user config < project config < init flags.
    Stored in the record. All subsequent commands read from here.
    CLI flags on individual commands override for that invocation only."""
    model: ModelConfig = field(default_factory=ModelConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    execute: ExecuteConfig = field(default_factory=ExecuteConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    models: ModelsConfig = field(default_factory=ModelsConfig)

@dataclass
class WorkflowMeta:
    id: str
    name: str
    created_at: str
    status: WorkflowStatus
    project: str
    source_branch: str
    source_commit: str
    worktree: str | None               # None = bare mode (main repo)
    config: WorkflowConfig = field(default_factory=WorkflowConfig)

@dataclass
class PlanRecord:
    recorded_at: str
    goal: str
    context: str
    default_model: str | None
    tasks: list[Task]
    usage: Usage

@dataclass
class CloseRecord:
    recorded_at: str
    merge_result: str                   # "clean" | "conflicted" | "failed"
    final_commit: str | None
    diff_stat: str

CURRENT_SCHEMA_VERSION = 1

@dataclass
class WorkflowRecord:
    workflow: WorkflowMeta
    schema_version: int = CURRENT_SCHEMA_VERSION
        # Python: workflow must precede schema_version (non-default before default).
        # JSON: record_to_json writes schemaVersion as the first key regardless.
    brainstorm: BrainstormRecord | None = None
    plan: PlanRecord | None = None
    implementation: ImplementationRecord | None = None
    reviews: list[ReviewRecord] = field(default_factory=list)
    close: CloseRecord | None = None

# --- Serialization ---

def record_from_json(data: dict) -> WorkflowRecord
    """Deserialize a dict (from JSON) into a WorkflowRecord.
    Reads schemaVersion from the record. If absent, assumes version 1.
    If the version is higher than CURRENT_SCHEMA_VERSION, raises with
    a clear message directing the user to upgrade wf.
    Ignores unknown top-level keys (forward-compatibility for records
    written by newer wf versions that this version can still partially read).
    """
def record_to_json(record: WorkflowRecord) -> dict
    """Serialize a WorkflowRecord to a JSON-compatible dict (camelCase keys).
    Always writes schemaVersion as the first key.
    """
def plan_from_json(data: dict) -> Plan
def plan_to_json(plan: Plan) -> dict
def validate_schema(data: dict, component: str | None = None) -> list[str]
    # component=None validates full record, "plan"/"brainstorm"/etc. validates that $def
    # returns errors, empty = valid

# --- Message extraction ---

def extract_tool_call(messages: list[dict], tool_name: str) -> dict | None
    """Scan messages backwards for the last tool call matching tool_name.
    Returns the tool call's arguments dict, or None if not found.

    Looks for assistant messages containing a content block with
    type='toolCall' and name matching tool_name. Returns block['arguments'].

    This is the single extraction pattern used by all structured agent
    outputs: report_result (implementation agents), submit_plan (review
    agents), record_brainstorm (brainstorm agents). Each caller wraps
    this with its own type-specific parsing:

        # runner.py
        args = extract_tool_call(messages, 'report_result')
        return ReportResult(**args) if args else None

        # review.py
        return extract_tool_call(messages, 'submit_plan')
    """
```

---

## `wflib/config.py`

Configuration loading, merging, and resolution. Implements the 5-level precedence chain:

```
CLI flags  >  init-time overrides  >  project config  >  user config  >  baked-in defaults
```

Levels 1-4 are resolved at `wf init` time and snapshotted into `workflow.config` in the record. Level 5 (CLI flags) is applied at runtime by each command and is ephemeral - it does not modify the record.

### Config File Format

Both user and project config files use the same TOML format:

```toml
# ~/.config/wf/config.toml   (user-wide)
# .wf/config.toml             (project-level, committed to repo)

# Per-phase model preferences
[model]
brainstorm = "claude-sonnet-4-5"
plan = "claude-sonnet-4-5"
implement = "claude-sonnet-4-5"     # default for tasks; individual tasks can still override
review = "claude-sonnet-4-5"
fixup = "claude-sonnet-4-5"
close = "claude-sonnet-4-5"

# Per-phase automation levels: interactive | supervised | automatic
[automation]
brainstorm = "interactive"
plan = "interactive"
implement = "supervised"
review = "automatic"
close = "automatic"

# Execution settings
[execute]
concurrency = 4
worktrees = true
auto-review = true

# Runtime/UI settings
[ui]
auto-close = 30         # seconds; 0 = disabled
tmux = true

# Agent
[agent]
profile = "pi"          # runner profile: "pi", "claude-code"
# cmd = "/custom/path/to/pi"   # override binary path (optional; default: derived from profile)

# Model name aliases and per-profile mappings
[models]
# User-defined aliases → canonical names. These are personal shorthands.
# Built-in aliases (sonnet, opus, haiku) are always available.
# User aliases override built-in aliases.
fast = "claude-haiku-4-5"
default = "claude-sonnet-4-5"
big = "claude-opus-4"

[models.pi]
# Canonical → pi-specific overrides. Only needed when the profile's
# built-in map is wrong or missing (e.g. new model, custom provider).
# "gpt-4o" = "openai/gpt-4o"  # already built-in for pi

[models.claude-code]
# Canonical → claude-code-specific overrides.
```

Project config at `.wf/config.toml` is committed to version control. This lets teams share conventions ("this project always uses worktrees", "default review model is X"). User config at `~/.config/wf/config.toml` is personal ("I always want auto-close at 60s").

All sections and keys are optional. Missing keys fall through to the next lower precedence level.

### Config File Locations

| Level | Path | Scope |
|-------|------|-------|
| User | `~/.config/wf/config.toml` | All projects, this user |
| Project | `.wf/config.toml` (repo root) | This project, all users |

The project config path is `.wf/config.toml` (not inside `docs/workflows/`) because configuration is a project-level concern, not a workflow artifact. It sits alongside `.git/`, `.gitignore`, etc.

### Resolution and Snapshotting

At `wf init` time:

1. Load baked-in defaults (hardcoded `WorkflowConfig()`)
2. Load and merge user config (`~/.config/wf/config.toml`)
3. Load and merge project config (`.wf/config.toml`)
4. Apply init-time overrides (`--set key=value` flags)
5. Write the fully-resolved `WorkflowConfig` into `record.workflow.config`

All subsequent commands read from `record.workflow.config`. They do NOT re-read config files. This makes the workflow self-contained - it runs with the settings it was initialized with, regardless of config file changes afterward.

CLI flags on individual commands (`wf execute --concurrency 2`, `wf brainstorm --model claude-opus-4`) override the snapshot for that invocation only. They are the highest precedence level but are ephemeral - they don't modify the record.

For implementation tasks, the model precedence chain is:
```
CLI --model  >  task.model (LLM-authored)  >  plan.defaultModel (LLM-authored)  >  config.model.implement (snapshot)  >  None
```
The LLM's per-task model override (`task.model`) and plan-level default (`plan.defaultModel`) sit between the CLI flag and the config snapshot. This preserves the existing `resolveTaskModel` semantics while extending the fallback chain.

### API

```python
import tomllib

USER_CONFIG_PATH = "~/.config/wf/config.toml"
PROJECT_CONFIG_NAME = ".wf/config.toml"

# --- Baked-in defaults ---

DEFAULTS = WorkflowConfig()   # all dataclass defaults

# --- Loading ---

def load_user_config() -> dict
    """Load ~/.config/wf/config.toml. Returns raw dict.
    Returns {} if file doesn't exist. Raises on parse error.
    """

def load_project_config(cwd: str) -> dict
    """Load .wf/config.toml from the project root.
    Walks up from cwd to find the repo root (looks for .git/).
    Returns {} if file doesn't exist. Raises on parse error.
    """

def parse_overrides(overrides: list[str]) -> dict
    """Parse --set key=value flags into a nested dict.
    Supports dotted keys: 'model.plan=claude-opus-4' becomes
    {'model': {'plan': 'claude-opus-4'}}.
    Raises ValueError on malformed input.
    """

# --- Merging ---

def merge_configs(*layers: dict) -> dict
    """Deep-merge config dicts, left to right (last wins).
    Only merges dicts - scalars and lists are replaced, not merged.
    """

# --- Resolution ---

def resolve_config(
    cwd: str,
    overrides: list[str] | None = None,
) -> WorkflowConfig
    """Build a fully-resolved WorkflowConfig by merging all levels:
    baked-in defaults < user config < project config < overrides.
    This is called once at wf init time. The result is stored in the record.

    Raises ConfigError on any validation failure:
      - Unknown keys in any config file (hard error, no forward-compat leniency)
      - Invalid values (bad enum string, negative concurrency, etc.)
      - Malformed TOML (via tomllib)

    Every key in every config file must match a known config path.
    Validation rules:
      - concurrency: int >= 1
      - auto_close: int >= 0 (0 = disabled)
      - automation.*: one of 'interactive', 'supervised', 'automatic'
      - profile: registered profile name ('pi', 'claude-code', 'mock')
      - model.*: any non-empty string (validated at resolve time by profile)
      - worktrees, auto_review, tmux: boolean
    """

def apply_cli_overrides(
    config: WorkflowConfig,
    **kwargs,
) -> WorkflowConfig
    """Apply ephemeral CLI flag overrides to a config snapshot.
    Returns a new WorkflowConfig (does not mutate the input).
    Used by commands that accept runtime flags:
        config = apply_cli_overrides(record.workflow.config,
            model_implement='claude-opus-4', concurrency=2)
    """

def config_to_dict(config: WorkflowConfig) -> dict
    """Serialize a WorkflowConfig to a dict for JSON storage in the record."""

def config_from_dict(data: dict) -> WorkflowConfig
    """Deserialize a WorkflowConfig from a record's workflow.config dict."""

# --- Inspection ---

def show_resolved(config: WorkflowConfig) -> str
    """Format a resolved config for display (wf config list)."""

def show_with_origins(
    cwd: str,
    overrides: list[str] | None = None,
) -> str
    """Format the config showing each value's source level.
    e.g. 'model.plan = claude-sonnet-4-5  (project)'
    Only meaningful before snapshotting (at init time or for inspection).
    """

# --- Editing (for wf config set) ---

def set_config_value(path: str, key: str, value: str, scope: str = "user") -> None
    """Set a value in a config file. scope is 'user' or 'project'.
    Creates the file if it doesn't exist.
    Validates that the key is a known config path and the value is valid
    for that key (same rules as resolve_config). Raises ConfigError on
    unknown keys or invalid values — hard error, never writes bad config.
    Uses targeted string manipulation (find section, set key=value).
    Does not parse and re-serialize the whole file - preserves
    comments and formatting.
    """
```

---

## `wflib/record.py`

Workflow record file I/O. The central state manager. Every phase reads and writes through this module.

```python
WORKFLOWS_DIR = "docs/workflows"

def record_path(name: str, cwd: str) -> str
    """Absolute path to docs/workflows/<name>.json."""

def ensure_workflows_dir(cwd: str) -> str
    """Create docs/workflows/ if needed. Returns absolute path."""

# --- CRUD ---

def create_record(
    name: str,
    cwd: str,
    source_branch: str,
    source_commit: str,
    worktree: str | None = None,
    config: WorkflowConfig | None = None,
) -> WorkflowRecord
    """Create a new record file. Generates workflow ID.
    Writes to docs/workflows/<name>.json. Raises if name already exists.
    config is the fully-resolved WorkflowConfig snapshot from config.resolve_config().
    If None, uses default WorkflowConfig (baked-in defaults only).
    Returns the new record.
    """

def load_record(name: str, cwd: str) -> WorkflowRecord
    """Load a record from disk. Raises FileNotFoundError if missing, ValueError if malformed."""

def save_record(record: WorkflowRecord, cwd: str) -> None
    """Write record to disk. Atomic write (write tmp + rename)."""

def list_records(cwd: str) -> list[WorkflowRecord]
    """Scan docs/workflows/ for all record files. Returns loaded records.
    Skips malformed files with a warning.
    """

# --- Phase transitions ---

def record_brainstorm(
    record: WorkflowRecord,
    motivation: str,
    solution: str,
    design_decisions: list[DesignDecision],
    usage: Usage,
) -> None
    """Write brainstorm data into the record. Sets status to 'planning'."""

def record_plan(
    record: WorkflowRecord,
    plan: Plan,
    usage: Usage,
) -> None
    """Write plan data into the record. Sets status to 'implementing'.
    Caller is responsible for validating the plan (via validate_plan)
    before calling this - record.py trusts its inputs.
    """

def record_implementation_start(
    record: WorkflowRecord,
    base_commit: str,
) -> None
    """Mark implementation as started. Sets base_commit."""

def record_task_start(record: WorkflowRecord, task_id: str, worktree_path: str | None = None) -> None
    """Mark a task as running with startedAt timestamp.
    Adds worktree to activeResources. Appends taskStart event.
    """

def record_task_complete(record: WorkflowRecord, task_id: str, result: TaskResult) -> None
    """Record a task's result. Updates implementation.tasks[task_id].
    Appends taskComplete event.
    """

def record_event(record: WorkflowRecord, event: str, task: str | None = None, detail: str | None = None) -> None
    """Append an operational event to implementation.events.
    Used for all events in the closed v1 enum: taskStart, taskComplete,
    mergeStart, mergeComplete, mergeFailed, mergeResolveStart,
    mergeResolveComplete, mergeResolveFailed, worktreeCleanup,
    skipDependents, crashRecovery, error.
    """

def clear_active_resource(record: WorkflowRecord, task_id: str) -> None
    """Remove a worktree from activeResources after cleanup."""

def record_implementation_complete(record: WorkflowRecord) -> None
    """Mark implementation as done. Sets completed_at. Sets status to 'reviewing'."""

def record_review(
    record: WorkflowRecord,
    review_text: str,
    findings_actionable: bool,
    usage: Usage,
    base_commit: str | None = None,
    fixup_plan: Plan | None = None,
) -> ReviewRecord
    """Append a review entry to reviews[]. Returns the new ReviewRecord
    for the caller to populate fixup_implementation if needed.
    """

def record_fixup_complete(
    review: ReviewRecord,
    implementation: ImplementationRecord,
) -> None
    """Attach fixup implementation results to a review entry."""

def record_close(
    record: WorkflowRecord,
    merge_result: str,
    final_commit: str | None,
    diff_stat: str,
) -> None
    """Write close data into the record. Sets status to 'done'."""

# --- Query helpers ---

def get_plan(record: WorkflowRecord) -> Plan | None
    """Extract a Plan object from the record's plan phase (for scheduler, brief assembly, etc.)."""

def get_implementation_state(record: WorkflowRecord) -> dict[str, TaskResult]
    """Get current task statuses/results from the implementation phase."""

def get_total_usage(record: WorkflowRecord) -> Usage
    """Aggregate usage across all phases (brainstorm + plan + implementation + reviews)."""
```

---

## `wflib/validate.py`

Pure validation. No I/O. Combines structural checks (deps, cycles) with
mechanical heuristic checks derived from the task-decomposition skill.
The heuristic checks are warnings, not hard errors — they flag likely
problems without blocking submission.

```python
@dataclass
class ValidationResult:
    errors: list[str]        # hard errors (bad refs, cycles) — plan is invalid
    warnings: list[str]      # heuristic warnings — plan is valid but suspect

def validate_plan(plan: Plan) -> ValidationResult
    """Full validation: structural checks + heuristic checks.
    Raises ValueError on hard errors (callers who just want pass/fail).
    Returns ValidationResult for callers who want warnings too.

    Warnings are surfaced to callers, not silently dropped:
      - CLI commands (wf submit-plan, wf plan): warnings are included in
        the JSON response as a "warnings" array AND printed to stderr.
      - wf validate: warnings are printed alongside "Valid" status.
      - Harness wrappers: the JSON response includes warnings, which the
        wrapper can display as notifications.
    Warnings are NOT stored in the record — they are transient feedback
    about plan quality at submission time, not workflow history.
    """

# --- Structural checks (hard errors) ---

def _check_refs(plan: Plan) -> list[str]
    """Every dependsOn ID exists in plan.tasks."""

def _check_cycles(plan: Plan) -> list[str]
    """DFS cycle detection on the dependency graph."""

# --- Heuristic checks (warnings) ---
# These are the mechanizable subset of the task-decomposition skill's
# guidance. They catch common plan quality problems that are detectable
# from structure alone. The non-mechanizable guidance ("one reason to
# fail", "refactor first", knowing when changes are truly independent)
# lives in prompts/planning-context.md and requires LLM judgment.

def _check_empty_acceptance(plan: Plan) -> list[str]
    """Warn if any task has zero acceptance criteria.
    Every task should have concrete, testable completion criteria."""

def _check_constraint_count(plan: Plan, threshold: int = 6) -> list[str]
    """Warn if any task has more than `threshold` constraints.
    From the skill: 'More than 5-6 constraints usually means it bundles
    multiple concerns.' Not a hard limit — just a signal to review."""

def _check_empty_goal(plan: Plan) -> list[str]
    """Warn if any task has an empty or very short goal."""

def _check_duplicate_ids(plan: Plan) -> list[str]
    """Hard error: task IDs must be unique."""
```

---

## `wflib/brief.py`

Deterministic task brief assembly. Pure function - plan data in, string out.

```python
def assemble_task_brief(
    task: Task,
    plan: Plan,
    results: dict[str, TaskResult],
) -> str
    """Build a scoped prompt for an implementation agent.

    Includes: context, file hints, constraints, prior work
    summaries (with diff stats), skills, goal, acceptance criteria.
    Ends with instruction to call report_result when done.

    Does NOT include: other tasks, planner reasoning, step-by-step instructions.
    """

def _render_prior_work(task: Task, results: dict[str, TaskResult]) -> str
    """Format dependency task summaries for the brief."""
```

---

## `wflib/scheduler.py`

DAG scheduler. Pure scheduling logic - manages task readiness, concurrency pool, dependency tracking. Delegates per-task execution to `task_executor.py`.

The scheduler owns "which tasks run when." It does NOT own worktree lifecycle, brief assembly, agent spawning, result extraction, or merging - those are `task_executor.run_task`'s responsibility.

```python
async def execute_plan(
    record: WorkflowRecord,
    cwd: str,
    cli_overrides: dict | None = None,
    on_task_start: Callback | None = None,
    on_task_complete: Callback | None = None,
    on_state_change: Callback | None = None,
) -> ExecutionSummary
    """Execute all pending tasks via DAG scheduling.

    Reads all settings from record.workflow.config (the init-time snapshot).
    cli_overrides (from command-line flags) are applied on top for this
    invocation only via config.apply_cli_overrides().

    Pool-based: tasks start as soon as deps complete, up to concurrency limit.
    When multiple tasks become ready simultaneously, they are started in
    lexicographic order by task.id (deterministic tie-breaking).
    For each ready task, calls task_executor.run_task which handles the full
    per-task lifecycle (worktree → brief → spawn → results → merge → cleanup).
    Serialized merge-back via asyncio.Lock passed to run_task.
    Saves record to disk after every state change.

    Callbacks fired for UI integration - harness wrappers can
    poll the record file instead if callbacks aren't practical.
    """

async def execute_single_task(
    record: WorkflowRecord,
    task_id: str,
    cwd: str,
    cli_overrides: dict | None = None,
) -> TaskResult
    """Execute (or re-run) a single task.
    Reads settings from record.workflow.config, applies cli_overrides.
    Validates deps are met, then delegates to task_executor.run_task.
    """

async def execute_fixup(
    review: ReviewRecord,
    record: WorkflowRecord,
    cwd: str,
    cli_overrides: dict | None = None,
) -> ExecutionSummary
    """Execute a fixup plan from a review. Same DAG scheduler and same
    run_task pipeline, results stored in review.fixup_implementation
    instead of record.implementation.
    Reads settings from record.workflow.config, applies cli_overrides.

    Fixup model precedence chain (highest to lowest):
      1. cli_overrides["fixup_model"] (from --fixup-model CLI flag)
      2. config.model.fixup (from the init-time config snapshot)
      3. Falls through to resolve_task_model's normal chain:
         task.model > fixup_plan.defaultModel > config.model.implement > None

    Implementation: execute_fixup resolves the effective fixup default
    by picking cli_overrides["fixup_model"] ?? config.model.fixup, then
    passes that as the cli_model parameter to the scheduler. This makes
    the fixup default act like a --model override from the scheduler's
    perspective, without adding a separate resolution path.
    """

def get_ready_tasks(plan: Plan, statuses: dict[str, TaskStatus]) -> list[Task]
    """Tasks that are pending with all deps done."""

def skip_dependents(plan: Plan, statuses: dict[str, TaskStatus], failed_id: str) -> list[str]
    """Mark transitive dependents of a failed task as skipped. Returns skipped IDs."""

def reset_ready_skipped(plan: Plan, statuses: dict[str, TaskStatus]) -> list[str]
    """After success, reset skipped tasks whose deps are now all done. Returns reset IDs."""

def resolve_task_model(
    task: Task,
    plan: Plan,
    config: WorkflowConfig,
    cli_model: str | None = None,
) -> tuple[str | None, str]
    """Returns (model_name, source). Precedence chain:
    cli_model > task.model > plan.defaultModel > config.model.implement > None.
    The LLM-authored overrides (task.model, plan.defaultModel) sit between
    the CLI flag and the config snapshot.

    The returned model_name is a wf canonical name or user-written string
    (e.g. "claude-sonnet-4-5", "sonnet", "gpt-4o"). It has NOT been
    through profile.resolve_model yet - that happens inside
    build_headless_cmd / build_tmux_wrapper, which translates the name
    to the exact harness-specific string. This separation keeps the
    scheduler profile-agnostic.
    """

@dataclass
class ExecutionSummary:
    counts: dict[str, int]       # {done: N, failed: N, skipped: N, pending: N}
    duration_seconds: int
    usage_rows: list[UsageRow]
    base_commit: str | None
```

---

## `wflib/task_executor.py`

Per-task execution lifecycle. Owns the full pipeline for running a single task: worktree setup, brief assembly, agent spawning, result processing, merge-back, and cleanup. Called by the scheduler for each task.

This is the module that was previously implicit inside `scheduler.py` / the legacy `index.ts` `runTask` function. Factoring it out means the scheduler focuses purely on DAG logic, and the per-task pipeline is independently testable and modifiable.

```python
async def run_task(
    task: Task,
    plan: Plan,
    record: WorkflowRecord,
    cwd: str,
    merge_lock: asyncio.Lock,
    config: WorkflowConfig,
    cli_model: str | None = None,
) -> TaskResult
    """Execute a single task through the full lifecycle.

    Reads profile, worktree, tmux, and auto_close settings from config
    (the resolved snapshot from the record). Resolves the runner profile
    via profiles.get_profile(config.agent.profile). cli_model is the
    ephemeral --model flag from the CLI, if any.

    Steps:
      1. Create worktree (if config.execute.worktrees) → worktree.py
      2. Assemble brief → brief.py
      3. Resolve model → scheduler.resolve_task_model (cli > task > plan > config)
      4. Resolve profile → profiles.get_profile(config.agent.profile)
      5. Record task_start + save → record.py
      6. Spawn agent → runner.py (spawn_headless or spawn_in_tmux)
         Runner delegates to profile for command construction + output parsing.
      7. Copy results.json to durable location → file I/O
      8. Read results + extract report_result → runner.py
      9. Capture git diff/stat from worktree → git.py
     10. Commit if dirty → worktree.py
     11. Merge back (acquires merge_lock) → worktree.py
     12. If merge conflict → auto-resolve (see below)
     13. Record task_complete + save → record.py
     14. Update dependency graph (skip_dependents or reset_ready_skipped)
     15. Cleanup worktree → worktree.py
     16. Record cleanup event → record.py

    On agent failure: marks task failed, skips dependents, preserves
    session file for investigation.

    On merge conflict: automatic resolution is attempted before failing.
    The resolution agent runs while holding the merge lock (the worktree
    is mid-rebase). Steps:
      a. Record mergeResolveStart event
      b. Spawn conflict resolution agent in the worktree with
         prompts/merge-resolver.md as system prompt and conflict context
         (conflicting files, conflict markers, diff stat). Uses the same
         model as the task that caused the conflict (already resolved via
         the task model precedence chain).
      c. Agent resolves conflicts, runs `git add` on each file, does NOT commit
      d. After agent exits, check for remaining unmerged files
         (`git diff --name-only --diff-filter=U`)
      e. If all resolved: record mergeResolveComplete event,
         `git rebase --continue`, fast-forward merge, task succeeds
      f. If conflicts remain or agent fails: record mergeResolveFailed event,
         mark task failed, preserve worktree (worktree_preserved=True),
         capture resolution attempt details in error field. Dependents skipped.

    Note: while the resolution agent runs, other tasks that finish will
    queue on the merge lock. This is correct but means a slow resolution
    blocks other merge-backs.

    The merge_lock is provided by the scheduler to serialize merge-back
    across concurrent tasks (each rebase sees the latest HEAD).
    """

def _setup_worktree(
    task: Task,
    cwd: str,
    workflow_id: str,
) -> WorktreeInfo
    """Create and setup a task worktree. Records active_resource."""

def _capture_diff_stat(
    worktree_path: str,
    main_branch: str,
) -> tuple[list[str], str | None]
    """Get files_changed and diff_stat from the worktree branch.
    Uses git diff --name-only and git diff --stat against main.
    Returns (files_changed, diff_stat).
    """

async def _merge_and_cleanup(
    cwd: str,
    wt: WorktreeInfo,
    task: Task,
    record: WorkflowRecord,
    merge_lock: asyncio.Lock,
    profile: RunnerProfile,
    model: str | None,
    config: WorkflowConfig,
) -> MergeResult
    """Acquire merge lock, commit, rebase, merge, cleanup.
    On conflict: spawn conflict resolution agent (prompts/merge-resolver.md)
    using the task's resolved model. If resolution succeeds, continue rebase
    and merge. If resolution fails, preserve worktree and record error.
    On clean merge: cleanup worktree, clear active_resource.
    """

def _preserve_results(
    results_path: str,
    workflow_name: str,
    task_id: str,
    cwd: str,
    session_dir: str | None = None,
    preserve_session: bool = False,
) -> None
    """Copy results.json (always) and session file (on failure) to
    docs/workflows/.sessions/<workflow>/ for crash recovery.
    """
```

---

## `profiles/` - Runner Profiles

A **runner profile** is a single Python module that encodes everything needed to spawn and read results from one agent harness. It is the complete "how to drive this agent CLI" in one place. The runner (`wflib/runner.py`) never contains harness-specific code - it calls the profile interface exclusively.

Profiles are the answer to: "what do I change to add a new harness?" One file. The profile interface is obvious from reading any existing profile.

### Why Profiles Instead of Just Adapters

The earlier design had adapters (output parsers) as the harness-specific zone, with command construction buried in `runner.py`. This was insufficient because harness-specific knowledge spans three concerns, not one:

1. **Command construction** - how you build the CLI invocation (`pi --mode json -p --no-session --no-extensions --append-system-prompt ... -e ext.ts` vs `claude -p --bare --output-format stream-json --append-system-prompt-file ... --mcp-config ...`)
2. **Output parsing** - how you extract messages/usage/tool calls from agent output (pi's JSON event stream vs Claude Code's `stream-json` NDJSON)
3. **Tool registration** - how you give the agent custom tools like `report_result` (pi's `-e extension.ts` vs Claude Code's MCP servers)

These three are intertwined - how you load tools is part of how you construct the command, and the output format determines which adapter to use. A profile bundles all three into a single cohesive unit.

### The `RunnerProfile` Protocol

```python
# profiles/__init__.py

from typing import Protocol

class RunnerProfile(Protocol):
    """Complete interface for driving one agent harness."""

    name: str

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],           # ["report-result", "submit-plan", "record-brainstorm"]
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]
        """Build the full argv for headless (non-interactive) execution.

        tools: which subagent tools to make available. The profile knows
        how its harness loads tools — pi uses -e with .ts extensions,
        Claude Code uses --mcp-config with an MCP server.

        cmd_override: replace the default binary path (e.g. "/custom/path/to/pi").
        If None, uses the profile’s default (e.g. "pi", "claude").

        models_config: resolved model aliases and per-profile mappings from
        the workflow config snapshot. Used by resolve_model internally.
        """

    def build_tmux_wrapper(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt_file: str,
        session_dir: str,
        exit_code_file: str,
        results_file: str,
        auto_close: int | None = None,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> str
        """Return the full shell script content for a tmux wrapper.

        The wrapper must:
          1. Run the agent interactively in the pane
          2. After the agent exits, produce results_file (via adapter)
          3. Write exit_code_file (signals completion to the polling loop)

        The profile knows how to invoke its harness interactively,
        where session data is written, and which adapter to call.
        """

    def parse_headless_output(self, stdout: str) -> dict
        """Parse captured stdout from headless mode into a results dict.
        Returns the standardized results format (see Agent Output Contract).
        Delegates to the appropriate adapter.
        """

    def parse_session_output(self, session_dir: str, results_file: str) -> dict
        """Parse session/results from tmux mode into a results dict.
        Called by the runner after the tmux wrapper exits.
        """

    def get_tool_paths(self) -> dict[str, str]
        """Map tool names to their implementation paths.

        For pi: {"report-result": "<wf>/tools/pi_extensions/report-result-tool.ts", ...}
        For claude-code: {"report-result": "mcp://<wf>/tools/mcp_server.py", ...}

        The runner doesn't interpret these paths - it passes tool names
        to build_headless_cmd/build_tmux_wrapper, and the profile uses
        these paths internally to construct the right flags.
        """

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str
        """Map a model name to the exact, unambiguous string for this harness.

        Two-stage resolution:
          1. Resolve aliases to canonical names (config aliases override built-in aliases)
          2. Map canonical names to harness-specific identifiers
             (config profile overrides override built-in MODEL_MAP)

        If the name (after alias resolution) is in the effective model map,
        return the mapped value. Otherwise, pass through verbatim - the user
        may be using a harness-native identifier directly.

        models_config comes from the workflow's resolved config snapshot.
        """

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]
        """Return (canonical_name, harness_id) pairs for all models this profile supports.
        Merges built-in MODEL_MAP with config profile overrides.
        Used by `wf help models` and config validation.
        """

    @property
    def supports_tmux(self) -> bool
        """Whether this profile supports interactive tmux mode.
        Some harnesses may only support headless execution.
        """

# --- Built-in aliases (shared across all profiles) ---

BUILTIN_ALIASES: dict[str, str] = {
    # Convenience shorthands → canonical names.
    # Users can override or extend these via [models] in config.
    "sonnet": "claude-sonnet-4-5",
    "opus": "claude-opus-4",
    "haiku": "claude-haiku-4-5",
}

def resolve_alias(name: str, models_config: ModelsConfig) -> str
    """Resolve a model alias to its canonical name.
    Config aliases (models_config.aliases) override built-in aliases.
    Returns the input unchanged if it's not a known alias.
    """

# --- Profile registry ---

def get_profile(name: str) -> RunnerProfile
    """Look up a profile by name. Raises ValueError for unknown profiles.

    Built-in profiles:
      - "pi"          PiProfile (default)
      - "claude-code"  ClaudeCodeProfile
      - "mock"         MockProfile (for E2E tests)
    """
```

### Model Resolution

Model names written by users (in config files, plans, and CLI flags) go through two deterministic resolution stages before reaching the harness CLI. Both stages are **user-configurable** via the `[models]` section in config files.

**Stage 1: Alias → Canonical** (shared across profiles)

Aliases map convenient shorthands to canonical model names. Built-in aliases (`sonnet`, `opus`, `haiku`) ship with `wf`. Users define their own in config:

```toml
# ~/.config/wf/config.toml
[models]
fast = "claude-haiku-4-5"        # personal shorthand
default = "claude-sonnet-4-5"    # team convention
sonnet = "claude-sonnet-4-5"     # override built-in (same here, but could differ)
```

Config aliases override built-in aliases with the same name. The resolution is a dict lookup - no fuzzy matching, no heuristics. This is `wf`'s vocabulary: users define it, it doesn't change per harness.

**Stage 2: Canonical → Harness-specific** (per-profile)

Each profile has a built-in `MODEL_MAP` that translates canonical names to the exact string its harness CLI expects. Users can override or extend this map in config:

```toml
# ~/.config/wf/config.toml
[models.pi]
# Override pi's built-in mapping for a specific model
"my-custom-model" = "custom-provider/my-model-v2"

[models.claude-code]
# Nothing to override - claude-code's built-ins are fine
```

Config profile overrides are merged on top of the profile's built-in `MODEL_MAP`. This means:
- New models can be added without waiting for a `wf` release
- Custom providers or internal deployments work without forking profiles
- Teams can standardize model names in project config (`.wf/config.toml`)

**The effective model map** for a given profile is: `built-in MODEL_MAP + config [models.<profile>]` (config wins on conflict).

**Resolution table showing both layers:**

| Canonical name | Pi (built-in) | Claude Code (built-in) | Hypothetical Bedrock (built-in) |
|---|---|---|---|
| `claude-sonnet-4-5` | `claude-sonnet-4-5` | `claude-sonnet-4-5` | `anthropic.claude-sonnet-4-5-v2:0` |
| `claude-opus-4` | `claude-opus-4` | `claude-opus-4` | `anthropic.claude-opus-4-v1:0` |
| `gpt-4o` | `openai/gpt-4o` | - (not available) | - (not available) |
| `gemini-pro` | `gcp/google/gemini-3-pro` | - (not available) | - (not available) |

A user adding a new model before the profile ships it:
```toml
[models.pi]
"claude-next-gen" = "claude-next-gen-20260401"
```

**Passthrough for unknown names:** If a name isn't in the effective model map (after alias resolution), it passes through verbatim. This lets users write harness-native identifiers directly when needed. The profile doesn't gatekeep - it translates known names and passes through unknown ones.

**`None` values mean unavailable:** If a canonical name maps to `None` (either in the built-in `MODEL_MAP` or via config), `resolve_model` raises with a clear message: `"Model 'gpt-4o' is not available on the claude-code harness."` Users can also use this in config to explicitly block a model:

```toml
[models.pi]
"gpt-4o" = false   # disallow gpt-4o on this project's pi profile
```

**Why this matters:**

1. **No black-box resolution.** Every step is a dict lookup the user can inspect and override. `wf config list --show-origin` shows the resolved model map with sources.

2. **One name, all harnesses.** The user writes `model.implement = "sonnet"` once. Each profile translates it to the right harness string. Switch profiles and it still works.

3. **User-extensible without code changes.** New model? Add one line to config. Custom provider format? Override the mapping. No Python edits, no `wf` update.

4. **Snapshotted at init time.** The resolved `[models]` config (aliases + per-profile overrides) is captured in `workflow.config.models` in the record. A workflow always uses the model mappings it was initialized with, even if config changes later.

**Where resolution happens in the pipeline:**

The scheduler resolves the *which model* question (`resolve_task_model`: CLI flag > task override > plan default > config snapshot). The profile resolves the *what string to pass* question (`resolve_model`: alias > canonical > harness-specific). These are separate concerns:

```
user writes "fast"  →  config stores "fast"  →  resolve_task_model picks it
  →  profile.resolve_model("fast", models_config)
    Stage 1: aliases["fast"] → "claude-haiku-4-5"     (from user config)
    Stage 2: model_map["claude-haiku-4-5"] → "claude-haiku-4-5"  (built-in, identity)
  →  --model claude-haiku-4-5
```

`resolve_model` is called inside `build_headless_cmd` and `build_tmux_wrapper` - the runner never sees harness-specific model strings.

### `profiles/pi.py` - Pi Runner Profile

```python
from adapters import pi_json_mode, pi_session
from profiles import resolve_alias

class PiProfile:
    name = "pi"

    # Built-in canonical name → exact pi model string.
    # Identity for most models (pi accepts canonical Anthropic names directly).
    # Non-Anthropic models need pi's provider/model format.
    # None = model exists canonically but is not available on this harness.
    # Users can override/extend this via [models.pi] in config.
    BUILTIN_MODEL_MAP = {
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-opus-4": "claude-opus-4",
        "claude-haiku-4-5": "claude-haiku-4-5",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gemini-pro": "gcp/google/gemini-3-pro",
    }

    def _effective_map(self, models_config: ModelsConfig) -> dict[str, str | None]:
        """Merge built-in MODEL_MAP with config [models.pi] overrides."""
        merged = dict(self.BUILTIN_MODEL_MAP)
        merged.update(models_config.profiles.get(self.name, {}))
        return merged

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        canonical = resolve_alias(name, models_config)
        model_map = self._effective_map(models_config)
        if canonical in model_map:
            mapped = model_map[canonical]
            if mapped is None:
                raise ValueError(f"Model '{name}' is not available on the pi harness.")
            return mapped
        return canonical  # passthrough: user may be using a pi-native identifier

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        return [(k, v) for k, v in self._effective_map(models_config).items() if v is not None]

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        cmd = cmd_override or "pi"
        args = [cmd, "--mode", "json", "-p", "--no-session", "--no-extensions",
                "--append-system-prompt", system_prompt_file]

        # Always load research and web_fetch
        args += ["-e", f"{self._ext_dir}/research.ts",
                 "-e", f"{self._ext_dir}/web-fetch/index.ts"]

        # Load requested tools as pi extensions
        tool_paths = self.get_tool_paths()
        for tool in tools:
            if tool in tool_paths:
                args += ["-e", tool_paths[tool]]

        if model:
            mc = models_config or ModelsConfig()
            args += ["--model", self.resolve_model(model, mc)]
        args.append(prompt)
        return args

    def build_tmux_wrapper(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt_file: str,
        session_dir: str,
        exit_code_file: str,
        results_file: str,
        auto_close: int | None = None,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> str:
        """Generate a bash wrapper that:
          1. Runs interactive pi with --session-dir
          2. After exit, runs the pi session adapter to produce results_file
          3. Writes exit_code_file
        """
        cmd = cmd_override or "pi"
        pi_args = ["--no-extensions", "--append-system-prompt", system_prompt_file,
                   "--session-dir", session_dir]
        pi_args += ["-e", f"{self._ext_dir}/research.ts",
                    "-e", f"{self._ext_dir}/web-fetch/index.ts"]
        tool_paths = self.get_tool_paths()
        for tool in tools:
            if tool in tool_paths:
                pi_args += ["-e", tool_paths[tool]]
        if auto_close and auto_close > 0:
            pi_args += ["-e", f"{self._ext_dir}/planner/auto-quit.ts"]
        if model:
            mc = models_config or ModelsConfig()
            pi_args += ["--model", self.resolve_model(model, mc)]
        pi_args.append(f"@{prompt_file}")

        adapter_cmd = f"python3 {self._wf_dir}/adapters/pi_session.py {session_dir} {results_file}"

        return f"""#!/bin/bash
RESULT_FILE='{exit_code_file}'
_cleanup() {{ if [ ! -f "$RESULT_FILE" ]; then echo 1 > "$RESULT_FILE"; fi }}
trap _cleanup EXIT HUP TERM INT
{f'export PI_AUTO_CLOSE_DELAY={auto_close}' if auto_close and auto_close > 0 else ''}
{cmd} {' '.join(shlex.quote(a) for a in pi_args)}
{adapter_cmd}
echo $? > "$RESULT_FILE"
"""

    def parse_headless_output(self, stdout: str) -> dict:
        return pi_json_mode.parse(stdout)

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        return pi_session.parse(session_dir, results_file)

    def get_tool_paths(self) -> dict[str, str]:
        return {
            "report-result": f"{self._wf_dir}/tools/pi_extensions/report-result-tool.ts",
            "submit-plan": f"{self._wf_dir}/tools/pi_extensions/submit-plan-tool.ts",
            "record-brainstorm": f"{self._wf_dir}/tools/pi_extensions/record-brainstorm-tool.ts",
        }

    @property
    def supports_tmux(self) -> bool:
        return True

    @property
    def _wf_dir(self) -> str:
        """Root of the wf installation (parent of profiles/)."""
        return str(Path(__file__).parent.parent)

    @property
    def _ext_dir(self) -> str:
        """Pi extensions directory (~/.pi/agent/extensions)."""
        return str(Path.home() / ".pi" / "agent" / "extensions")
```

### `profiles/claude_code.py` - Claude Code Runner Profile

```python
from adapters import claude_stream_json
from profiles import resolve_alias

class ClaudeCodeProfile:
    name = "claude-code"

    # Built-in canonical name → exact claude CLI model string.
    # Identity for Anthropic models. Non-Anthropic models are not available.
    # None = explicitly unavailable (resolve_model raises with a clear message).
    # Users can override/extend this via [models.claude-code] in config.
    BUILTIN_MODEL_MAP = {
        "claude-sonnet-4-5": "claude-sonnet-4-5",
        "claude-opus-4": "claude-opus-4",
        "claude-haiku-4-5": "claude-haiku-4-5",
        "gpt-4o": None,            # not available on Claude Code
        "gpt-4o-mini": None,       # not available on Claude Code
        "gemini-pro": None,        # not available on Claude Code
    }

    def _effective_map(self, models_config: ModelsConfig) -> dict[str, str | None]:
        merged = dict(self.BUILTIN_MODEL_MAP)
        merged.update(models_config.profiles.get(self.name, {}))
        return merged

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        canonical = resolve_alias(name, models_config)
        model_map = self._effective_map(models_config)
        if canonical in model_map:
            mapped = model_map[canonical]
            if mapped is None:
                raise ValueError(
                    f"Model '{name}' (canonical: '{canonical}') is not available "
                    f"on the claude-code harness. Available models: "
                    f"{', '.join(k for k, v in model_map.items() if v is not None)}"
                )
            return mapped
        return canonical  # passthrough

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        return [(k, v) for k, v in self._effective_map(models_config).items() if v is not None]

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        cmd = cmd_override or "claude"
        args = [cmd, "-p", "--bare", "--output-format", "stream-json",
                "--append-system-prompt-file", system_prompt_file]

        # Claude Code uses MCP servers for custom tools
        if tools:
            mcp_config = self._build_mcp_config(tools)
            args += ["--mcp-config", json.dumps(mcp_config)]

        if model:
            mc = models_config or ModelsConfig()
            args += ["--model", self.resolve_model(model, mc)]
        args.append(prompt)
        return args

    def build_tmux_wrapper(self, **kwargs) -> str:
        """Claude Code's interactive mode does not use --session-dir in
        the same way as pi. The wrapper runs `claude` interactively,
        then invokes the stream-json adapter on any captured output.
        Details TBD - Claude Code's interactive session format may
        differ from its -p output.
        """
        raise NotImplementedError(
            "Claude Code tmux support is not yet implemented. "
            "Use --no-tmux for headless execution."
        )

    def parse_headless_output(self, stdout: str) -> dict:
        return claude_stream_json.parse(stdout)

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        raise NotImplementedError("Claude Code session parsing not yet implemented")

    def get_tool_paths(self) -> dict[str, str]:
        return {
            "report-result": f"mcp://{self._wf_dir}/tools/mcp_server.py",
            "submit-plan": f"mcp://{self._wf_dir}/tools/mcp_server.py",
            "record-brainstorm": f"mcp://{self._wf_dir}/tools/mcp_server.py",
        }

    @property
    def supports_tmux(self) -> bool:
        return False  # not yet implemented

    def _build_mcp_config(self, tools: list[str]) -> dict:
        """Build MCP server config that exposes the requested tools.
        Points to the bundled mcp_server.py which reads schemas from
        wf schema --component and validates inputs.
        """
        return {
            "mcpServers": {
                "wf-tools": {
                    "command": "python3",
                    "args": [f"{self._wf_dir}/tools/mcp_server.py", "--tools", ",".join(tools)],
                }
            }
        }

    @property
    def _wf_dir(self) -> str:
        return str(Path(__file__).parent.parent)
```

### `profiles/mock.py` - Mock Profile for E2E Tests

```python
class MockProfile:
    """Deterministic mock profile for E2E testing.

    Reads WF_TEST_SCENARIO env var to locate the scenario file.
    Runs the mock_agent.py script (from tests/e2e/) which reads
    the scenario, performs scripted file operations, and writes
    results.json directly. No real agent, no adapters, no parsing.
    """
    name = "mock"

    def resolve_model(self, name: str, models_config: ModelsConfig) -> str:
        return resolve_alias(name, models_config)  # resolve aliases, no harness-specific mapping

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        return []  # mock doesn't have real models

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
    ) -> list[str]:
        mock_agent = cmd_override or f"{self._wf_dir}/tests/e2e/mock_agent.py"
        # The mock agent reads the brief from a file, not argv
        return ["python3", mock_agent, prompt]

    def build_tmux_wrapper(self, **kwargs) -> str:
        raise NotImplementedError("Mock profile does not support tmux")

    def parse_headless_output(self, stdout: str) -> dict:
        # Mock agent writes results.json directly; stdout is ignored
        return {}  # runner reads results.json from the expected path

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        raise NotImplementedError("Mock profile does not have sessions")

    def get_tool_paths(self) -> dict[str, str]:
        return {}  # mock agent doesn't need tool extensions

    @property
    def supports_tmux(self) -> bool:
        return False

    @property
    def _wf_dir(self) -> str:
        return str(Path(__file__).parent.parent)
```

### How Profiles Are Selected

The config determines the profile:

```toml
# ~/.config/wf/config.toml
[agent]
profile = "pi"              # which profile to use
# cmd = "/custom/path/to/pi"  # optional: override binary path
```

The `profile` field selects the full behavior set: command construction, output parsing, tool loading. The `cmd` field optionally overrides just the binary path within that profile (e.g. a custom pi build at a non-standard location). This is passed through to `build_headless_cmd(cmd_override=config.agent.cmd)`.

CLI flags:
- `wf execute --profile claude-code` - ephemeral override for this invocation
- `wf init --set agent.profile=claude-code` - snapshot into the record

---

## `wflib/runner.py`

Agent subprocess spawning. **Profile-driven - zero harness-specific code.**

The runner is the bridge between the scheduler and the profile. It handles process lifecycle (tmpdir, spawn, wait, cleanup, durability) while delegating all harness-specific decisions (command construction, output parsing, tool loading) to the active profile.

### Agent Output Contract

`wf` does not parse harness-internal formats (pi session files, pi `--mode json` events, Claude Code stream-json, etc.) in its core code. Each spawn mode produces a standardized `results.json` in a known location. This is the **only** interface between the runner and the agent harness. How that `results.json` gets produced - which adapter runs, when it runs, what it parses - is the profile's responsibility.

**`results.json` format:**
```json
{
  "exitCode": 0,
  "messages": [{"role": "assistant", "content": [...]}],
  "usage": {"input": 23000, "output": 5400, "cacheRead": 8200, "cacheWrite": 3100, "cost": 0.045, "turns": 3},
  "model": "claude-sonnet-4-5",
  "provider": "anthropic"
}
```

`messages` is a flat list of conversation messages with `role` and `content` fields. Content blocks include `{"type": "text", "text": "..."}` and `{"type": "toolCall", "name": "report_result", "arguments": {...}}`. This is the minimal subset needed for `extract_report_result` to find the structured completion report, and `extract_summary_fallback` to grab the last assistant text.

**Why this matters for reuse:** The current planner imports `SessionManager` from `@mariozechner/pi-coding-agent` to read tmux-mode session files. A Python rewrite would have to reimplement that parsing - duplicating internal knowledge of pi's session format. The profile+adapter pattern keeps that knowledge in one thin, replaceable layer and gives `runner.py` a single code path for reading results regardless of harness or spawn mode.

**Future direction:** If pi grows a `pi --export-results <session-dir> <output-file>` command, the pi profile's adapter could delegate to it instead of reimplementing the parsing. This would make the adapter a one-liner and keep pi's session format fully encapsulated in pi.

```python
from profiles import get_profile, RunnerProfile

@dataclass
class AgentResult:
    exit_code: int
    summary: str
    notes: str
    error: str | None
    usage: Usage
    model: str | None = None
    provider: str | None = None
    messages: list[dict] = field(default_factory=list)  # raw messages for tool call extraction

def spawn_headless(
    cwd: str,
    prompt: str,
    system_prompt: str,
    profile: RunnerProfile,
    tools: list[str],
    model: str | None = None,
    cmd_override: str | None = None,
    models_config: ModelsConfig | None = None,
) -> AgentResult
    """Spawn a headless agent subprocess.

    The runner:
      1. Writes system prompt to tmpfile
      2. Asks the profile for the command:
         profile.build_headless_cmd(..., models_config=models_config)
      3. Spawns the subprocess, captures stdout/stderr
      4. Asks the profile to parse output: profile.parse_headless_output(stdout)
      5. Copies results to docs/workflows/.sessions/ (durable location)
      6. Reads results into AgentResult
      7. Tmpdir cleaned up

    The profile handles all harness-specific decisions: which flags,
    which output format, how to load tools, model name resolution.
    The runner handles universal concerns: tmpdir, subprocess lifecycle,
    durability, abort handling (SIGTERM then SIGKILL after 5s), result extraction.
    """

def spawn_in_tmux(
    cwd: str,
    prompt: str,
    system_prompt: str,
    profile: RunnerProfile,
    tools: list[str],
    task_id: str,
    task_title: str,
    workflow_label: str,
    model: str | None = None,
    auto_close: int | None = None,
    cmd_override: str | None = None,
    preserve_session_dir: str | None = None,
    models_config: ModelsConfig | None = None,
) -> AgentResult
    """Spawn agent in a tmux pane. Wait for completion via exit-code file.

    The runner:
      1. Writes prompt and system prompt to tmpfiles
      2. Asks the profile for the wrapper script: profile.build_tmux_wrapper(...)
      3. Writes and executes the wrapper in a tmux pane
      4. Polls for exit-code file (primary) + pane existence (fallback)
      5. Reads results.json (produced by the wrapper's adapter step)
      6. Copies results to docs/workflows/.sessions/ (durable location)
      7. Reads results into AgentResult
      8. Tmpdir cleaned up

    The profile's wrapper script is responsible for producing results.json
    before writing exit-code file. This ensures results survive even if
    the scheduler crashes during step 6-7.

    Raises NotImplementedError if profile.supports_tmux is False.
    """

def _read_agent_results(results_path: str) -> AgentResult
    """Read a results.json file into an AgentResult.
    Runs extract_report_result on messages for summary/notes.
    Falls back to extract_summary_fallback if no tool call found.
    Single code path - used by both spawn_headless and spawn_in_tmux,
    regardless of which profile produced the results.
    """

def extract_report_result(messages: list[dict]) -> ReportResult | None
    """Extract ReportResult from the agent's messages.
    Delegates to extract_tool_call(messages, 'report_result') from types.py,
    then wraps the result in a ReportResult dataclass.
    Returns None if the agent didn't call report_result.
    """

def extract_summary_fallback(messages: list[dict]) -> str
    """Fallback when report_result was not called.
    Returns last 500 chars of the last assistant message's text content.
    This is the degraded path - it means the agent didn't finish cleanly.
    """
```

---

## `tools/` - Subagent Tool Implementations

Subagent tools (`report_result`, `submit_plan`, `record_brainstorm`) need to be available to agents regardless of which harness runs them. Each harness has its own tool loading mechanism, so `wf` ships one implementation per mechanism:

### `tools/pi_extensions/` - Pi Tool Extensions (TypeScript)

Three small TypeScript files, each following the pi extension API. Each uses a TypeBox schema that mirrors the corresponding `$defs` in `workflow.schema.json`. The pi runner profile loads them via `-e <path>`.

**Schema consistency:** A small Node test (`tools/pi_extensions/schema-consistency.test.ts`) loads the TypeBox schemas and the JSON Schema `$defs` (via `wf schema --component ...`), then runs the same valid/invalid fixtures through both validators. This catches drift without requiring automated generation. The Python test suite only asserts that the JSON Schema components are internally valid and loadable.

- **`report-result-tool.ts`** - schema from `$defs/ReportResult`. Implementation agents call this when done.
- **`submit-plan-tool.ts`** - schema from `$defs/Plan`. Planning and review agents call this.
- **`record-brainstorm-tool.ts`** - schema from `$defs/Brainstorm`. Brainstorm agents call this.

All three are validate-and-return - they don't write to the record or do any I/O beyond schema validation. `wf` extracts the tool call from `results.json` messages after the session ends.

### `tools/mcp_server.py` - MCP Tool Server (Python)

A single Python MCP server that exposes all three tools. Used by Claude Code (via `--mcp-config`) and any future MCP-based harness. Accepts a `--tools` flag to expose only a subset (e.g. `--tools report-result` for implementation agents, `--tools submit-plan` for review agents).

Reads schemas from `wf schema --component <name>` at startup. Validates inputs against the schema. Returns success with the validated data. Same validate-and-return pattern as the pi extensions.

Pure stdlib Python - no external dependencies. Uses the MCP stdio transport protocol (JSON-RPC over stdin/stdout), which is simple enough to implement in ~100 lines without an MCP SDK.

### Why Tools Ship with `wf`, Not with Wrappers

In the earlier design, subagent tool extensions lived with the pi wrapper (`~/.pi/agent/extensions/wf/`). This created a circular dependency: the runner needed to know where the wrapper installed its extensions, and the extensions had to be installed before any workflow could execute. Moving tools into the `wf` repo eliminates this:

- The runner profile resolves tool paths relative to the `wf` install directory
- Tools are always present if `wf` is installed - no separate wrapper installation step
- Adding a new harness means adding a profile + adapter - if the harness uses MCP, the tools are already available; if it uses a different mechanism, add one more implementation to `tools/`

---

## `adapters/` - Output Format Parsers

Pure functions that parse harness-specific output into the standardized results dict. No command construction, no subprocess management, no tool loading - just output → results. Profiles call adapters; adapters know nothing about profiles.

- **`pi_json_mode.py`** - parses pi `--mode json` stdout (NDJSON event stream: `message_end`, `tool_result_end` events) into results dict with messages, usage, model, provider.
- **`pi_session.py`** - parses pi session `.jsonl` files (same message format as pi's `SessionManager`) into results dict.
- **`claude_stream_json.py`** - parses Claude Code `--output-format stream-json` stdout (NDJSON: `text`, `tool_use`, `tool_result` events) into results dict.

Adapters are shared across profiles where formats overlap. A future harness that emits pi-compatible JSON events could reuse `pi_json_mode.py` directly.

---

## `wflib/tmux.py`

Tmux pane/window management.

```python
# --- Detection ---
def is_tmux_available() -> bool
    """Check if tmux is installed and a session is running.
    When this returns False and config.ui.tmux is True, callers
    warn to stderr and fall back to headless mode. Never hard fail.
    """
def get_current_window_id() -> str
def select_window(window_id: str) -> None

# --- Execution window state (module-level, reset between runs) ---
def reset_execution_window() -> None
def get_or_create_execution_pane(
    cwd: str,
    command: str,
    workflow_label: str,
    task_id: str,
    task_title: str,
) -> str    # returns pane_id

# --- Pane lifecycle ---
def pane_exists(pane_id: str) -> bool
def wait_for_exit_code_file(exit_code_file: str, pane_id: str) -> None
    """Poll for completion. Fallback: check pane existence."""

# --- Helpers ---
def shell_escape(s: str) -> str
```

---

## `wflib/git.py`

Thin git wrapper.

```python
@dataclass
class GitResult:
    ok: bool
    stdout: str
    stderr: str

def git(args: list[str], cwd: str, timeout: int = 60) -> GitResult
    """Run a git command. Returns GitResult."""

def is_git_repo(cwd: str) -> bool
def is_clean(cwd: str) -> bool
def get_dirty_files(cwd: str) -> list[str]
def get_current_branch(cwd: str) -> str
def get_head(cwd: str, short: bool = False) -> str
def get_head_full(cwd: str) -> str | None
```

---

## `wflib/worktree.py`

Git worktree lifecycle - create, setup deps, merge back, cleanup.

```python
@dataclass
class WorktreeInfo:
    path: str
    branch: str
    main_branch: str

@dataclass
class MergeResult:
    success: bool
    conflicts: str | None = None
    conflict_files: list[str] | None = None
    resolution_attempted: bool = False         # True if a conflict resolution agent was spawned
    resolution_succeeded: bool = False         # True if the agent resolved all conflicts

@dataclass
class WorkflowCloseResult:
    merge_state: str             # "clean" | "conflicted" | "failed"
    conflict_files: list[str]
    conflicts: str
    diff_stat: str

# --- Task worktrees (for parallel execution) ---

def create_task_worktree(cwd: str, workflow_id: str, task_id: str) -> WorktreeInfo
    """Create worktree + branch from HEAD. Cleans up stale if exists."""

def setup_worktree(main_cwd: str, worktree_path: str) -> None
    """Run .worktree-setup if present, else symlink dep dirs."""

def symlink_deps(main_cwd: str, worktree_path: str) -> None
    """Symlink node_modules, .venv, vendor, etc."""

def commit_if_dirty(worktree_path: str, task_id: str, title: str) -> bool
    """Stage all + commit with [workflow] prefix. Returns True if committed.
    Excludes docs/workflows/ - the record file is owned by the scheduler
    in the main repo, not by task subagents. Prevents stale record copies
    from merging back and overwriting the scheduler's updates.
    Uses: git add -A -- ':!docs/workflows/'
    """

def merge_back(main_cwd: str, wt: WorktreeInfo) -> MergeResult
    """Rebase onto main, then fast-forward merge. Serialized by caller."""

def cleanup_worktree(main_cwd: str, wt: WorktreeInfo) -> None
    """Remove worktree + branch. Idempotent."""

# --- Workflow worktrees (for init/close multi-workflow isolation) ---

def create_workflow_worktree(cwd: str, workflow_name: str) -> WorktreeInfo
    """Create ../<repo>-wf-<name>/ on branch wf-<name>."""

def close_workflow_worktree(main_cwd: str, wt: WorktreeInfo) -> WorkflowCloseResult
    """Rebase + merge, or fall back to merge --no-commit on conflict."""

def commit_or_amend_workflow_files(cwd: str, workflow_name: str) -> bool
    """Commit docs/workflows/. Amends if last commit is [workflow-init]."""

def commit_remaining_changes(cwd: str, message: str) -> bool
    """Stage all + commit with caller's message."""
```

---

## `wflib/review.py`

Code review orchestration - diff context building and review agent spawning.

```python
def build_diff_context(cwd: str, base_commit: str | None = None) -> str
    """Build markdown diff context (commits, stat, full diff).
    Caps full diff at 100KB. Falls back to uncommitted changes.
    """

async def run_review(
    cwd: str,
    config: WorkflowConfig,
    base_commit: str | None = None,
    description: str | None = None,
    scope: str | None = None,
    cli_model: str | None = None,
) -> ReviewResult
    """Spawn a code review subagent.
    Reads profile, tmux, auto_close from config. Resolves the runner
    profile and delegates spawning to runner.py.
    Uses config.model.review as default model; cli_model overrides.
    """

async def run_auto_review(
    cwd: str,
    config: WorkflowConfig,
    base_commit: str | None = None,
    cli_model: str | None = None,
) -> AutoReviewResult
    """Spawn review agent with submit_plan tool.
    Reads profile, tmux, auto_close from config. Resolves the runner
    profile and delegates spawning to runner.py.
    Uses config.model.review as default model; cli_model overrides.
    Returns optional fixup plan extracted from tool call.
    """

def extract_plan_from_messages(messages: list[dict]) -> dict | None
    """Extract a fixup plan from the review agent's messages.
    Delegates to extract_tool_call(messages, 'submit_plan') from types.py.
    Returns plan dict or None if the reviewer found no actionable issues.
    """

@dataclass
class ReviewResult:
    review_text: str
    usage: Usage
    model: str | None = None
    provider: str | None = None

@dataclass
class AutoReviewResult(ReviewResult):
    plan: Plan | None = None      # fixup plan, if issues found
```

---

## `wflib/render.py`

All text rendering - markdown, usage tables, status formatting.

```python
def render_record_markdown(record: WorkflowRecord) -> str
    """Full human-readable markdown rendering of an entire workflow record.
    Replaces the old per-plan .md files.
    """

def render_plan_markdown(plan: Plan) -> str
    """Render just the plan portion as markdown."""

def format_usage_table(rows: list[UsageRow]) -> str
    """Markdown table with per-phase and total token usage."""

def format_history_table(records: list[WorkflowRecord], limit: int = 20) -> str
    """Plain text table of recent workflows. Scans record files instead of
    a separate history log.
    """

def format_status(record: WorkflowRecord) -> str
    """Multi-line status summary (current phase, task list, usage totals)."""

def format_execution_summary(record: WorkflowRecord) -> str
    """Final execution report with task results and usage table."""

def format_model_summary(
    tasks: list[Task],
    default_model: str | None = None,
    execute_model: str | None = None,
) -> str
    """Pre-execution model resolution summary."""

@dataclass
class UsageRow:
    label: str
    input: int
    output: int
    cache_read: int
    cache_write: int
    cost: float
    turns: int
    model: str | None = None

def fmt_num(n: int) -> str
def fmt_cost(n: float) -> str
def fmt_duration(seconds: int) -> str
def slugify(text: str) -> str
def workflow_label(workflow_id: str, name: str) -> str
```

---

## Templates

Reusable prompt fragments with variable substitution. Harness-agnostic - any wrapper can discover and render them.

### Structure

Templates live in two places, with project-level overriding shipped defaults:

1. **Shipped defaults** - `wf/templates/` in the `wf` install (read-only)
2. **Project-level** - `docs/workflows/templates/` in the project repo (user-editable)

Each template is a markdown file with YAML frontmatter:

```markdown
---
description: Quality check a recent implementation
---
We just finished some new work.

$@

This project values above all else implementation simplicity and reuse of
available framework/library components and common well-understood patterns
in an effort to have the highest possible long-term maintainability for
agentic developers. Please carefully analyze this implementation...
```

Placeholders:
- `$1`, `$2`, ... - positional arguments
- `$@` - all arguments joined with spaces

Project-level templates with the same filename as a shipped default override it. This lets projects customize the brainstorming or review style without forking `wf`.

### Shipped Defaults

These ship with `wf` and carry forward the wisdom from the current pi prompt templates and skills. All are **ported verbatim** - they work well and should not be rewritten.

| File | Source | Content |
|------|--------|---------|
| `brainstorm.md` | `~/.pi/agent/prompts/help-me-brainstorm.md` | Iterative brainstorming: present alternatives with pros/cons, identify gaps, discuss tradeoffs, verify readiness. "Values simplicity and reuse of framework/library components for long-term maintainability by agentic developers." |
| `check-implementation.md` | `~/.pi/agent/prompts/check-implementation.md` | Quality check: custom/complex implementation, code brevity, unnecessary hoisting/redirection, code duplication, test coverage/potency, error handling. |
| `execute-plan-step.md` | `~/.pi/agent/prompts/execute-plan-step.md` | Single step execution: read the plan, implement only step N, stop on contradictions, write tests, verify changes, report difficulties. |
| `write-plan-to-file.md` | `~/.pi/agent/prompts/write-plan-to-file.md` | Write a plan to file: independent and logically sequenced steps, no contradictions, scoped small enough, testing is part of each step. |

These are **not** the same as the system prompts in `wf/prompts/` (which are injected into subagent contexts). Templates are user-invokable fragments for interactive conversation.

### CLI Commands

```
wf template list [--cwd DIR]

    List available templates (shipped + project-level). Shows name and
    description. Project-level overrides are marked.

    stdout: formatted table

wf template show <name> [--cwd DIR]

    Show a template's full content (frontmatter + body) without rendering.

    stdout: raw template content

wf template render <name> [args...] [--cwd DIR]

    Render a template with argument substitution. Resolves project-level
    first, then shipped defaults.

    $1, $2, ... replaced by positional args.
    $@ replaced by all args joined with spaces.

    stdout: rendered text (ready to inject into conversation)
```

### How Harness Wrappers Use This

The pi wrapper (or any harness) calls `wf template list` to discover available templates, presents them as slash commands or autocompletions, and calls `wf template render <name> <args>` when the user invokes one. The rendered text is injected into the conversation as a user message.

For pi specifically, this replaces the current `~/.pi/agent/prompts/` directory as the template source - the wrapper reads from `wf` instead of its own prompts directory.

### `wflib/templates.py`

```python
SHIPPED_DIR = "<wf_install>/templates"    # alongside wflib/
PROJECT_DIR = "docs/workflows/templates"  # in the project repo

@dataclass
class Template:
    name: str                              # filename without .md
    description: str                       # from YAML frontmatter
    body: str                              # raw body with placeholders
    source: str                            # "shipped" | "project"
    path: str                              # absolute path to the file

def list_templates(cwd: str) -> list[Template]
    """Discover templates from both shipped and project directories.
    Project-level overrides shipped defaults with the same name.
    Returns sorted by name.
    """

def load_template(name: str, cwd: str) -> Template
    """Load a template by name. Project-level first, then shipped.
    Raises FileNotFoundError if not found in either location.
    """

def render_template(template: Template, args: list[str]) -> str
    """Render a template with argument substitution.
    $1, $2, ... replaced by positional args (empty string if missing).
    $@ replaced by all args joined with spaces.
    Returns the rendered body (frontmatter stripped).
    """

def parse_frontmatter(content: str) -> tuple[dict, str]
    """Split YAML frontmatter from body. Returns (metadata, body).
    If no frontmatter, returns ({}, full content).
    """
```

---

## `wflib/log.py`

Debug logging - append-only JSONL file.

```python
LOG_PATH = "~/.wf/debug.log"

def log(event: str, **data) -> None
    """Append a JSON line to the debug log. Non-fatal.
    Verbose fallback for truly obscure issues. For normal investigation,
    the events array in the record is the primary source.
    """

def status_snap(statuses: dict[str, TaskStatus]) -> str
    """Compact status string: 'task-1:done task-2:running ...'"""
```

---

## `wflib/completions.py`

Shell completion script generation and dynamic completion callback. Self-contained - no imports from scheduler, record, runner, or any other wflib module. Knows only the static CLI surface (subcommands, flags per subcommand) and how to shell out to query commands for dynamic completions.

```python
# --- Script generation ---

def generate_bash() -> str
    """Return a complete bash completion script.

    The script:
      1. Completes subcommand names after `wf `
      2. Completes flags per subcommand (hardcoded in the script)
      3. Calls `wf --complete <context>` for dynamic values:
         - workflow names after positional args that expect them
         - task IDs after `execute-task <workflow>`
         - template names after `template show` / `template render`
         - help topics after `help`
         - `--component` values after `schema --component`
      4. Handles `--model` flags by not completing (wf has no model
         registry - harness wrappers fill this gap)

    Install: eval "$(wf completions bash)"  # in .bashrc
    """

def generate_zsh() -> str
    """Return a complete zsh completion script.

    Same logic as bash but uses zsh's _arguments / _describe for
    richer display (flag descriptions, grouped completions).

    Install: eval "$(wf completions zsh)"  # in .zshrc
    Or: wf completions zsh > ~/.zfunc/_wf && fpath+=(~/.zfunc)
    """

def generate_fish() -> str
    """Return a complete fish completion script.

    Uses fish's `complete -c wf` commands.

    Install: wf completions fish > ~/.config/fish/completions/wf.fish
    """

# --- Dynamic completion callback ---

def complete(words: list[str], cwd: str) -> list[str]
    """Return completions for the current command line context.

    Called by the generated shell script via `wf --complete <words...>`.
    Fast, no side effects. Returns one completion per line on stdout.

    Dispatches based on what the words indicate is being completed:

      wf execute <TAB>              → workflow names (scan docs/workflows/)
      wf execute-task wf1 <TAB>     → task IDs (read record, return ids)
      wf execute --model <TAB>      → nothing (wf has no model registry)
      wf template show <TAB>        → template names (scan both dirs)
      wf template render <TAB>      → template names
      wf schema --component <TAB>   → component names (hardcoded)
      wf help <TAB>                 → topic names (hardcoded)
      wf status <TAB>               → workflow names
      wf close <TAB>                → workflow names
      wf --complete <TAB>           → nothing (avoid recursion)

    Dynamic lookups are lightweight:
      - Workflow names: os.listdir('docs/workflows/'), strip .json
      - Task IDs: json.load the record, extract plan.tasks[].id
      - Template names: os.listdir both template dirs, strip .md
    All are direct filesystem reads - no subprocess spawning.
    """

# --- Internals ---

# Static data baked into generated scripts and used by complete()
SUBCOMMANDS: list[str]  # ["init", "run", "brainstorm", ...]
FLAGS: dict[str, list[str]]  # subcommand → ["--cwd", "--model", ...]
COMPONENT_NAMES: list[str]  # ["plan", "brainstorm", "task", "report-result", "usage"]
```

### Design Notes

**Zero dependencies on wflib internals.** The module does not import `record.py`, `types.py`, or anything else. Dynamic completions read JSON files directly with `json.load` and scan directories with `os.listdir`. This keeps it trivially testable and avoids import-time side effects during completion (which must be fast and silent).

**Python startup latency.** The generated shell scripts call `wf --complete <words>` for dynamic completions. Python startup is ~30-50ms, plus ~10-20ms for a directory scan or JSON read. Total ~50-70ms per tab press - well within the ~100ms threshold where completions feel instant.

**`--complete` is a hidden internal interface.** It is not listed in `wf help`, not documented for users, and not part of the public CLI contract. The generated scripts are the only intended caller. The word list format matches the shell's `COMP_WORDS` (bash) or equivalent.

**No model completions.** `wf` deliberately does not complete `--model` values. It has no model registry - that's harness-specific. In pi, the wrapper's `getArgumentCompletions` fills this gap using `modelRegistry.getAvailable()`. In a bare terminal, the user types the model name.

---

## `bin/wf` - CLI Entry Point

```
#!/usr/bin/env python3
"""wf - structured AI development workflows.

Usage:
    wf init <name> [options]
    wf run <workflow> [options]
    wf brainstorm <workflow> [options]
    wf plan <workflow> [options]
    wf record-brainstorm <workflow> [--cwd DIR]
    wf submit-plan <workflow> [--cwd DIR]
    wf execute <workflow> [options]
    wf execute-task <workflow> <task-id> [options]
    wf review <workflow> [options]
    wf auto-review <workflow> [options]
    wf close <workflow> [options]
    wf status <workflow> [--cwd DIR]
    wf list [--cwd DIR]
    wf history [--json] [--limit N] [--cwd DIR]
    wf render <workflow> [--cwd DIR]
    wf validate <file>
    wf brief <workflow> <task-id> [--cwd DIR]
    wf recover <workflow> [--cwd DIR]
    wf schema [--component NAME]
    wf config [list|get|set] [options]
    wf template list [--cwd DIR]
    wf template show <name> [--cwd DIR]
    wf template render <name> [args...] [--cwd DIR]
    wf completions <shell>
    wf help [topic]

Init options:
    --cwd DIR               Project directory (default: .)
    --no-worktree           Work directly in the main repo
    --set KEY=VALUE         Override config for this workflow (repeatable)
                            Uses dotted keys: --set model.plan=claude-opus-4
                            --set automation.implement=automatic
                            --set execute.concurrency=8

Run options:
    --cwd DIR               Working directory (default: .)
    --model MODEL           Override model for all phases (ephemeral)
    --prompt TEXT            Initial problem description (passed to brainstorm/plan)
    --concurrency N         Override max parallel tasks (ephemeral)
    --no-worktrees          Override worktree isolation (ephemeral)
    --no-tmux               Override tmux usage (ephemeral)
    --auto-close [SECONDS]  Override auto-close delay (ephemeral)

Brainstorm options:
    --cwd DIR               Working directory (default: .)
    --model MODEL           Override model for the brainstorm agent (ephemeral)
    --prompt TEXT            Initial message / problem description
                            (required for --no-tmux, optional for tmux)
    --no-tmux               Override tmux usage (ephemeral)
    --auto-close [SECONDS]  Override auto-close delay (ephemeral)

Plan options:
    --cwd DIR               Working directory (default: .)
    --model MODEL           Override model for the planning agent (ephemeral)
    --prompt TEXT            Additional guidance (appended to brainstorm context)
    --no-tmux               Override tmux usage (ephemeral)
    --auto-close [SECONDS]  Override auto-close delay (ephemeral)

Execute options:
    --cwd DIR               Working directory (default: .)
    --model MODEL           Override model for all tasks (ephemeral)
    --concurrency N         Override max parallel tasks (ephemeral)
    --no-worktrees          Override worktree isolation (ephemeral)
    --no-tmux               Override tmux usage (ephemeral)
    --auto-close [SECONDS]  Override auto-close delay (ephemeral)
    --auto-review           Override auto-review setting (ephemeral)
    --review-model MODEL    Override model for review subagent (ephemeral)

Review options:
    --cwd DIR
    --ref COMMIT            Base commit to diff against
    --desc DESCRIPTION      Description of work being reviewed
    --scope FILES           Focus scope
    --model MODEL           Override model for review agent (ephemeral)
    --no-tmux               Override tmux usage (ephemeral)
    --auto-close [SECONDS]  Override auto-close delay (ephemeral)

Close options:
    --cwd DIR
    --model MODEL           Override model for conflict resolution (ephemeral)

Config options:
    wf config list [--cwd DIR] [--show-origin]
    wf config get <key> [--cwd DIR]
    wf config set <key>=<value> [--user|--project] [--cwd DIR]
"""
```

### Subcommand Details

**`wf init <name>`**
- **Requires a git repository.** `wf init` refuses to run outside a git repo (exits with error: `"Not a git repository"`). Git is required for `sourceBranch`/`sourceCommit` tracking, worktree isolation, diff-based review, and merge-back on close. Non-git usage is not supported.
- Resolves the full `WorkflowConfig` by merging: baked-in defaults < user config (`~/.config/wf/config.toml`) < project config (`.wf/config.toml`) < `--set` overrides
- Validates preconditions (git repo, clean working tree if worktree mode)
- Creates `docs/workflows/` directory
- Writes initial record file with `status: init` and the resolved `workflow.config` snapshot - **first**, before worktree creation, so that if any subsequent step fails, the record exists and captures the error
- Captures `sourceBranch`, `sourceCommit`
- **Commits the record** via `git add docs/workflows/<name>.json && git commit -m "[workflow-init] <name>"`. This commit is required so the worktree (created next) branches from a state that includes the record.
- Creates workflow worktree at `../<repo>-wf-<name>/` (unless `--no-worktree` or `config.execute.worktrees` is false). The worktree branches from the commit above, so it contains the record file at `docs/workflows/<name>.json`. **All subsequent commands operate in the worktree** — the record lives there, is updated there, and is merged back to the source branch by `wf close`.
- Runs `.worktree-setup` hook if present
- On any failure after record creation: updates record with error details and `status: failed`
- stdout: JSON `{"workflowId": "...", "recordFile": "...", "worktree": "...", "configSources": ["defaults", "user", "project", "overrides"]}`

**`wf run <workflow>`**
- The single entry point for walking through the full workflow lifecycle
- Reads `workflow.status` from the record to determine the current phase
- For each remaining phase, runs the appropriate command with settings from `workflow.config` - the init-time snapshot determines automation levels, models, concurrency, etc.
- Blocks on each phase, shows unified progress output, then advances to the next
- On phase failure (execution failures, tool not called, merge conflict): stops and reports. User investigates, then runs `wf run` again to resume from the current phase
- Resumable by design: `wf run <workflow>` always reads the current status and picks up where it left off - whether resuming after a failure, a ctrl-c, or a fresh terminal
- `--prompt` is passed to brainstorm as the initial problem description and to plan as additional guidance (appended to brainstorm context from the record)
- All settings (models, automation, concurrency, tmux, auto-close) come from `workflow.config` (the init-time snapshot). CLI flags (`--model`, `--concurrency`, etc.) override for this invocation only.
- Phase-to-automation mapping (from `config.automation`):
  - `interactive` → tmux session, user drives (blocks until session ends)
  - `supervised` → tmux panes, runs autonomously (user can watch/intervene)
  - `automatic` → headless, no tmux
- Execute phase includes auto-review if `config.execute.autoReview` is true
- stdout: unified progress output per phase, final summary with total cost

**`wf brainstorm <workflow>`**
- Reads model from `config.model.brainstorm`, profile from `config.agent.profile`, tmux from `config.ui.tmux`, autoClose from `config.ui.autoClose`. CLI flags override.
- Spawns an agent session with `prompts/brainstorm.md` as system prompt
- Loads `record-brainstorm-tool` extension so agent can call `record_brainstorm`
- In tmux mode (default per config): opens interactive session - user drives the conversation
- In headless mode (`--no-tmux` flag or `config.ui.tmux` is false): agent brainstorms from `--prompt` autonomously
- After session ends: extracts last `record_brainstorm` tool call from messages
- If found: validates, writes to record, sets status to `planning`
- If not found: warns, record stays in current state
- Records session usage
- stdout: JSON `{"message": "...", "status": "planning"}` or `{"message": "...", "warning": "record_brainstorm not called"}`

**`wf plan <workflow>`**
- Reads model from `config.model.plan`, profile from `config.agent.profile`, tmux from `config.ui.tmux`, autoClose from `config.ui.autoClose`. CLI flags override.
- Spawns an agent session with `prompts/planning-context.md` as system prompt
- Loads `submit-plan-tool` extension so agent can call `submit_plan`
- Assembles initial message from brainstorm context in record (if exists) + `--prompt` (if provided)
- **Read-only enforcement is prompt-only in standalone mode.** `prompts/planning-context.md` instructs the agent "Do NOT make file changes," but the CLI does not enforce this mechanically — the agent has its full tool set and *could* make changes. If the agent modifies files, the working tree becomes dirty, which may cause `wf execute` to warn about uncommitted changes before worktree branching. Harness wrappers MAY add mechanical enforcement: pi blocks `edit`/`write`/destructive bash via its `tool_call` event hook. This is a wrapper-level enhancement, not a `wf` responsibility. Standalone users should be aware that read-only mode depends on prompt compliance.
- In tmux mode (default per config): opens interactive session - user guides exploration
- In headless mode (`--no-tmux` flag or `config.ui.tmux` is false): agent plans autonomously from context
- After session ends: extracts last `submit_plan` tool call from messages
- If found: validates plan (deps + cycles), writes to record, initializes task statuses, sets status to `implementing`
- If not found: warns, record stays in current state
- Records session usage
- stdout: JSON `{"message": "Plan submitted with N tasks", "status": "implementing"}` or `{"message": "...", "warning": "submit_plan not called"}`

**`wf record-brainstorm <workflow>`**
- Write endpoint: reads brainstorm JSON from stdin (matches `$defs/Brainstorm`)
- Validates against schema
- Writes brainstorm data into the record
- Updates `workflow.status` to `planning`
- Used by: harness wrapper tool handlers, `wf brainstorm` internally, manual piping
- `--usage JSON` — optional usage data from the calling session (see "Usage capture in inline mode" in the Harness Integration Contract)
- stdout: JSON `{"message": "Brainstorm recorded", "status": "planning"}`

**`wf submit-plan <workflow>`**
- Write endpoint: reads plan JSON from stdin (matches `$defs/Plan`)
- Validates plan (schema + dependency refs + cycle detection + heuristic warnings)
- **Re-submission policy** based on current `workflow.status`:
  - `init` or `planning`: accept, replace any existing plan. Normal path.
  - `implementing` with all tasks still `pending`: accept, replace plan. This is a revision before execution started — no work is lost.
  - `implementing` with any tasks `done`/`failed`/`running`: accept with a **warning** in the response (`"warnings": ["Replacing plan with N completed tasks. Prior results discarded."]`). The previous plan data is replaced; prior task results are lost (the `events` array retains the operational timeline). This allows mid-course correction but makes the cost explicit.
  - `reviewing`, `closing`, or `done`: **reject** with error (`"Plan submission rejected: workflow has moved past implementation (status: reviewing). Start a new workflow with wf init."`). The workflow has progressed beyond the planning phase.
- Writes plan data into the record
- Initializes `implementation.tasks` with all statuses `pending`
- Updates `workflow.status` to `implementing`
- Used by: harness wrapper tool handlers, `wf plan` internally, manual piping
- `--usage JSON` — optional usage data from the calling session (see "Usage capture in inline mode" in the Harness Integration Contract)
- stdout: JSON `{"message": "Plan submitted with N tasks", "status": "implementing", "warnings": [...]}` (warnings array is empty when there are none)

**`wf execute <workflow>`**
- Loads record, reads all execution settings from `workflow.config` (concurrency, worktrees, agent.profile, model.implement, ui.tmux, ui.autoClose). CLI flags override for this invocation.
- Auto-commits the record file and any other `docs/workflows/` content (keeps working tree clean so task worktree branches start from a committed state). Uses `commit_or_amend_workflow_files` — amends if the last commit is already a `[workflow]` commit, otherwise creates a new one. This mirrors the current planner's `commitOrAmendPlanFiles`.
- Records `implementation.baseCommit`
- Runs DAG scheduler: spawns subagents, manages worktrees, tracks results
- On merge conflict during task merge-back: automatically spawns a conflict resolution agent (using `prompts/merge-resolver.md` and the task's resolved model) before marking the task as failed. Only if resolution fails is the task marked `failed` with the worktree preserved.
- Writes results into record after each task. Saves record to disk after every state change (atomic write: tmp + rename). During execution, these writes are **uncommitted** — the working tree is dirty with record updates while tasks run. This is safe because: (a) task worktrees exclude `docs/workflows/` from commits via `git add -A -- ':!docs/workflows/'`, so stale copies never merge back; (b) the scheduler is the single writer; (c) a final commit captures the completed record state after all tasks finish.
- stdout: JSON `{"counts": {...}, "duration": N, "usageRows": [...]}`

**`wf execute-task <workflow> <task-id>`**
- Single task execution or re-run. Reads settings from `workflow.config`. CLI flags override.
- Validates deps are met
- Prompts confirmation for re-running completed tasks (if interactive)
- stdout: JSON task result

**`wf review <workflow>`**
- Reads settings from `workflow.config` (model.review, agent.profile, ui.tmux, ui.autoClose). CLI flags override.
- Reads `implementation.baseCommit` from record for diff context
- Spawns review subagent
- Appends ReviewRecord to `reviews[]`
- stdout: review text

**`wf auto-review <workflow>`**
- Like `wf review` but uses `reviewer-with-plan.md` prompt
- If review agent calls `submit_plan`, extracts fixup plan
- Executes fixup plan via the same DAG scheduler
- Results stored in `review.fixup_implementation`
- stdout: JSON with review text + fixup results

**`wf close <workflow>`**
- Reads model.close and agent.profile from `workflow.config`. CLI `--model` overrides.
- **Cleans up session artifacts:** deletes `docs/workflows/.sessions/<workflow>/` directory. This removes all `results.json` crash recovery files (no longer needed — results are in the record) and any preserved `.jsonl` session files from failed tasks. Session files for failed tasks that haven't been investigated are logged to stderr before deletion (`"Removing preserved session for task-2: docs/workflows/.sessions/.../task-2.jsonl"`) so the user is aware.
- Commits any uncommitted changes:
  1. Commits `docs/workflows/` files via `commit_or_amend_workflow_files` (the record; session artifacts are already deleted)
  2. Commits remaining uncommitted changes with `[workflow-close] <name>: final changes`
- Merges workflow worktree back to source branch (rebase + ff)
- On clean merge: cleans up worktree and branch, writes close data to record
- On conflict: spawns a conflict resolution agent in a tmux pane (or headless if `--no-tmux`):
  1. Agent receives the conflict context: which files conflict, diff stat, conflict markers
  2. Agent uses `prompts/merge-resolver.md` as system prompt (resolve both sides' intent, `git add` each file, verify no markers remain, do NOT commit)
  3. After the agent exits, `wf close` checks for remaining unmerged files (`git diff --name-only --diff-filter=U`)
  4. If all resolved: creates the merge commit, cleans up worktree, writes close data
  5. If conflicts remain: reports which files still have conflicts, preserves worktree for manual resolution, sets `workflow.status` to `failed`
- If `workflow.worktree` is null (bare mode / `--no-worktree`): skip worktree merge. Commit final record state, set status to `done`.
- Writes close data to record
- Cleans up worktree + branch on success
- stdout: JSON `{"mergeResult": "clean", "finalCommit": "...", "diffStat": "..."}`

**`wf status <workflow>`**
- Loads record, renders current state
- stdout: formatted status text

**`wf list`**
- Scans `docs/workflows/` for record files
- Shows name, status, task progress, cost for each
- stdout: formatted table

**`wf history`**
- Like `wf list` but includes completed workflows
- `--json` for raw JSON array
- stdout: formatted table or JSON

**`wf render <workflow>`**
- Generates full human-readable markdown from the record
- stdout: markdown text

**`wf validate <file>`**
- Validates a plan JSON file against schema + deps + cycles
- stdout: "Valid" or error details

**`wf brief <workflow> <task-id>`**
- Generates the task brief from the record's plan and results
- stdout: the brief text (raw markdown)

**`wf recover <workflow>`**
- **Explicit cleanup without re-execution.** This command performs the same recovery logic that `wf execute` runs automatically on resume (see Crash recovery flow below), but does NOT proceed to execute any tasks. Use it when you want to inspect and clean up crash artifacts without triggering a new execution run, or when you need to recover a workflow that's stuck in a bad state before deciding what to do next.
- Loads record, inspects for crash artifacts
- Finds tasks stuck in `running` status
- Checks `docs/workflows/.sessions/<workflow>/` for orphaned results files — if found, incorporates them into the record
- Reads `activeResources` to locate orphaned worktrees
- Cleans up orphaned worktrees and branches
- Resets interrupted tasks to `pending`
- Appends `crashRecovery` events to the timeline
- stdout: JSON summary of what was cleaned up and reset
- **Relationship to `wf execute`:** `wf execute` runs this same recovery logic automatically before resuming DAG scheduling. `wf recover` exists for manual inspection/cleanup when you don't want to immediately re-execute, or when you want to verify the recovery results before proceeding. Running `wf recover` followed by `wf execute` is equivalent to running `wf execute` alone (execute's auto-recovery is idempotent — if nothing needs recovering, it proceeds directly to scheduling).

**`wf schema [--component NAME]`**
- No args: outputs the full `workflow.schema.json`
- `--component plan`: outputs just `$defs/Plan` as a standalone schema (refs inlined)
- `--component brainstorm`: outputs just `$defs/Brainstorm`
- `--component task`, `--component usage`, etc. for any `$def`
- Used by harness wrappers to get tool input schemas without parsing `$ref` themselves
- stdout: JSON Schema

**`wf config list [--cwd DIR] [--show-origin]`**
- Shows the fully-resolved configuration (all levels merged)
- `--show-origin`: annotate each value with its source level (baked-in, user, project)
- If run inside a workflow directory, also shows the workflow's snapshotted config
- stdout: formatted config display

**`wf config get <key> [--cwd DIR]`**
- Shows a single resolved value. Supports dotted keys: `model.plan`, `execute.concurrency`
- stdout: the value + its source level

**`wf config set <key>=<value> [--user|--project] [--cwd DIR]`**
- Sets a value in the specified config file
- `--user`: write to `~/.config/wf/config.toml` (default)
- `--project`: write to `.wf/config.toml`
- Creates the file if it doesn't exist
- Preserves existing comments and formatting
- stdout: confirmation message

### Exit Codes

- 0: success
- 1: execution failure / validation error — stdout is `{"error": "<message>"}` JSON
- 2: bad arguments / missing workflow — stderr has argparse-style usage text

### State Contract

All state changes go through the record file at `docs/workflows/<name>.json`. The CLI reads and writes this file. Harness wrappers poll this file for progress updates. No other state files exist.

Configuration files (`~/.config/wf/config.toml`, `.wf/config.toml`) are read-only inputs to `wf init` - they are never read after the workflow is created. The resolved config snapshot in the record is the single source of truth for all workflow settings.

### Record File and Git Worktrees

The record file lives in `docs/workflows/<name>.json`. Its location follows the worktree lifecycle:

- **At init time:** written to the main repo, then committed (the `[workflow-init]` commit). If a workflow worktree is created, it branches from this commit, so the record exists in the worktree from the start.
- **During the workflow:** all commands operate in the worktree (if one exists) or the main repo (bare mode). The record is read and written there. The worktree is the canonical location.
- **At close time:** `wf close` merges the worktree (including the record) back to the source branch. After close, the record lives in the main repo on the source branch.

During execution specifically:

1. **Single writer** - only the scheduler process reads/writes the record. Subagents never touch it.
2. **Pre-execution commit** - the record is committed before task worktrees branch, so all worktrees start from the same snapshot.
3. **Uncommitted updates** - during execution, the scheduler writes record updates to disk without committing. These are safe because task branch merges only touch project files, not the record.
4. **Exclusion safeguard** - `commit_if_dirty` in task worktrees uses `git add -A -- ':!docs/workflows/'` to ensure stale record copies never get committed to task branches, even if a subagent accidentally touches the file.
5. **Final commit** - after execution completes, the scheduler commits the final record state.

Parallel workflows use separate record files (`auth-refactor.json`, `perf-fix.json`) - no cross-workflow conflicts.

### Error Recovery and Investigation

Every failure should leave enough context in the record for an investigating agent to understand what happened, why, and what to do about it - without needing external files or tribal knowledge.

**Principles:**

1. **Record-first.** The record file is written before any destructive or complex operation. Init writes the record before creating the worktree. Execution records `activeResources` before spawning subagents. If anything crashes, the record exists and explains the intent.

2. **No truncation.** Error fields capture full output - rebase stderr, conflict details, merge output. The record file can handle a few KB of error text. Truncating errors forces the investigating agent to guess.

3. **Preserve results before cleanup.** The wrapper script produces `results.json` (via the adapter) *before* writing the exit-code file. This means results exist on disk before the runner is even notified of completion. The runner's first act is to copy `results.json` to `docs/workflows/.sessions/<workflow>/<task-id>.results.json` - a durable location outside the tmpdir. Only then does it proceed to update the record and clean up the tmpdir. If the scheduler crashes between "agent done" and "record updated," crash recovery can find the orphaned results file and incorporate it.

   On task failure, the raw session file is also copied to `docs/workflows/.sessions/<workflow>/<task-id>.jsonl` for full conversation investigation. On success, only `results.json` is preserved as a recovery safety net - it's small (summary, usage, notes) and gets cleaned up by `wf close`.

4. **Capture the brief.** Each `TaskResult` includes the full `brief` that was sent to the subagent. An investigating agent can read exactly what the subagent was told to do, without needing to understand brief assembly logic or have the `wf` tool available.

5. **Track resources for crash cleanup.** `implementation.activeResources` maps task IDs to worktree paths for all live worktrees. Updated on create, cleared on cleanup. After a scheduler crash, `wf execute` reads this to clean up orphaned worktrees before resuming. This also helps `wf list` report orphaned resources.

6. **Operational timeline.** `implementation.events` is a lightweight log of major operations - task starts, completions, merge attempts, merge failures, merge conflict resolution attempts (mergeResolveStart/Complete/Failed), worktree cleanups, dependency skips. Not every debug line, but enough to reconstruct the sequence of events. An investigating agent reading the record can see: "task-1 merged at T=11:18, task-2 started merge at T=11:19, conflict in src/auth.ts, resolution agent spawned at T=11:20, resolution succeeded at T=11:21" without cross-referencing a separate debug log.

**Session file preservation:**

```
docs/workflows/
├── auth-refactor.json              # the record
└── .sessions/
    └── auth-refactor/
        ├── task-1.results.json      # preserved - crash recovery safety net
        ├── task-2.results.json      # preserved - crash recovery safety net
        ├── task-2.jsonl             # preserved - task-2 failed, full conversation
        └── auto-review-1.jsonl     # preserved - review agent failed
```

`results.json` files are small (summary, notes, usage - a few KB) and serve as a crash recovery safety net. They are written for every completed task, durable outside the tmpdir. If the scheduler crashes after the agent finishes but before the record is updated, `wf recover` finds these files, incorporates them into the record, and cleans them up.

Session `.jsonl` files contain the full agent conversation: every tool call, every edit, every reasoning step. These are only preserved on task failure (they can be large). The path is recorded in `TaskResult.session_file`.

**Cleanup lifecycle for `.sessions/`:**
- `wf recover` / `wf execute` auto-recovery: incorporates orphaned `results.json` files into the record, then deletes them. Does NOT delete `.jsonl` files (they may be needed for investigation).
- `wf close`: deletes the entire `docs/workflows/.sessions/<workflow>/` directory — both `results.json` files (no longer needed, results are in the record) and `.jsonl` session files (workflow is complete). Logs a warning to stderr for each `.jsonl` file being deleted so the user is aware preserved investigation data is being removed.
- If the user wants to keep session files, they should copy them elsewhere before `wf close`.

**Crash recovery flow:**

This logic runs in two places: automatically at the start of `wf execute` (before resuming DAG scheduling), and explicitly via `wf recover` (without proceeding to execute). Both run the same steps; `wf recover` simply stops after step 6.

1. Load the record
2. Find tasks with `status: running` - these were in-flight when the scheduler crashed
3. Check `docs/workflows/.sessions/<workflow>/` for orphaned `<task-id>.results.json` files - if found, incorporate them into the record (the agent finished but the scheduler crashed before writing to the record)
4. Read `activeResources` to find orphaned worktrees, clean them up
5. Reset any still-unresolved `running` tasks to `pending`
6. Append `crashRecovery` events to the timeline
7. (`wf execute` only) Resume normal DAG scheduling

**What an investigating agent sees in the record after a failure:**

- `workflow.status` - which phase failed
- `implementation.events` - timeline showing what happened and in what order
- `implementation.tasks["task-X"].error` - full error details
- `implementation.tasks["task-X"].brief` - what the subagent was told to do
- `implementation.tasks["task-X"].sessionFile` - full agent conversation (if preserved)
- `implementation.tasks["task-X"].worktreePath` + `worktreePreserved` - where to inspect the code
- `implementation.activeResources` - any orphaned worktrees from crashes

---

## Harness Integration Contract

This section is the complete interface between `wf` and any harness wrapper. A wrapper author needs **only** what's listed here - no internal knowledge of wflib, no Python imports, no shared memory. Everything is CLI calls, file reads, and stdin pipes.

### CLI commands the wrapper calls

| Command | When | Input | Output |
|---------|------|-------|--------|
| `wf init <name> [--cwd DIR] [--no-worktree]` | User starts a workflow | flags | JSON: `{workflow_id, record_file, worktree}` |
| `wf brainstorm <workflow> [options]` | User brainstorms from CLI (standalone) | flags | JSON: `{message, status}` or `{message, warning}` |
| `wf plan <workflow> [options]` | User plans from CLI (standalone) | flags | JSON: `{message, status}` or `{message, warning}` |
| `wf record-brainstorm <workflow> [--cwd DIR]` | Agent calls `record_brainstorm` tool (write endpoint) | Brainstorm JSON on stdin | JSON: `{message, status}` |
| `wf submit-plan <workflow> [--cwd DIR]` | Agent calls `submit_plan` tool (write endpoint) | Plan JSON on stdin | JSON: `{message, status}` |
| `wf execute <workflow> [options]` | User runs implementation | flags | JSON: `{counts, duration, usageRows}` |
| `wf execute-task <workflow> <task-id> [options]` | User runs single task | flags | JSON: TaskResult |
| `wf review <workflow> [options]` | User requests review | flags | review text |
| `wf auto-review <workflow> [options]` | User requests review+fixup | flags | JSON: `{review_text, findings_actionable, fixup_counts}` |
| `wf close <workflow> [--cwd DIR]` | User closes workflow | flags | JSON: `{mergeResult, finalCommit, diffStat}` |
| `wf status <workflow> [--cwd DIR]` | UI refresh, user query | - | formatted text |
| `wf list [--cwd DIR]` | UI, user query | - | formatted table |
| `wf history [--cwd DIR] [--json]` | User query | - | formatted table or JSON |
| `wf recover <workflow> [--cwd DIR]` | After crash | - | JSON: `{cleaned_worktrees, reset_tasks}` |
| `wf schema [--component NAME]` | Tool registration (once, at extension load) | - | JSON Schema |
| `wf config list [--cwd DIR]` | Show resolved config | - | formatted text |
| `wf template list [--cwd DIR]` | Template discovery | - | formatted table |
| `wf template render <name> [args...]` | User invokes template | - | rendered text |

### Files the wrapper reads

| File | Purpose | Format |
|------|---------|--------|
| `docs/workflows/<name>.json` | Poll for UI updates during execution, restore state on session load | JSON matching `schemas/workflow.schema.json` |
| `<wf_install>/prompts/brainstorm.md` | Inject into conversation when entering brainstorm mode | markdown |
| `<wf_install>/prompts/planning-context.md` | Inject into conversation when entering plan mode | markdown |

The wrapper discovers `<wf_install>` by resolving the `wf` binary on PATH (e.g. `dirname $(readlink -f $(which wf))/..`), or via an environment variable, or a hardcoded known path. The prompts are plain markdown files - the wrapper reads them and injects them however its harness handles system prompt additions.

### Tool schemas for LLM tool registration

The wrapper registers tools that the LLM can call. For pi, these use TypeBox schemas mirroring the JSON Schema `$defs` (same approach as the subagent tool extensions). For harnesses that accept JSON Schema directly, `wf schema --component <name>` provides standalone, self-contained schemas.

- **`record_brainstorm`** - TypeBox schema mirroring `$defs/Brainstorm`. On tool call: pipe the arguments as JSON to `wf record-brainstorm <workflow>` on stdin.
- **`submit_plan`** - TypeBox schema mirroring `$defs/Plan`. On tool call: pipe to `wf submit-plan <workflow>` on stdin.

Schema consistency between TypeBox and JSON Schema is verified by a Node test (`tools/pi_extensions/schema-consistency.test.ts`).

### Active workflow selection

The wrapper must track which workflow is "active" so that tool calls (`submit_plan`, `record_brainstorm`) and commands (`/wf execute`, `/wf status`) know which `<workflow>` argument to pass to the CLI.

**Source of truth: wrapper in-memory state.** The wrapper stores the active workflow name when:
- `/wf init <name>` succeeds (the just-created workflow becomes active)
- The user explicitly targets a workflow via a command (`/wf status <name>`, `/wf execute <name>`)

**Recovery on session restore** (`session_start` / `session_switch`): the wrapper scans `docs/workflows/` for record files, filters to those with `status` not in (`done`, `failed`), and picks the most recently modified one. If exactly one active workflow exists, it becomes the active workflow automatically. If multiple exist, the wrapper sets no active workflow and requires the user to specify one explicitly.

**When no workflow is active:** tool handlers and commands that require a workflow name display an error: `"No active workflow. Run /wf init <name> or /wf status <name> to select one."`

### `--cwd` and path expectations

The wrapper passes `--cwd <path>` to all CLI calls. The path must point to the directory containing `docs/workflows/<name>.json` — which is:

- **During the workflow:** the workflow worktree path (if one exists) or the main repo (bare mode). The wrapper uses `ctx.cwd` which the harness sets to the current working directory.
- **After `wf close`:** the main repo (the worktree is gone). The wrapper detects this when `ctx.cwd` no longer exists and falls back to `workflow.project` from the record.

In practice, the wrapper's `ctx.cwd` is the correct path in nearly all cases. The edge case is when a wrapper session outlives a `wf close` that deleted the worktree — the wrapper should detect the missing directory and notify the user.

### Wrapper tool call protocol

When the LLM calls a tool (`submit_plan`, `record_brainstorm`) during an inline wrapper session (e.g. `/wf plan` in pi), the wrapper handles it as follows:

1. **Intercept the tool call.** The wrapper's registered tool handler receives the call with the LLM's arguments (a JSON object matching the schema).
2. **Pipe to CLI.** The wrapper spawns `wf submit-plan <workflow> --cwd <project>` (or `wf record-brainstorm <workflow> --cwd <project>`) as a subprocess, piping the tool arguments as JSON to stdin. `<workflow>` comes from the active workflow name (see above). `<project>` comes from `ctx.cwd`.
3. **Read CLI output.** The CLI validates, writes to the record, and returns a JSON response on stdout (`{"message": "...", "status": "...", "warnings": [...]}`).
4. **Return to LLM.** The wrapper returns the CLI's response as the tool result to the LLM. If `warnings` is non-empty, also display them as notifications.
5. **Update UI.** The wrapper re-reads the record file to refresh the status bar and widget.

The wrapper never writes to the record file directly. The `wf` CLI is the sole writer. This means validation, state transitions, and file I/O are always in one place (Python), and the wrapper is pure pass-through.

**Why not have the pi extension tools call `wf` themselves?** The pi extension tools in `tools/pi_extensions/` are loaded into *subagent* processes (implementation, review), not the main wrapper session. They are validate-and-return only — they don't write to the record because subagents don't know the workflow name or have write access to the record. The wrapper's tool handlers are different: they run in the main pi session, know the active workflow name, and pipe to the CLI.

### Subagent tool extensions

Brainstorm, planning, implementation, and review agents need tools that `wf` can extract results from. The tool implementations ship with `wf` in `tools/`, with one implementation per tool loading mechanism:

- **`tools/pi_extensions/`** - TypeScript pi extensions (`report-result-tool.ts`, `submit-plan-tool.ts`, `record-brainstorm-tool.ts`). Loaded by the pi profile via `-e <path>`. Each validates the schema and returns success.
- **`tools/mcp_server.py`** - Python MCP server exposing the same three tools. Loaded by the Claude Code profile via `--mcp-config`. Reads schemas from `wf schema --component` and validates inputs.

All implementations follow the same pattern: validate schema, return success to the agent. `wf` extracts the tool call from `results.json` messages after the session ends.

The runner profile handles tool loading automatically. When the runner calls `profile.build_headless_cmd(tools=["report-result"])`, the profile knows how its harness loads tools and constructs the right flags. For pi: `-e <wf>/tools/pi_extensions/report-result-tool.ts`. For Claude Code: `--mcp-config` pointing to the MCP server. The runner never interprets tool paths directly.

### Record file format for UI

The wrapper polls `docs/workflows/<name>.json` for live UI updates during execution. The relevant fields:

- `workflow.status` - current phase (`init`, `brainstorming`, `planning`, `implementing`, `reviewing`, `closing`, `done`, `failed`)
- `implementation.tasks.<id>.status` - per-task status (`pending`, `running`, `done`, `failed`, `skipped`)
- `implementation.tasks.<id>.usage.cost` - per-task cost for inline display
- `plan.tasks` - task list for widget rendering (id, title, dependsOn)

The wrapper treats the record as read-only JSON. It never writes to it - all mutations go through `wf` CLI commands.

### Usage capture in inline mode

When brainstorm or plan phases run inline (e.g. `/wf brainstorm` in pi), usage is tracked by the harness, not by `wf`. The wrapper accumulates usage via harness events (`message_end` in pi) and passes it to the CLI when the phase completes:

```
# After the LLM calls record_brainstorm, the wrapper pipes:
echo '{"motivation": "...", "solution": "...", "designDecisions": [...]}' \
  | wf record-brainstorm <workflow> --cwd <project> \
    --usage '{"input": 45000, "output": 8000, "cacheRead": 12000, "cacheWrite": 5000, "cost": 0.082, "turns": 4, "model": "claude-sonnet-4-5"}'
```

The `--usage` flag accepts a JSON object matching the `Usage` schema. If omitted, usage is recorded as zeros (the data simply isn't available). This is the expected path for CLI-only usage (`wf brainstorm` captures usage from the spawned agent's `results.json`; only inline wrapper mode needs this flag).

For `wf submit-plan`, same pattern:
```
echo '<plan json>' | wf submit-plan <workflow> --cwd <project> \
  --usage '{"input": 32000, "output": 6000, ...}'
```

### What the wrapper does NOT need

- No Python imports or wflib knowledge
- No understanding of worktree lifecycle, DAG scheduling, or merge strategies
- No direct git operations
- No subprocess management for subagents
- No plan validation logic (that's `wf submit-plan`'s job)
- No result extraction from agent output (that's the profile + adapter's job)

---

## What the Pi Wrapper Becomes

Thin TS extension in `~/.pi/agent/extensions/wf/`. ~300 lines. Registers commands, tools, and event hooks that delegate to `wf` CLI and read the record file.

The wrapper provides a richer UX for brainstorm and plan phases than the standalone CLI: inline mode toggles within the current conversation, per-turn usage tracking, write-tool blocking during planning, and context compaction. These are **convenience features on top of what `wf brainstorm` and `wf plan` accomplish standalone** - both paths write to the same record file via the same `wf record-brainstorm` / `wf submit-plan` logic.

```
~/.pi/agent/extensions/wf/
├── index.ts                      # Commands, tools, events, UI
└── README.md
```

The subagent tool extensions (`report-result-tool.ts`, `submit-plan-tool.ts`, `record-brainstorm-tool.ts`) now live in the `wf` repo at `tools/pi_extensions/`, not in the pi wrapper. The pi runner profile knows their paths and loads them via `-e`. This means the pi wrapper is **pure UI glue** - it has no artifacts that the runner depends on.

### Responsibilities

**Tools (registered for LLM use):**

1. **`record_brainstorm`** - register tool with TypeBox schema mirroring `$defs/Brainstorm`. On call: pipe JSON to `wf record-brainstorm <workflow>`, update UI.

2. **`submit_plan`** - register tool with TypeBox schema mirroring `$defs/Plan`. On call: pipe JSON to `wf submit-plan <workflow>`, update UI, exit plan mode.

**Commands (registered for user):**

3. **`/wf init <name> [--set KEY=VALUE ...]`** - call `wf init <name>` with any `--set` overrides. Config resolution (baked-in < user < project < overrides) happens inside `wf init`. Open tmux window in worktree with interactive pi session.

4. **`/wf run [options]`** - call `wf run`, poll record file for UI updates across all phases. Unified entry point - same as the standalone CLI but with live status bar, widget, and notification integration. All settings come from the config snapshot in the record; CLI flags are ephemeral overrides. **`wf run` always spawns new tmux sessions for interactive phases** (brainstorm, plan) — it does not use the inline `/wf brainstorm` / `/wf plan` convenience modes. Inline modes are a separate entry point for users who want to brainstorm/plan within their current conversation.

6. **`/wf brainstorm`** - convenience mode: inject `prompts/brainstorm.md` context into the current session, enable `record_brainstorm` tool. Agent converses with user inline, calls tool when conclusions reached. Provides per-turn usage tracking. (Standalone equivalent: `wf brainstorm` spawns a dedicated agent session.)

7. **`/wf plan`** - convenience mode: toggle planning mode in the current session. Inject `prompts/planning-context.md`, enable `submit_plan` tool, block write tools. Provides per-turn usage tracking. (Standalone equivalent: `wf plan` spawns a dedicated agent session.)

8. **`/wf plan compact`** - compact brainstorm context first, then enter planning mode. Pi-specific: uses the harness's context compaction API, not available from the standalone CLI.

9. **`/wf execute [options]`** - parse flags, call `wf execute`, poll record file for UI updates (task status widget, footer progress).

10. **`/wf execute <task-id>`** - call `wf execute-task`.

11. **`/wf review [options]`** - call `wf review` or `wf auto-review`.

12. **`/wf close`** - call `wf close`.

13. **`/wf status`** - call `wf status`, display result.

14. **`/wf list`** - call `wf list`, display result.

15. **`/wf history`** - call `wf history`, display result.

**Event hooks (pi-specific integration):**

16. **`before_agent_start`** - inject phase-appropriate context when in brainstorm or plan mode.

17. **`tool_call`** - in plan mode: block `edit`, `write`, and destructive bash commands. Returns `{ block: true, reason: "..." }`. This is the mechanical enforcement that backs up the prompt instruction. Not available from the standalone CLI.

18. **`message_end`** - track token usage during brainstorm and plan phases. Accumulate per-turn, pass to `wf record-brainstorm` / `wf submit-plan` via `--usage` when the phase completes.

19. **`session_start` / `session_switch`** - restore active workflow state from record file for UI. On restore, scans `docs/workflows/` for active records (status not `done`/`failed`). If exactly one active workflow exists, it becomes the active workflow automatically. If multiple exist, no workflow is selected (user must specify one explicitly). On `/new`, clears the active workflow.

**UI:**

19. **Status bar** - current workflow phase and progress (e.g. `⚡ 3/5 implementing`).

20. **Widget** - per-task status list with icons and costs.

21. **Autocompletions** - workflow names (from `docs/workflows/`), task IDs, model IDs, flags.

22. **Keyboard shortcut** - `Ctrl+Alt+W` toggle plan mode.

**What the wrapper does NOT do:**

- No DAG scheduling logic
- No git/worktree operations
- No subprocess spawning
- No plan validation or brief assembly
- No state file format knowledge beyond reading JSON for UI display

---

## `wf help` - Agent-Friendly Reference System

### Why a Help Subcommand

The primary consumer of `wf help` is not a human - it's an AI agent that needs to understand the tool in order to use it, debug failures, or investigate stuck workflows. The help system is designed for that use case:

1. **Single-call completeness.** `wf help` (no topic) dumps the entire reference - every subcommand, every flag, every concept, every error message, debugging guides, record file anatomy, recovery procedures. ~1200 lines. An agent calls it once and has everything it needs in context. No multi-step discovery ("list topics" → "query each one").

2. **Authoritative.** The help text is the canonical documentation for `wf`. It is more detailed than `--help` flags on individual subcommands (which use argparse's terse format). When in doubt about behavior, `wf help` is the source of truth.

3. **Actionable for debugging.** Each subcommand topic includes: every possible error message with its cause and fix, troubleshooting for common failure patterns, and concrete investigation commands ("run this to see what the agent was told", "check this field in the record"). The `debugging` topic is a step-by-step guide with copy-pasteable shell commands for inspecting workflows, tasks, execution timelines, and worktrees.

4. **Structured for search.** Consistent formatting across all topics: OPTIONS, STDOUT, EXIT CODES, ERRORS, TROUBLESHOOTING, EXAMPLES. An agent can pattern-match to find what it needs.

5. **Self-contained.** No references to external docs, no "see the README", no links. Everything an agent needs is in the output.

### Design

`wf help` lives in `wflib/help.py`. Each topic is a function returning a string. The topic registry controls ordering and lookup.

```
wf help                    Full reference dump (all topics, ~1200 lines)
wf help topics             List available topics (quick orientation)
wf help <topic>            Specific topic
wf help <prefix>           Prefix match (wf help exec → execute)
wf                         Alias for wf help topics
```

Topics cover three categories:

| Category | Topics |
|----------|--------|
| Subcommands | init, run, brainstorm, plan, record-brainstorm, submit-plan, execute, execute-task, review, close, status, list, render, validate, brief, recover, schema, config, templates |
| Concepts | overview, lifecycle, subcommands (quick ref), record (file anatomy), config (precedence chain, snapshotting, file locations), models (resolution precedence), worktrees (isolation), exit-codes |
| Operations | recovery (crash cleanup procedures), debugging (investigation guide with concrete commands and common scenarios), harness (integration contract) |

Each subcommand topic follows this structure:

```
wf <command> <args> [options]

    Description of what the command does.

    OPTIONS:
      --flag VALUE          Description (default: X)

    BEHAVIOR / STEPS:
      What the command actually does, in order.

    STDOUT:
      Exact output format (JSON shape or text description).

    EXIT CODES:
      Command-specific exit code meanings.

    EXAMPLES:
      Concrete invocations.

    ERRORS:
      "Exact error message"
          Cause and fix.

    TROUBLESHOOTING:
      Common failure patterns and investigation steps.
```

### What Makes It Agent-Friendly

The help output is optimized for how agents actually use reference material:

- **Error messages are quoted exactly** so the agent can match them against stderr output. Each error includes the cause and a specific remediation.

- **The `debugging` topic** includes copy-pasteable investigation commands: how to extract a specific task's error from the record JSON, how to view the events timeline, how to inspect what brief was sent to a subagent, how to find orphaned worktrees. These are the commands an agent would need to run when investigating a failure.

- **The `record` topic** lists every field an agent might need to inspect, with paths (`implementation.tasks.<id>.error`, `implementation.events`, etc.) and what each contains. This is the "where do I look" reference.

- **No progressive disclosure.** Agents don't benefit from hiding information behind layers. The full dump is the default because that's what an agent should call.

- **Prefix matching** (`wf help exec` → `execute`) reduces the chance of a failed lookup when an agent constructs a help query from memory.

### Implementation

```python
# wflib/help.py - ~800 lines, pure functions, no I/O beyond print()

TOPICS: list[tuple[str, str, callable]]   # (name, title, content_fn)
TOPIC_MAP: dict[str, tuple[str, callable]] # name → (title, content_fn)

def get_help(topic: str | None = None) -> str
    """Return help text. topic=None → full dump. Never raises."""

def help_command(args: list[str]) -> None
    """CLI entry point. Prints to stdout."""
```

The module has zero I/O dependencies - it returns strings. The CLI entry point calls `print()`. This makes it trivially testable: `assert "--concurrency" in get_help("execute")`.

---

## Complete CLI Reference

```
wf - structured AI development workflows

LIFECYCLE COMMANDS

  wf init <name> [--cwd DIR] [--no-worktree] [--set KEY=VALUE ...]

      Start a new workflow. Requires a git repository.

      Resolves the full configuration by merging:
      baked-in defaults < user config < project config < --set overrides.
      Snapshots the resolved config into the record. Creates the record
      file, commits it, optionally creates a workflow worktree.

      Sequence: write record → commit → create worktree (if enabled).
      The commit ensures the worktree branches from a state that
      includes the record file. All subsequent commands operate in
      the worktree (if created) or the main repo (bare mode).

      --cwd DIR               Project directory (default: .)
      --no-worktree           Work directly in the main repo instead of a worktree
      --set KEY=VALUE         Override config for this workflow (repeatable).
                              Uses dotted keys matching the config file structure:
                              --set model.plan=claude-opus-4
                              --set automation.implement=automatic
                              --set execute.concurrency=8
                              --set ui.auto-close=60
                              --set agent.profile=claude-code

      Config resolution:
        1. Baked-in defaults (hardcoded in wf)
        2. User config (~/.config/wf/config.toml)
        3. Project config (.wf/config.toml)
        4. --set overrides (highest precedence at init time)

      The resolved config is stored in workflow.config in the record.
      All subsequent commands read from this snapshot. Config files are
      never re-read after init.

      stdout: {"workflowId": "...", "recordFile": "...", "worktree": "..."}

  wf run <workflow> [options]

      Walk through the full workflow lifecycle: brainstorm → plan →
      execute → review → close. Reads workflow.status to determine
      the current phase and picks up from there.

      This is the primary way to use wf. One command walks you through
      the entire process, pausing for interactive phases (opening tmux
      sessions you drive), running autonomous phases automatically, and
      resuming from where you left off if anything fails or you ctrl-c.

      All settings (models, automation, concurrency, tmux, auto-close,
      runner profile) come from the config snapshot in the record
      (workflow.config), set at init time. CLI flags override for this
      invocation only - they do not modify the record.

      The automation level per phase (from config.automation) controls
      the behavior:

        interactive   Open a tmux session. You drive the conversation.
                      wf run blocks until the session ends, then
                      extracts the result and advances to the next phase.
        supervised    Open tmux panes. Agent runs autonomously but you
                      can watch and intervene. wf run blocks until done.
        automatic     Run headless. No tmux. wf run shows progress
                      inline and advances when done.

      Defaults (if no --set automation.* was passed to wf init):
        brainstorm=interactive, plan=interactive,
        implement=supervised, review=automatic, close=automatic

      Phase behavior:

        [brainstorm]  Runs wf brainstorm. --prompt is passed as the
                      initial problem description. If the agent doesn't
                      call record_brainstorm, wf run stops and reports.
        [plan]        Runs wf plan. Brainstorm context from the record
                      is included automatically. --prompt is appended
                      as additional guidance. If the agent doesn't call
                      submit_plan, wf run stops and reports.
        [execute]     Runs wf execute. Includes auto-review if
                      config.execute.autoReview is true (default).
                      Task progress is shown inline. On task failures,
                      wf run stops.
        [review]      Handled by --auto-review within the execute phase.
                      If review finds fixup issues, fixup tasks run
                      automatically.
        [close]       Runs wf close. On merge conflict, spawns a
                      resolution agent. Reports final diff stat.

      Resume: run the same command again after fixing a failure.
      wf run reads workflow.status and starts from the current phase.
      No skip flags needed - if you want to skip brainstorm, run
      wf submit-plan manually to advance the status, then wf run
      picks up from execute.

      --cwd DIR               Working directory (default: .)
      --model MODEL           Override model for all phases (ephemeral)
      --prompt TEXT            Problem description (brainstorm) / guidance (plan)
      --concurrency N         Override max parallel tasks (ephemeral)
      --no-worktrees          Override worktree isolation (ephemeral)
      --no-tmux               Override tmux usage (ephemeral)
      --auto-close [SECONDS]  Override auto-close delay (ephemeral)

      All flags except --cwd and --prompt are ephemeral overrides -
      they apply to this invocation only and do not change the
      config snapshot in the record.

      stdout (unified progress):

        [brainstorm] interactive - opening tmux session...
        [brainstorm] ✓ recorded - 3 design decisions ($0.082)
        [plan] interactive - opening tmux session...
        [plan] ✓ submitted - 5 tasks ($0.055)
        [execute] supervised - 5 tasks, concurrency 4
          ✓ task-1 Extract token module         $0.045
          ✓ task-2 Session module               $0.038
          ✓ task-3 Middleware integration        $0.052
          ✓ task-4 Update tests                 $0.041
          ✓ task-5 Documentation                $0.022
        [execute] ✓ 5/5 done ($0.198)
        [review] automatic - running auto-review...
        [review] ✓ no actionable issues ($0.038)
        [close] automatic - merging to main...
        [close] ✓ clean merge - 12 files changed

        ✓ auth-refactor complete. $0.373 total.

      Fully automatic example:
        wf init auth-refactor \
            --set automation.brainstorm=automatic \
            --set automation.plan=automatic \
            --set automation.implement=automatic
        wf run auth-refactor --prompt "Split auth module into token, session, middleware"

      Or, if your user config already has all automation=automatic:
        wf init auth-refactor
        wf run auth-refactor --prompt "Split auth module into token, session, middleware"

  wf brainstorm <workflow> [options]

      Spawn a brainstorm agent session. The agent converses about the
      problem space and calls record_brainstorm when design conclusions
      are reached. After the session ends, the tool call is extracted
      from the agent's messages and recorded in the workflow.

      In tmux mode (default): opens an interactive session - the user
      drives the conversation, challenges assumptions, steers toward
      conclusions. This is the expected mode for brainstorming.

      In headless mode: the agent brainstorms autonomously from the
      provided --prompt. Less useful - brainstorming benefits from
      human pushback - but available for automated pipelines.

      --cwd DIR               Working directory (default: .)
      --model MODEL           Override model (ephemeral; default from config.model.brainstorm)
      --prompt TEXT            Initial message / problem description
                              (required for --no-tmux, optional for tmux)
      --no-tmux               Override tmux usage (ephemeral; default from config.ui.tmux)
      --auto-close [SECONDS]  Override auto-close (ephemeral; default from config.ui.autoClose)

      Runner profile, model, tmux, and auto-close default to the
      config snapshot in the record. CLI flags override for this
      invocation only.

      The agent is spawned with:
        - System prompt: prompts/brainstorm.md
        - Tool: record-brainstorm-tool (schema from $defs/Brainstorm)
        - Initial message: --prompt text (if provided)

      After the session:
        1. Read results.json
        2. Extract last record_brainstorm tool call from messages
        3. If found: validate, write to record, set status to 'planning'
        4. If not found: warn, record stays in current state
        5. Record usage from the session

      stdout: {"message": "...", "status": "planning"} or
              {"message": "...", "warning": "record_brainstorm not called"}

  wf plan <workflow> [options]

      Spawn a planning agent session. The agent explores the codebase
      and calls submit_plan with a structured implementation plan. After
      the session ends, the plan is extracted, validated, and recorded.

      In tmux mode (default): opens an interactive session - the user
      can guide exploration, answer questions, reject drafts. The agent
      calls submit_plan when the plan is ready.

      In headless mode: the agent plans autonomously using brainstorm
      context from the record. Useful when brainstorm was thorough and
      the codebase is well-structured enough for autonomous planning.

      --cwd DIR               Working directory (default: .)
      --model MODEL           Override model (ephemeral; default from config.model.plan)
      --prompt TEXT            Additional guidance (appended to brainstorm context)
      --no-tmux               Override tmux usage (ephemeral; default from config.ui.tmux)
      --auto-close [SECONDS]  Override auto-close (ephemeral; default from config.ui.autoClose)

      Runner profile, model, tmux, and auto-close default to the
      config snapshot in the record. CLI flags override for this
      invocation only.

      The agent is spawned with:
        - System prompt: prompts/planning-context.md
        - Tool: submit-plan-tool (schema from $defs/Plan)
        - Initial message: brainstorm context from record (if exists)
          + --prompt text (if provided)
        - Read-only enforcement is prompt-only: the system prompt
          instructs "Do NOT make file changes" but the agent has its
          full tool set. Harness wrappers can add mechanical enforcement
          (pi blocks edit/write/destructive bash via tool_call hook).
          Standalone users should be aware that compliance depends on
          the prompt. If the agent modifies files, wf execute will warn
          about dirty working tree before proceeding.

      After the session:
        1. Read results.json
        2. Extract last submit_plan tool call from messages
        3. If found: validate plan (deps + cycles), write to record,
           initialize task statuses, set status to 'implementing'
        4. If not found: warn, record stays in current state
        5. Record usage from the session

      stdout: {"message": "Plan submitted with N tasks", "status": "implementing"} or
              {"message": "...", "warning": "submit_plan not called"}

  wf record-brainstorm <workflow> [--cwd DIR]

      Record brainstorm conclusions (write endpoint). Reads JSON from
      stdin matching $defs/Brainstorm schema (motivation, solution,
      design_decisions). Sets workflow status to 'planning'.

      Used by: harness wrapper tool handlers, wf brainstorm internally,
      manual piping (cat brainstorm.json | wf record-brainstorm myworkflow).

      stdin:  Brainstorm JSON
      stdout: {"message": "...", "status": "planning"}

  wf submit-plan <workflow> [--cwd DIR]

      Submit an implementation plan (write endpoint). Reads JSON from
      stdin matching $defs/Plan schema. Validates deps, cycles, and
      heuristic warnings. Initializes all task statuses to 'pending'.
      Sets workflow status to 'implementing'.

      Re-submission policy:
        status=init/planning:       Accept, replace plan.
        status=implementing,        Accept, replace plan.
          all tasks pending:
        status=implementing,        Accept with warning (prior results
          some tasks done/failed:     discarded). Warning in response.
        status=reviewing/closing/   Reject with error.
          done:

      Heuristic warnings (empty acceptance, high constraint count,
      etc.) are included in the response JSON and printed to stderr.
      They do not block submission.

      Used by: harness wrapper tool handlers, wf plan internally,
      manual piping (cat plan.json | wf submit-plan myworkflow).

      stdin:  Plan JSON
      stdout: {"message": "...", "status": "implementing", "warnings": [...]}

  wf execute <workflow> [options]

      Execute all pending tasks via DAG scheduling. On merge conflicts
      during task merge-back, automatically spawns a conflict resolution
      agent (prompts/merge-resolver.md) before marking the task as failed.

      All settings default to the config snapshot in the record.
      CLI flags override for this invocation only (ephemeral).

      --cwd DIR               Working directory (default: .)
      --profile NAME          Override runner profile (ephemeral)
      --model MODEL           Override model for all tasks (ephemeral)
      --concurrency N         Override max parallel tasks (ephemeral)
      --no-worktrees          Override worktree isolation (ephemeral)
      --no-tmux               Override tmux usage (ephemeral)
      --auto-close [SECONDS]  Override auto-close delay (ephemeral)
      --auto-review           Override auto-review setting (ephemeral)
      --review-model MODEL    Override model for review subagent (ephemeral)

      stdout: {"counts": {"done": N, "failed": N, "skipped": N}, "duration": N, "usageRows": [...]}

  wf execute-task <workflow> <task-id> [options]

      Execute or re-run a single task. Settings from config snapshot;
      CLI flags override for this invocation only.

      --cwd DIR               Working directory (default: .)
      --model MODEL           Override model for this task (ephemeral)
      --no-tmux               Override tmux usage (ephemeral)
      --auto-close [SECONDS]  Override auto-close delay (ephemeral)

      stdout: TaskResult JSON

  wf review <workflow> [options]

      Spawn a code review subagent. Appends a ReviewRecord to reviews[].
      Settings from config snapshot; CLI flags override for this invocation.

      --cwd DIR
      --model MODEL           Override model for review (ephemeral)
      --ref COMMIT            Base commit to diff against (default: from record)
      --desc DESCRIPTION      Description of work being reviewed
      --scope FILES           Focus scope (file paths or patterns)
      --no-tmux               Override tmux usage (ephemeral)
      --auto-close [SECONDS]  Override auto-close delay (ephemeral)

      stdout: review text

  wf auto-review <workflow> [options]

      Code review that produces a fixup plan if issues found.
      Same options as wf review, plus execution options for the fixup.
      Settings from config snapshot; CLI flags override.

      --cwd DIR
      --model MODEL           Override model for review (ephemeral)
      --ref COMMIT
      --no-tmux               Override tmux usage (ephemeral)
      --auto-close [SECONDS]  Override auto-close delay (ephemeral)
      --fixup-model MODEL     Override model for fixup tasks (ephemeral).
                              Precedence: --fixup-model > config.model.fixup
                              > fixup_task.model > fixup_plan.defaultModel
                              > config.model.implement > None
      --fixup-concurrency N   Override max parallel fixup tasks (ephemeral)

      stdout: {"reviewText": "...", "findingsActionable": bool, "fixupCounts": {...} | null}

  wf close <workflow> [--cwd DIR] [--model MODEL]

      Close the workflow. Cleans up session artifacts, commits changes,
      merges worktree back to source branch, cleans up worktree.
      On conflict, spawns a resolution agent.
      Settings from config snapshot; --model overrides for this invocation.

      First deletes docs/workflows/.sessions/<workflow>/ (results.json
      crash recovery files + preserved .jsonl session files). Logs a
      warning for each .jsonl being deleted. Then commits and merges.

      --cwd DIR
      --model MODEL           Override model for conflict resolution (ephemeral)

      stdout: {"mergeResult": "clean"|"conflicted"|"failed", "finalCommit": "...", "diffStat": "..."}

QUERY COMMANDS

  wf status <workflow> [--cwd DIR] [--json]

      Show current workflow state: phase, task progress, usage totals.

      --json                  Output raw record JSON instead of formatted text

      stdout: formatted status text (or JSON with --json)

  wf list [--cwd DIR] [--all] [--json]

      List workflows in this project.

      --all                   Include completed/failed workflows (default: active only)
      --json                  Output raw JSON array

      stdout: formatted table

  wf history [--cwd DIR] [--json] [--limit N]

      Show all workflows including completed. Alias for wf list --all.

      --json                  Output raw JSON array
      --limit N               Max entries (default: 20)

      stdout: formatted table or JSON

  wf render <workflow> [--cwd DIR]

      Generate human-readable markdown from the record.

      stdout: markdown text

UTILITY COMMANDS

  wf validate <file>

      Validate a plan JSON file against schema + dependency refs + cycles.

      stdout: "Valid" or error details

  wf brief <workflow> <task-id> [--cwd DIR]

      Generate the task brief from the record's plan and completed results.

      stdout: brief text (raw markdown)

  wf recover <workflow> [--cwd DIR]

      Clean up after a crash without re-executing. Finds tasks stuck in
      'running', incorporates orphaned results.json files, cleans up
      orphaned worktrees from activeResources, resets tasks to 'pending'.

      This is the same recovery logic that wf execute runs automatically
      on resume. Use wf recover when you want to inspect/clean up without
      immediately re-executing, or to verify the state before proceeding.

      stdout: {"cleanedWorktrees": [...], "resetTasks": [...], "incorporatedResults": [...]}

  wf schema [--component NAME]

      Output JSON Schema.

      (no args)               Full workflow record schema
      --component plan        Just $defs/Plan (standalone, $refs inlined)
      --component brainstorm  Just $defs/Brainstorm
      --component task        Just $defs/Task
      --component report-result Just $defs/ReportResult
      --component usage       Just $defs/Usage

      stdout: JSON Schema

CONFIG COMMANDS

  wf config list [--cwd DIR] [--show-origin]

      Show the fully-resolved configuration (all levels merged).

      Without --show-origin: shows the merged result as a TOML-like display.
      With --show-origin: annotates each value with where it came from:
        model.plan = claude-sonnet-4-5    (project: .wf/config.toml)
        model.implement = claude-sonnet-4-5  (user: ~/.config/wf/config.toml)
        execute.concurrency = 4           (default)
        automation.brainstorm = interactive (default)

      If run inside a directory with an active workflow, also shows
      the workflow's snapshotted config for comparison.

      stdout: formatted config display

  wf config get <key> [--cwd DIR]

      Show a single resolved value. Supports dotted keys:
        wf config get model.plan
        wf config get execute.concurrency
        wf config get automation.implement

      stdout: value and its source level

  wf config set <key>=<value> [--user|--project] [--cwd DIR]

      Set a value in a config file.

      --user                  Write to ~/.config/wf/config.toml (default)
      --project               Write to .wf/config.toml

      Creates the config file and parent directories if they don't exist.
      Preserves existing comments and formatting in the file.

      Keys use dotted notation matching the config file structure:
        wf config set model.plan=claude-opus-4 --user
        wf config set execute.concurrency=8 --project
        wf config set automation.implement=automatic --project
        wf config set agent.profile=claude-code --user

      stdout: confirmation message

TEMPLATE COMMANDS

  wf template list [--cwd DIR]

      List available templates (shipped defaults + project-level).
      Project-level overrides are marked. Shows name and description.

      Templates are discovered from:
        1. docs/workflows/templates/ in the project (project-level)
        2. <wf_install>/templates/ (shipped defaults)
      Project-level files with the same name override shipped defaults.

      stdout: formatted table (name, description, source)

  wf template show <name> [--cwd DIR]

      Show a template's full content including frontmatter.

      stdout: raw template markdown

  wf template render <name> [args...] [--cwd DIR]

      Render a template with argument substitution.

      $1, $2, ... replaced by positional args.
      $@ replaced by all args joined with spaces.
      Frontmatter is stripped from output.

      stdout: rendered text

HELP COMMANDS

  wf help

      Print the full reference - every subcommand, every flag, every concept,
      every error message, plus debugging and investigation guides. ~1200 lines.
      Designed for agent consumption: one call, complete information.

      An agent's first interaction with wf should be `wf help`. The output is
      self-contained and authoritative - no need to discover topics first.

      stdout: full reference text

  wf help topics

      List available help topics. Quick orientation for humans.

      stdout: topic list with descriptions

  wf help <topic>

      Show help for a specific topic. Supports prefix matching:
      `wf help exec` resolves to `wf help execute`.

      Topics cover: every subcommand (init, run, brainstorm, plan, execute,
      execute-task, review, close, status, list, render, validate, brief,
      recover, schema, templates, record-brainstorm, submit-plan), plus
      concept topics (lifecycle, record, models, worktrees, recovery,
      exit-codes, debugging, harness).

      Each subcommand topic includes: all options with types and defaults,
      stdin/stdout formats, exit codes, effects on record state, concrete
      examples, every possible error message with causes and fixes, and
      troubleshooting for common failure patterns.

      stdout: topic help text

  wf (no arguments)

      Alias for `wf help topics` - quick orientation, not the full dump.

COMPLETION COMMANDS

  wf completions bash

      Print a bash completion script. Source it to enable tab completion:

        eval "$(wf completions bash)"    # add to ~/.bashrc

      Completes: subcommands, flags per subcommand, workflow names,
      task IDs, template names, help topics, schema component names.
      Does NOT complete model IDs (harness-specific - use the pi
      wrapper for model completions).

      Dynamic completions call `wf --complete <words>` internally.
      Latency: ~50-70ms per tab press (Python startup + filesystem scan).

      stdout: bash completion script

  wf completions zsh

      Print a zsh completion script with descriptions.

        eval "$(wf completions zsh)"     # add to ~/.zshrc
        # or:
        wf completions zsh > ~/.zfunc/_wf && fpath+=(~/.zfunc)

      stdout: zsh completion script

  wf completions fish

      Print a fish completion script.

        wf completions fish > ~/.config/fish/completions/wf.fish

      stdout: fish completion script

  wf --complete <words...>

      Internal. Called by the generated shell scripts for dynamic
      completions. Not for direct use. Outputs one completion per line.

EXIT CODES

  0  Success
  1  Execution failure / validation error.
     stdout: {"error": "<message>"} JSON. Parseable by wrappers.
  2  Bad arguments / missing workflow.
     stderr: argparse-style usage text.

GLOBAL BEHAVIOR

  All workflow state is in docs/workflows/<name>.json.
  Configuration files (~/.config/wf/config.toml, .wf/config.toml) are
  read-only inputs to wf init - they are resolved and snapshotted into
  the record at init time and never re-read after that.
  All commands that modify state use atomic writes (write tmp + rename).
  All commands accept --cwd to operate on a different project directory.
  <workflow> arguments match record filenames (without .json extension).
```

---

## Complete Pi Extension Reference

```
/wf - workflow commands in pi

LIFECYCLE COMMANDS

  /wf init <name> [--no-worktree] [--set KEY=VALUE ...]

      Create a new workflow. Resolves config (baked-in < user < project
      < --set overrides), snapshots into record. Opens a tmux window
      in the worktree with an interactive pi session.

      Autocompletions: --no-worktree, --set, config keys

  /wf run [options]

      Walk through the full workflow lifecycle. Calls wf run, shows
      unified progress in the notification area. For interactive phases
      (brainstorm, plan), wf run opens tmux sessions - the user drives
      those, then execution continues automatically.

      Same as wf run but with pi UI integration: status bar updates,
      widget updates, and notifications at each phase transition.

      All settings come from the config snapshot in the record.
      CLI flags are ephemeral overrides for this invocation.

      Options (passed through to wf run):
        --model MODEL           Override model for all phases (ephemeral)
        --prompt TEXT            Problem description / guidance
        --concurrency N         Override max parallel tasks (ephemeral)
        --no-worktrees          Override worktree isolation (ephemeral)
        --no-tmux               Override tmux usage (ephemeral)
        --auto-close [SECONDS]  Override auto-close delay (ephemeral)

      Autocompletions: all flags, model IDs, workflow names

  /wf brainstorm

      Convenience mode for brainstorming within the current pi session.
      Injects prompts/brainstorm.md as context, enables the
      record_brainstorm tool. Agent converses with user inline and
      calls record_brainstorm when design conclusions are reached.

      Tracks per-turn token usage via message_end hook and writes to
      record. This is the richer UX version of `wf brainstorm`, which
      spawns a dedicated agent session instead.

      Both paths write to the same record via wf record-brainstorm.

  /wf plan

      Convenience mode for planning within the current pi session.
      Injects prompts/planning-context.md, enables submit_plan tool,
      blocks write tools (edit, write, destructive bash). Agent explores
      codebase, then calls submit_plan.

      Toggle: run again to exit planning mode.

      Tracks per-turn token usage. This is the richer UX version of
      `wf plan`, which spawns a dedicated agent session instead.

      Both paths write to the same record via wf submit-plan.

  /wf plan compact

      Compact the brainstorm conversation (preserving decisions, discarding
      tangents), then enter planning mode. Pi-specific: uses the harness's
      context compaction API. Use when brainstorm was long and context
      space is tight.

  /wf execute [options]

      Execute all pending tasks. Calls wf execute, then polls the record
      file for UI updates. Shows per-task progress in the widget and
      footer status bar.

      All settings from config snapshot; CLI flags are ephemeral.

      Options (passed through to wf execute):
        --model MODEL           Override model for all tasks (ephemeral)
        --concurrency N         Max parallel tasks (default: 4)
        --no-worktrees          Disable worktree isolation
        --no-tmux               Override tmux usage (ephemeral)
        --auto-close [SECONDS]  Override auto-close delay (ephemeral)
        --auto-review           Override auto-review setting (ephemeral)
        --review-model MODEL    Override model for review (ephemeral)

      Autocompletions: all flags, model IDs from model registry

  /wf execute <task-id>

      Execute or re-run a single task. Confirms before re-running
      completed tasks.

      Autocompletions: task IDs from current plan with status

  /wf review [options]

      Spawn a code review subagent.

      Options (passed through to wf review / wf auto-review):
        --model MODEL           Override model for review (ephemeral)
        --ref COMMIT            Base commit to diff against
        --desc DESCRIPTION      Description of work
        --scope FILES           Focus scope
        --no-tmux               Override tmux usage (ephemeral)
        --auto-close [SECONDS]  Override auto-close delay (ephemeral)
        --auto-review           Use auto-review (with fixup plan)

      Autocompletions: all flags, model IDs

  /wf close

      Close the workflow. Calls wf close. Displays merge result.

  /wf status

      Show workflow state. Calls wf status, displays in notification.

  /wf list

      List active workflows. Calls wf list, displays in notification.

  /wf history [--json] [N]

      Show workflow history. Calls wf history, displays in notification.

  /wf recover

      Clean up after a crash. Calls wf recover, displays summary.

  /wf render

      Generate markdown from the record. Calls wf render, displays
      in notification.

TOOLS (registered for LLM use)

  record_brainstorm

      Schema: TypeBox mirroring $defs/Brainstorm
      Available when: brainstorm mode is active (/wf brainstorm)
      Action: pipes JSON to wf record-brainstorm, updates UI,
              transitions to planning phase

      Parameters:
        motivation: string          Problem statement
        solution: string            High-level approach
        designDecisions: array     [{decision, rationale}, ...]

  submit_plan

      Schema: TypeBox mirroring $defs/Plan
      Available when: plan mode is active (/wf plan)
      Action: pipes JSON to wf submit-plan, updates UI,
              exits plan mode, shows plan in widget

      Parameters:
        goal: string                One-sentence summary
        context: string             Architectural context
        defaultModel?: string       Default model for tasks
        tasks: array                [{id, title, goal, files, constraints,
                                      acceptance, dependsOn, skills?, model?}, ...]

EVENT HOOKS

  before_agent_start
      Brainstorm mode: injects prompts/brainstorm.md + enables record_brainstorm
      Plan mode: injects prompts/planning-context.md + enables submit_plan

  message_end
      Brainstorm mode: accumulates token usage, writes to record
      Plan mode: accumulates token usage, writes to record

  session_start / session_switch
      Scans docs/workflows/ for active record files.
      Restores UI state (widget, status bar) from the record.
      On /new: clears workflow state.
      On /resume: restores from the record matching the session.

UI ELEMENTS

  Status bar (footer)
      No workflow:        (nothing)
      Brainstorm mode:    📝 brainstorm
      Plan mode:          📝 plan
      Executing:          ⚡ 3/5 implementing
      Done (all passed):  ✓ 5/5
      Done (failures):    ⚠ 3/5

  Widget (sidebar)
      Shows per-task status when a plan exists:
        ○ task-1 Extract token module
        ✓ task-2 Session module          $0.045
        ⏳ task-3 Middleware integration
        ✗ task-4 Update tests            $0.032
        ⊘ task-5 Documentation (skipped)

      Status icons: ○ pending, ⏳ running, ✓ done, ✗ failed, ⊘ skipped
      Cost shown inline after completion.

  Notifications
      Phase transitions, execution start/complete summaries, errors,
      merge results - displayed via ctx.ui.notify().

  Autocompletions
      /wf init:      --set, config keys (model.plan, automation.implement, etc.)
      /wf execute:   task IDs with status, all flags, model IDs
      /wf review:    all flags, model IDs
      /wf status:    workflow names from docs/workflows/
      /wf list:      --all, --json
      /wf history:   --json, count

KEYBOARD SHORTCUT

  Ctrl+Alt+W     Toggle plan mode (same as /wf plan)
```

---

## Migration Map - Current Planner → `wf`

This section ties every new `wf` artifact back to its source in the current planner extension, prompt templates, and skills. Its purpose is to ensure that carefully-tuned prompts, hard-won heuristics, and non-obvious design decisions survive the rewrite. Implementers should read the source file and port the wisdom - not rewrite from scratch.

### Prompts

Each prompt file in `wf/prompts/` replaces an inline string constant or event handler in the current TypeScript codebase.

| New file | Source | What to preserve |
|----------|--------|------------------|
| `brainstorm.md` | **New.** No existing inline source - brainstorm mode currently has no system prompt. | This is a new system prompt for when the harness enters brainstorm mode. It should guide the agent toward calling `record_brainstorm` when design conclusions are reached. Keep it focused on that role - it is distinct from the `brainstorm` template (which is a user-invokable conversation fragment ported verbatim from `~/.pi/agent/prompts/help-me-brainstorm.md`). |
| `planning-context.md` | `index.ts` → `before_agent_start` handler (inline string, ~30 lines) **merged with** `~/.pi/agent/skills/task-decomposition/SKILL.md` (130 lines of task decomposition heuristics). | **Merge both sources into one authoritative prompt.** The inline handler has compact planning guidelines (goals not steps, constraints for architecture only, files are hints, group tightly-coupled changes, use skills field, use defaultModel). The task-decomposition skill has the richer heuristics that make plans actually work: "one reason to fail" principle, one behavioral change per task, refactor-first-then-build, "same file is not a dependency", constraint count warning (>6 = too big), sizing guide (10-30 turns), the "review before submitting" checklist (sequencing, contradictions, per-task scope, sizing). Both are currently in context during planning — the inline string is always injected, the skill is voluntarily loaded — but they diverge and overlap. Merge them into one file: start with the inline guidelines (they're well-calibrated for the tool interface), then add the skill's decomposition heuristics (they're well-calibrated for plan quality). The skill is retired after this merge — its content lives in `planning-context.md` and is always injected, replacing voluntary loading with guaranteed presence. |
| `implementer.md` | `runner.ts` → `IMPLEMENTER_PROMPT` (exported const). | **Port verbatim**, with one targeted change: replace the structured text output format ("## Summary", "## Files Changed", "## Notes") with a `report_result` tool call instruction. The agent calls `report_result(summary, notes)` when done instead of formatting markdown. `filesChanged` is no longer self-reported; it's derived from git. All behavioral instructions are preserved as-is: read suggested files first, follow constraints exactly, note contradictions, update comments/docstrings on rename, stop after 2-3 failed attempts, use research for library issues not project bugs, explain blockers instead of producing broken code. |
| `reviewer.md` | `code-review.ts` → `CODE_REVIEW_PROMPT` (exported const). | **Port verbatim.** The review prompt's agent-centric calibration is unique and working: "100% agent-developed project", "favor single-source-of-truth over duplication" (agents don't know about other copies), "comments explain WHY not WHAT", "don't flag breaking API changes" (no human muscle memory). Do not modify to incorporate content from other sources - the `check-implementation` template ships separately in `wf/templates/` for users who want that style of review. |
| `reviewer-with-plan.md` | `auto-review.ts` → `REVIEWER_SYSTEM_PROMPT` (const, ~10 lines). | Short but critical behavioral contract: review carefully, if actionable issues found call `submit_plan` with fixup tasks, if NO issues found state that clearly and do NOT call `submit_plan`. "It is perfectly fine to have no findings." |
| `merge-resolver.md` | `plan-lifecycle.ts` → `MERGE_RESOLUTION_PROMPT` (exported const). | The resolution workflow: read conflict markers in context, determine both sides' intent, resolve to preserve both, `git add` each file, verify no markers remain via grep, run `git diff --check`, do NOT commit. Structured output: Summary, Files Resolved, Notes. Fallback: "if genuinely irreconcilable, make your best judgment and explain." |

### Prompt Templates (ported verbatim to `wf/templates/`)

The four prompt templates are **ported verbatim** to `wf/templates/` as shipped defaults - they work well and should not be rewritten. The `wf template` CLI makes them harness-agnostic (any wrapper can discover and render them). Projects can override them via `docs/workflows/templates/`.

Most system prompts in `wf/prompts/` are ported verbatim from their current inline sources. The exception is `planning-context.md`, which merges the inline planning guidelines with the task-decomposition skill's heuristics into one authoritative prompt (see its row in the Prompts table above). Templates and system prompts are complementary - templates are for interactive use, system prompts are injected into subagent contexts.

| Source | Ships as |
|--------|----------|
| `~/.pi/agent/prompts/help-me-brainstorm.md` | `wf/templates/brainstorm.md` |
| `~/.pi/agent/prompts/write-plan-to-file.md` | `wf/templates/write-plan-to-file.md` |
| `~/.pi/agent/prompts/check-implementation.md` | `wf/templates/check-implementation.md` |
| `~/.pi/agent/prompts/execute-plan-step.md` | `wf/templates/execute-plan-step.md` |

### Skills

| Skill | Disposition |
|-------|-------------|
| `task-decomposition/SKILL.md` | **Retired.** Content merged into `wf/prompts/planning-context.md` (see Prompts table above). The skill's heuristics ("one reason to fail", refactor-first, sizing guide, review checklist) are valuable but were unreliably delivered — voluntary skill loading meant the agent might not read it, or might read it after already committing to a plan structure. Moving the content into the always-injected planning context prompt makes it deterministic: present at the start of every planning turn, before the agent does any reasoning. The ~1.5K token cost is negligible during planning (the phase routinely uses 50-100K tokens on codebase exploration). The skill is also pi-specific (`~/.pi/agent/skills/`); merging it into `wf/prompts/` makes the guidance available to any harness wrapper. After porting, delete the skill file from `~/.pi/agent/skills/task-decomposition/`. |

### Tool Schemas

| Current | New |
|---------|-----|
| `types.ts` → `PlanSchema` (TypeBox) | `schemas/workflow.schema.json` → `$defs/Plan` (published contract) + `tools/pi_extensions/submit-plan-tool.ts` (TypeBox mirror). Pi extensions use TypeBox (pi's native format); a Node test (`schema-consistency.test.ts`) verifies both accept/reject the same inputs. |
| `types.ts` → `TaskSchema` (TypeBox) | `schemas/workflow.schema.json` → `$defs/Task`. Referenced by `$defs/Plan`. |
| No current equivalent | `schemas/workflow.schema.json` → `$defs/Brainstorm`. New schema for `record_brainstorm` tool. |
| No current equivalent (was implicit text format in prompt) | `schemas/workflow.schema.json` → `$defs/ReportResult`. New schema for `report_result` tool. Replaces the "## Summary / ## Files Changed / ## Notes" text convention with a schema-validated tool call. `filesChanged` is deliberately omitted - derived from git. |
| `submit-plan-tool.ts` (standalone validate-only tool for review subagents) | `tools/pi_extensions/submit-plan-tool.ts` + `tools/mcp_server.py`. Still needed - review and planning subagents need a `submit_plan` tool. Now lives in `wf/tools/` (not with the pi wrapper). Pi profile loads it via `-e`; Claude Code profile loads it via MCP server. Pi extension uses a TypeBox schema mirroring `$defs/Plan`; MCP server reads the JSON Schema via `wf schema --component plan`. Both validate input and return success. |
| No current equivalent | `tools/pi_extensions/record-brainstorm-tool.ts` + `tools/mcp_server.py`. Loaded by brainstorm agents. Pi profile loads via `-e`; Claude Code via MCP. Registers the `record_brainstorm` tool with schema from `$defs/Brainstorm`. Same validate-and-return pattern. |
| No current equivalent | `tools/pi_extensions/report-result-tool.ts` + `tools/mcp_server.py`. Loaded by implementation subagents. Pi profile loads via `-e`; Claude Code via MCP. Registers the `report_result` tool with schema from `$defs/ReportResult`. Same pattern. |

### Core Logic

| Current file | New module | Migration notes |
|-------------|------------|------------------|
| `helpers.ts` → `validatePlan` | `wflib/validate.py` | Direct port. Dep ref check + DFS cycle detection. Pure function. |
| `brief.ts` → `assembleTaskBrief` | `wflib/brief.py` | **Port the code comments verbatim as docstrings.** The comments explain WHY files are hints (not inlined), WHY goals (not steps), WHY constraints are stated as facts. These are load-bearing design decisions. Also port the `toRelative` path conversion (from `helpers.ts`) - it ensures subagent file hints resolve against the worktree, not the main repo. |
| `runner.ts` → `spawnHeadless` | `wflib/runner.py` → `spawn_headless` + `profiles/pi.py` + `adapters/pi_json_mode.py` | The `--no-extensions -e research.ts -e web-fetch/index.ts` pattern (clean tool set + allowed extras) is now encoded in `profiles/pi.py` → `build_headless_cmd`. JSON line parsing for `message_end`/`tool_result_end` events moves to the pi JSON-mode adapter. Runner is profile-driven: calls `profile.build_headless_cmd()` for command construction, `profile.parse_headless_output()` for result extraction. Zero pi-specific code in runner.py. Abort handling: SIGTERM then SIGKILL after 5s timeout. Temp file cleanup in finally block. |
| `runner.ts` → `parseOutput` | `wflib/runner.py` → `extract_report_result` + `extract_summary_fallback` (both delegate to `types.extract_tool_call`) | **Replaced.** The old regex-based extraction of "## Summary" / "## Files Changed" / "## Notes" from text is replaced by `extract_report_result`, which delegates to the shared `extract_tool_call(messages, 'report_result')` in types.py. Schema-validated, deterministic. `filesChanged` is no longer extracted from agent output at all - it comes from `git diff --name-only` in the worktree (authoritative). The fallback to "last 500 chars" is preserved in `extract_summary_fallback` for the degraded path when the agent didn't call the tool (crash, error, forgot). |
| `tmux-runner.ts` | `wflib/tmux.py` + `wflib/runner.py` → `spawn_in_tmux` + `profiles/pi.py` → `build_tmux_wrapper` + `adapters/pi_session.py` | Execution window state management (first task creates window, subsequent tasks split panes) stays in `tmux.py`. Wrapper script generation moves to `profiles/pi.py` → `build_tmux_wrapper` - the profile generates the bash script with EXIT/HUP/TERM/INT trap, pi invocation, adapter call, and exit-code file write. Completion polling stays in `runner.py` (universal). Session file reading is in the pi session adapter (replaces direct `SessionManager.open` import). Pane border titles, tiled layout re-application after each split stay in `tmux.py`. |
| `git.ts` | `wflib/git.py` | Thin wrapper. Direct port. |
| `worktree.ts` → task worktree functions | `wflib/worktree.py` | **Key detail:** `commit_if_dirty` uses `git add -A -- ':!docs/workflows/'` to exclude the record file directory. Without this, stale record copies from task worktrees merge back and overwrite the scheduler's updates. Also: `.worktree-setup` hook (runs instead of default symlinking), `symlink_deps` default list (node_modules, .venv, vendor, etc.), rebase-then-ff merge strategy, worktree preservation on conflict (don't clean up - user needs it for manual resolution). |
| `worktree.ts` → plan worktree functions | `wflib/worktree.py` → workflow worktree functions | `createPlanWorktree` → `create_workflow_worktree`, `closePlanWorktree` → `close_workflow_worktree`. The `.plan-init-*.json` metadata file is replaced by the workflow record's `workflow.worktree` + `workflow.sourceBranch` fields. |
| `code-review.ts` → `buildDiffContext` | `wflib/review.py` → `build_diff_context` | Priority chain: baseCommit → uncommitted changes. 100KB cap on full diff with graceful fallback message. Includes commit log, diff stat, and full diff as separate markdown sections. |
| `auto-review.ts` → `extractPlanFromMessages` | `wflib/review.py` → `extract_plan_from_messages` (delegates to `types.extract_tool_call`) | Delegates to the shared `extract_tool_call(messages, 'submit_plan')` in types.py. Same extraction pattern as `extract_report_result` - both use one utility, eliminating the duplication between runner.py and review.py in the legacy code. |
| `auto-review.ts` → `runAutoReview` | `wflib/review.py` → `run_auto_review` | Orchestrates review agent spawning with the combined CODE_REVIEW_PROMPT + diff context + reviewer-with-plan system prompt. Loads submit-plan-tool extension for the subagent. |
| `index.ts` → DAG scheduler (pool-based `tryStart` loop) | `wflib/scheduler.py` → `execute_plan` + `wflib/task_executor.py` → `run_task` | **Pool-based, not wave-based** - task C that depends only on A starts when A finishes, even if slow sibling B is still running. Currently duplicated in index.ts (main execution + fixup execution) - consolidate to one function. The per-task lifecycle (worktree → brief → spawn → results → merge → cleanup) is extracted from the scheduler into `task_executor.run_task`, replacing the implicit `runTask` closure in index.ts. Scheduler owns DAG logic only: pool management, `get_ready_tasks`, `skip_dependents` with transitive BFS closure, `reset_ready_skipped` (iterates until stable). Merge serialization via asyncio.Lock passed to `run_task`. |
| `index.ts` → `resolveTaskModel` | `wflib/scheduler.py` → `resolve_task_model` | Extended precedence: CLI --model > task.model > plan.defaultModel > config.model.implement > None. The config snapshot adds a new fallback level between the LLM-authored plan default and "no model specified." **Intentional:** user's explicit CLI flag beats LLM-generated plan values, which beat the config snapshot. Returns both the model and its source (for logging/display). The returned name is still a wf canonical/user string - it is NOT harness-specific. Translation to the exact harness string happens in `profile.resolve_model()`, called inside `build_headless_cmd`/`build_tmux_wrapper`. This keeps the scheduler profile-agnostic. |
| No current equivalent | `wflib/config.py` | **New module.** Configuration loading (TOML via `tomllib`), merging (deep dict merge), resolution (5-level precedence chain), snapshotting (at init time). Also handles `wf config` subcommands (list, get, set). Config files are `~/.config/wf/config.toml` (user) and `.wf/config.toml` (project). The resolved snapshot is stored in `workflow.config` in the record and read by all subsequent commands. CLI flags override the snapshot ephemerally. |
| `helpers.ts` → state file I/O | **Eliminated.** `wflib/record.py` | The separate `.state.json` files and `~/.pi/plan-history.jsonl` are replaced by the single workflow record file. All the durability guarantees (atomic write, crash recovery, cross-session resume) now come from record.py's atomic write (write tmp + rename). |
| `plan-lifecycle.ts` → `readPlanMetadata` | **Eliminated.** Record file | The `.plan-init-*.json` tracking file is replaced by `workflow.worktree`, `workflow.sourceBranch`, `workflow.sourceCommit` in the record. |

### Harness-Specific Logic (stays in pi wrapper)

| What | Current source | Why it stays |
|------|---------------|---------------|
| Planning usage tracking | `index.ts` → `message_end` event handler | Accumulates input/output/cache/cost/turns during brainstorm and plan modes. Pi-specific - the harness fires `message_end` events. |
| Session restore | `index.ts` → `session_start`/`session_switch` handlers | Restores workflow state from record file on session load. Resets `running` tasks to `pending` (they were interrupted). Pi-specific session lifecycle. |
| UI rendering | `index.ts` → `updateUI`, status bar, widget | Status icons (○ ⏳ ✓ ✗ ⊘), colors, per-task cost display, footer progress. Reads record file for data. Pi TUI-specific. |
| Autocompletions | Various `getArgumentCompletions` | Task IDs with status, workflow names from `docs/workflows/`, model IDs from model registry, flag names. Pi-specific. |
| `auto-quit.ts` | `auto-quit.ts` | Pi extension that listens for `agent_end` and triggers exit after a configurable delay. Used for auto-closing tmux panes. |
| Keyboard shortcut (Ctrl+Alt+W) | `index.ts` → `registerShortcut` | Pi-specific keybinding registration. |
