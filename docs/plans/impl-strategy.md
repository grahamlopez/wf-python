# `wf` Implementation Proto-Plan

## 1. TDD Feasibility

**The sketch is already a test spec.** Every module has explicit function signatures, input/output types, and behavioral contracts. The fastest path is to encode the sketch into tests first, then build the implementation to satisfy them.

### Module categories by TDD suitability

**Pure-function modules — strict red→green TDD:**

| Module | Contract | Test shape |
|--------|----------|------------|
| `types.py` | Dataclass construction, `from_dict`/`to_dict`, `extract_tool_call` | Data in, data out |
| `validate.py` | Dep refs, cycle detection, heuristic warnings | `Plan` in, `ValidationResult` out |
| `config.py` | Merging, resolution, 5-level precedence, strict unknown-key rejection | Dicts in, `WorkflowConfig` out |
| `brief.py` | Task brief assembly from plan + completed results | `Task + Plan + results` in, string out |
| `render.py` | Markdown rendering, usage tables, status formatting | Record data in, strings out |
| `templates.py` | Frontmatter parsing, variable substitution, discovery | Strings in, strings out |
| `completions.py` | Shell script generation, dynamic completion output | Pure string output |
| `help.py` | Topic lookup, prefix matching, content checks | Pure strings |
| `profiles/` | Command construction, model resolution, tool path mapping | Config in, `list[str]` or `str` out |

Every one of these can have tests written directly from the sketch with zero guessing. No mocking needed — just construct inputs, call the function, assert outputs.

**Filesystem/git modules — TDD with `tmp_path` fixtures:**

| Module | Contract | Test shape |
|--------|----------|------------|
| `record.py` | Create/load/save, atomic writes, phase transitions | Temp git repo, assert file contents and round-trip fidelity |
| `git.py` | Thin wrapper: `is_clean`, `get_branch`, `get_head` | Real git in temp dirs |
| `worktree.py` | Create/merge/cleanup, conflict metadata, `docs/workflows/` exclusion | Real git worktrees in temp dirs |

Clear expected states: "after `merge_back`, the main branch has the task's commits" → directly assertable against git log.

**E2E tests — TDD at the scenario level:**

The sketch provides 12+ fixture scenarios with explicit inputs (`plan.json`, `scenario.json`) and expected outputs (record state, git state, event ordering). The mock profile and mock agent isolate the orchestration engine from any real harness — you can fully test scheduling, record updates, merge handling, and recovery without Pi, Claude Code, or any agent installed.

E2E test assertions are already spelled out in the sketch:

```python
# diamond-deps: D must wait for both B and C
assert tasks["task-4"]["status"] == "done"
assert task4_start["t"] > task2_done["t"]
assert task4_start["t"] > task3_done["t"]
```

**Caveat:** E2E tests can't be "red" until the full pipeline exists (scheduler → task_executor → runner → worktree → merge). They work better as "test-informed development" — write the test alongside the implementation, but the test only becomes runnable when the whole vertical slice is wired up. The fixtures and scenarios are still the spec; they're just written in the phase where they become executable.

### What's needed before any tests can run

A **Phase 0** (scaffold) that creates:

1. **Project skeleton** — full directory structure matching the sketch, `bin/wf` shebang, all `__init__.py` files
2. **JSON Schema** — `schemas/workflow.schema.json` with all `$defs` (the published test contract)
3. **Type stubs** — all dataclasses in `types.py` fully defined, `from_dict`/`to_dict` raising `NotImplementedError`
4. **Test infrastructure:**
   - `tests/conftest.py` with tmp git repo fixtures
   - `tests/util.py` — helper to run `wf` as a subprocess and parse stdout (for integration/E2E tests that exercise the CLI)
   - Test runner: stdlib `unittest` (zero deps), runnable via `python3 -m pytest tests/` when pytest is available. No external test dependencies.
   - `tests/e2e/mock_agent.py` from the sketch
   - Fixture directories (`tests/e2e/fixtures/simple-split/`, etc.) with `plan.json`, `scenario.json`, and `expected/` stubs

Once this exists, every pure-function module can have tests written that import cleanly, run, and fail (red). Implementation tasks turn them green.

### Red→green implementation order

Within and across phases, the natural dependency order for turning tests green is:

```
1. types.py + schema       (everything depends on these)
2. config.py               (record.py needs it, scheduler needs it)
3. validate.py             (submit-plan needs it, standalone)
4. record.py               (scheduler writes through it)
5. brief.py                (task_executor calls it)
6. git.py + worktree.py    (task_executor needs them)
7. profiles/ + adapters/   (runner.py delegates to them)
8. runner.py               (task_executor spawns through it)
9. task_executor.py        (scheduler delegates to it)
10. scheduler.py           (the DAG engine)
11. review.py              (post-execution)
12. CLI (bin/wf)           (wires everything together)
13. help.py + completions.py + render.py + templates.py  (leaf modules, no blockers)
```

Steps 1-6 are foundation. Steps 7-11 are orchestration. Steps 12-13 are surface. This order ensures each module's dependencies are green before it needs them.

---

## 2. Planning Structure: Two-Level Hierarchy

**A single monolithic plan won't work.** This needs a macro plan decomposed into per-phase implementation plans.

### Why

- **Scale:** A faithful implementation is 35-50 discrete tasks (15 wflib modules + 3 profiles + 3 adapters + 3 tool extensions + MCP server + schema + 6 prompts + 4 templates + CLI + test infra + unit/integration/E2E tests + pi wrapper). That's 3-4× the practical limit for one `submit_plan`.
- **Depth:** Deep dependency chains (scheduler → task_executor → runner → profiles → types) can't be expressed as flat tasks without becoming an unreadable linear chain.
- **TDD doubling:** If each module has paired "write tests" + "implement" tasks, the count approaches 60-70.
- **Feedback loops:** Later phases should benefit from what's learned implementing earlier ones. A single upfront plan locks in all decisions before any code exists.
- **Subsystem boundaries:** The project has distinct subsystems (types/schema, config/record, git/worktree, scheduler/executor, profiles/adapters, CLI, tools) that map naturally to separate planning batches.

### Macro Plan (Plan A): Phases and Milestones

Each phase is a self-contained `submit_plan` that produces a tested, working vertical slice. Phase N's plan is written after Phase N-1 ships, incorporating lessons learned.

### Phase 0 — Scaffold (~5-7 tasks)
**Goal:** Enable tests to import and run (red baseline).
**Scope:**
- Full directory tree per the sketch (all dirs, all `__init__.py`)
- `bin/wf` — shebang + minimal argparse skeleton (parses subcommands, prints help)
- `schemas/workflow.schema.json` — complete, with all `$defs`
- `wflib/types.py` — all dataclasses fully defined (fields, defaults, enums), `from_dict`/`to_dict`/`extract_tool_call` as `NotImplementedError` stubs
- `tests/conftest.py` — tmp git repo fixture, mock-agent-on-PATH fixture
- `tests/util.py` — subprocess helper for CLI tests
- `tests/e2e/mock_agent.py` — the deterministic mock from the sketch
- `tests/e2e/fixtures/` — at least `simple-split/`, `diamond-deps/`, `task-failure/` with `plan.json`, `scenario.json`, `expected/`
- Placeholder test files for each module (importable, with `@pytest.mark.skip` or `unittest.skip`)

**TDD Output:** `python3 -m pytest tests/` runs — imports succeed, all tests skip or fail.

### Phase 1 — Pure Foundation (~8-12 tasks)
**Goal:** Pure logic modules fully implemented and tested.
**Scope:**
- `types.py` (full impl), `validate.py`, `config.py`, `brief.py`, `render.py`, `templates.py` + all their unit tests

**TDD Approach:** Strict red→green — write each test file from the sketch's contracts, then implement the module.
**TDD Output:** All `tests/unit/` pass.

### Phase 2 — Git/IO Layer (~6-8 tasks)
**Goal:** Filesystem + git primitives implemented and tested.
**Scope:**
- `git.py`, `worktree.py`, `record.py`, `log.py` + integration tests

**TDD Approach:** TDD with `tmp_path` git repo fixtures — real git, no agent subprocesses.
**TDD Output:** All `tests/integration/` pass.

### Phase 3 — Profiles + Runner (~8-10 tasks)
**Goal:** Harness abstraction and output parsing complete.
**Scope:**
- Profile protocol + registry, `pi.py`, `claude_code.py`, `mock.py`, all adapters, `runner.py`, `tmux.py` + profile/adapter tests

**TDD Approach:** Test command construction, model resolution, and recorded output parsing against committed fixtures.
**TDD Output:** All `tests/unit/test_profiles.py`, `tests/profile/`, `tests/adapter/` pass.

### Phase 4 — Orchestration + CLI (~10-14 tasks)
**Goal:** Full workflow execution engine + CLI surface.
**Scope:**
- `scheduler.py`, `task_executor.py`, `review.py`, `bin/wf` (full argparse), `help.py`, `completions.py` + E2E tests

**TDD Approach:** E2E fixtures go green. Tests written alongside implementation since they need the full pipeline.
**TDD Output:** All `tests/e2e/` pass, `wf help` works.

### Phase 5 — Tools + Prompts + Pi Wrapper (~6-10 tasks)
**Goal:** Tooling + UI integration complete.
**Scope:**
- Pi tool extensions (TS), MCP server, all system prompts, shipped templates (ported verbatim), pi wrapper `index.ts`

**TDD Approach:** Integration testing against `wf` CLI.
**TDD Output:** Tools validate-and-return, prompts ported, wrapper delegates to CLI.

**Total: ~45-60 tasks across 6 phases.**

### Per-Phase Plans (Plan B): Written Just-in-Time

For each phase, a focused implementation plan is written with tasks sized for one subagent. The plan is authored when that phase is ready to execute — not upfront. This lets each plan incorporate:

- Actual module interfaces from the previous phase (not guesses)
- Any sketch adjustments discovered during implementation
- Test failures that revealed ambiguities in the sketch

### Why this phasing works for TDD

- **Phase 0** creates the skeleton that makes all subsequent test imports work. After this, any developer can `cd wf && python3 -m pytest` and see a clean red baseline.
- **Phase 1** is pure TDD: every module is a pure function with explicit inputs and outputs. Write test, run (red), implement, run (green), repeat. No mocking, no I/O, no subprocesses.
- **Phase 2** tests need real git repos but no agent subprocesses — a clean boundary. `tmp_path` fixtures make them fast and isolated.
- **Phase 3** tests use recorded output fixtures (captured from real harness runs, committed as test data). No live agents needed — testable in complete isolation.
- **Phase 4** is where E2E tests become runnable. The mock profile + mock agent exercise the full pipeline: DAG scheduling, worktree lifecycle, merge-back, conflict resolution, crash recovery. All without any real AI harness.
- **Phase 5** is integration with external systems (pi extensions, MCP, real prompts). By this point, the core engine is fully tested.

Each phase boundary is a **checkpoint**: everything implemented so far is tested and passing. No phase begins with a broken test suite.

**Next step: plan Phase 0 in detail and execute it.**
