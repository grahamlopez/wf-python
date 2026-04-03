"""Per-task execution lifecycle.

Owns the full pipeline for running a single task: worktree setup,
brief assembly, agent spawning, result processing, merge-back, and cleanup.
Called by the scheduler for each task.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess

from wflib.types import (
    ImplementationEventType,
    Plan,
    Task,
    TaskResult,
    TaskStatus,
    WorkflowConfig,
    WorkflowRecord,
)
from wflib.worktree import MergeResult, WorktreeInfo
from profiles import RunnerProfile


def _load_system_prompt(filename: str) -> str:
    """Load a system prompt from the prompts/ directory."""
    prompts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "prompts",
    )
    path = os.path.join(prompts_dir, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


async def run_task(
    task: Task,
    plan: Plan,
    record: WorkflowRecord,
    cwd: str,
    merge_lock: asyncio.Lock,
    config: WorkflowConfig,
    cli_model: str | None = None,
) -> TaskResult:
    """Execute a single task through the full lifecycle.

    The scheduler has already called record_task_start before invoking this
    function.  run_task must NOT call record_task_start again.  Instead,
    after creating the worktree it updates active_resources and
    worktree_path on the task result, then saves.

    Pipeline:
      (1)  create worktree if config.execute.worktrees
      (2)  update active_resources + worktree_path, save
      (3)  assemble brief via brief.py
      (4)  resolve model via scheduler.resolve_task_model
      (5)  get profile via profiles.get_profile
      (6)  spawn agent via runner.spawn_headless
      (7)  preserve results via _preserve_results
      (8)  capture diff/stat
      (9)  commit if dirty via worktree.commit_if_dirty
      (10) merge back with lock via _merge_and_cleanup
      (11) build TaskResult and return
    """
    from wflib._util import utc_now_iso
    from wflib.brief import assemble_task_brief
    from wflib.record import save_record, get_implementation_state
    from wflib.scheduler import resolve_task_model
    from wflib.runner import spawn_headless
    from profiles import get_profile

    use_worktrees = config.execute.worktrees
    workflow_id = record.workflow.id
    workflow_name = record.workflow.name
    profile = get_profile(config.agent.profile)

    # Preserve started_at set by the scheduler's record_task_start
    started_at = None
    if record.implementation and task.id in record.implementation.tasks:
        started_at = record.implementation.tasks[task.id].started_at

    wt: WorktreeInfo | None = None
    agent_cwd = cwd

    try:
        # (1) Create worktree if config.execute.worktrees
        if use_worktrees:
            wt = _setup_worktree(task, cwd, workflow_id)
            agent_cwd = wt.path

            # (2) Update active_resources + worktree_path, save
            record.implementation.active_resources[task.id] = wt.path
            record.implementation.tasks[task.id].worktree_path = wt.path
            save_record(record, cwd)

        # (3) Assemble brief via brief.py
        results = get_implementation_state(record)
        brief_text = assemble_task_brief(task, plan, results)

        # (4) Resolve model via scheduler.resolve_task_model
        model, _source = resolve_task_model(task, plan, config, cli_model)

        # (5) Get profile (already resolved above)

        # (6) Spawn agent via runner.spawn_headless
        system_prompt = _load_system_prompt("implementer.md")
        tools = list(profile.get_tool_paths().keys())

        agent_result = await asyncio.to_thread(
            spawn_headless,
            cwd=agent_cwd,
            prompt=brief_text,
            system_prompt=system_prompt,
            profile=profile,
            tools=tools,
            model=model,
            cmd_override=config.agent.cmd,
            models_config=config.models,
        )

        # (7) Preserve results via _preserve_results
        results_path = (
            os.environ.get("WF_RESULTS_PATH")
            or os.path.join(agent_cwd, "results.json")
        )
        is_failure = agent_result.exit_code != 0 or agent_result.error is not None
        _preserve_results(
            results_path=results_path,
            workflow_name=workflow_name,
            task_id=task.id,
            cwd=cwd,
            preserve_session=is_failure,
        )

        # Propagate model from agent_result into usage
        usage = agent_result.usage
        if agent_result.model and not usage.model:
            usage.model = agent_result.model

        # On agent failure: return FAILED immediately
        if is_failure:
            error_text = (
                agent_result.error
                or f"Agent exited with code {agent_result.exit_code}"
            )
            return TaskResult(
                status=TaskStatus.FAILED,
                started_at=started_at,
                completed_at=utc_now_iso(),
                exit_code=agent_result.exit_code,
                brief=brief_text,
                summary=agent_result.summary,
                notes=agent_result.notes,
                error=error_text,
                worktree_path=wt.path if wt else None,
                worktree_preserved=wt is not None,
                usage=usage,
            )

        # (8) Capture diff/stat
        if wt:
            files_changed, diff_stat = _capture_diff_stat(
                wt.path, wt.main_branch,
            )
        else:
            files_changed, diff_stat = _capture_diff_stat(cwd, "HEAD")

        # (9) Commit if dirty via worktree.commit_if_dirty
        if wt:
            from wflib.worktree import commit_if_dirty
            commit_if_dirty(wt.path, task.id, task.title)

        # (10) Merge back with lock via _merge_and_cleanup
        if wt:
            merge_result = await _merge_and_cleanup(
                cwd=cwd,
                wt=wt,
                task=task,
                record=record,
                merge_lock=merge_lock,
                profile=profile,
                model=model,
                config=config,
            )

            if not merge_result.success:
                return TaskResult(
                    status=TaskStatus.FAILED,
                    started_at=started_at,
                    completed_at=utc_now_iso(),
                    exit_code=agent_result.exit_code,
                    brief=brief_text,
                    summary=agent_result.summary,
                    notes=agent_result.notes,
                    files_changed=files_changed,
                    diff_stat=diff_stat,
                    error=f"Merge failed: {merge_result.conflicts or 'unknown conflict'}",
                    worktree_path=wt.path,
                    worktree_preserved=True,
                    usage=usage,
                )

        # (11) Build TaskResult and return
        return TaskResult(
            status=TaskStatus.DONE,
            started_at=started_at,
            completed_at=utc_now_iso(),
            exit_code=agent_result.exit_code or 0,
            brief=brief_text,
            summary=agent_result.summary,
            notes=agent_result.notes,
            files_changed=files_changed,
            diff_stat=diff_stat,
            worktree_path=wt.path if wt else None,
            worktree_preserved=False,
            usage=usage,
        )
    except Exception as exc:
        from wflib._util import utc_now_iso as _utc_now
        return TaskResult(
            status=TaskStatus.FAILED,
            started_at=started_at,
            completed_at=_utc_now(),
            error=str(exc),
            worktree_path=wt.path if wt else None,
            worktree_preserved=wt is not None,
        )


def _setup_worktree(
    task: Task,
    cwd: str,
    workflow_id: str,
) -> WorktreeInfo:
    """Create and setup a task worktree. Records active_resource."""
    from wflib.worktree import create_task_worktree, setup_worktree

    wt = create_task_worktree(cwd, workflow_id, task.id)
    setup_worktree(cwd, wt.path)
    return wt


def _capture_diff_stat(
    worktree_path: str,
    main_branch: str,
) -> tuple[list[str], str | None]:
    """Get files_changed and diff_stat from the worktree branch.

    Uses ``git diff --name-only <main_branch>`` and
    ``git diff --stat <main_branch>`` in the given path.
    For bare mode (no worktree) the caller passes ``"HEAD"`` as
    main_branch so the diff shows uncommitted changes.
    """
    from wflib.git import git

    # Changed file list
    name_result = git(["diff", "--name-only", main_branch], cwd=worktree_path)
    if name_result.ok and name_result.stdout.strip():
        files = [f for f in name_result.stdout.strip().splitlines() if f.strip()]
    else:
        files = []

    # Diff stat summary
    stat_result = git(["diff", "--stat", main_branch], cwd=worktree_path)
    diff_stat = (
        stat_result.stdout.strip()
        if stat_result.ok and stat_result.stdout.strip()
        else None
    )

    return files, diff_stat


async def _merge_and_cleanup(
    cwd: str,
    wt: WorktreeInfo,
    task: Task,
    record: WorkflowRecord,
    merge_lock: asyncio.Lock,
    profile: RunnerProfile,
    model: str | None,
    config: WorkflowConfig,
) -> MergeResult:
    """Acquire merge lock, rebase, merge, cleanup.

    On conflict: spawn conflict resolution agent (prompts/merge-resolver.md)
    using the task's resolved model.  If resolution succeeds, continue
    rebase and fast-forward merge.  If resolution fails, preserve worktree
    and record error.

    On clean merge: cleanup worktree, clear active_resource.
    """
    from wflib.git import git
    from wflib.record import record_event, clear_active_resource, save_record
    from wflib.worktree import merge_back, cleanup_worktree
    from wflib.runner import spawn_headless

    async with merge_lock:
        # Record merge start
        record_event(record, ImplementationEventType.MERGE_START, task=task.id)
        save_record(record, cwd)

        # Attempt rebase + ff-merge
        result = merge_back(cwd, wt)

        if result.success:
            record_event(
                record, ImplementationEventType.MERGE_COMPLETE, task=task.id,
            )
            cleanup_worktree(cwd, wt)
            clear_active_resource(record, task.id)
            record_event(
                record, ImplementationEventType.WORKTREE_CLEANUP, task=task.id,
            )
            save_record(record, cwd)
            return result

        # --- Merge conflict: attempt automatic resolution ---

        record_event(
            record,
            ImplementationEventType.MERGE_RESOLVE_START,
            task=task.id,
            detail=f"Conflict files: {', '.join(result.conflict_files or [])}",
        )
        save_record(record, cwd)

        # Build resolution prompt (includes 'merge-resolve' for mock matching)
        prompt_parts = [
            "merge-resolve: Resolve the following merge conflicts.\n",
        ]
        if result.conflict_files:
            prompt_parts.append("Conflicting files:")
            for f in result.conflict_files:
                prompt_parts.append(f"- {f}")
        if result.conflicts:
            prompt_parts.append(f"\nConflict details:\n{result.conflicts}")
        conflict_prompt = "\n".join(prompt_parts)

        # Load merge-resolver system prompt
        system_prompt = _load_system_prompt("merge-resolver.md")
        tools = list(profile.get_tool_paths().keys())

        # Spawn resolution agent in the worktree
        resolution_result = await asyncio.to_thread(
            spawn_headless,
            cwd=wt.path,
            prompt=conflict_prompt,
            system_prompt=system_prompt,
            profile=profile,
            tools=tools,
            model=model,
            cmd_override=config.agent.cmd,
            models_config=config.models,
        )

        # Check for remaining unmerged files
        check = git(
            ["diff", "--name-only", "--diff-filter=U"], cwd=wt.path,
        )
        remaining_conflicts = check.stdout.strip() if check.ok else ""

        if not remaining_conflicts and resolution_result.exit_code == 0:
            # Resolution succeeded — stage all, continue rebase, ff-merge
            git(["add", "-A"], cwd=wt.path)

            # Continue the rebase (GIT_EDITOR=true suppresses editor)
            env = os.environ.copy()
            env["GIT_EDITOR"] = "true"
            subprocess.run(
                ["git", "rebase", "--continue"],
                cwd=wt.path,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Fast-forward merge into main branch
            git(["checkout", wt.main_branch], cwd=cwd)
            ff_result = git(["merge", "--ff-only", wt.branch], cwd=cwd)

            if ff_result.ok:
                record_event(
                    record,
                    ImplementationEventType.MERGE_RESOLVE_COMPLETE,
                    task=task.id,
                )
                cleanup_worktree(cwd, wt)
                clear_active_resource(record, task.id)
                record_event(
                    record,
                    ImplementationEventType.WORKTREE_CLEANUP,
                    task=task.id,
                )
                save_record(record, cwd)
                return MergeResult(
                    success=True,
                    resolution_attempted=True,
                    resolution_succeeded=True,
                )

            # FF merge failed even after resolution
            record_event(
                record,
                ImplementationEventType.MERGE_RESOLVE_FAILED,
                task=task.id,
                detail=f"FF merge failed after resolution: {ff_result.stderr}",
            )
            save_record(record, cwd)
            return MergeResult(
                success=False,
                conflicts=ff_result.stderr or ff_result.stdout,
                resolution_attempted=True,
                resolution_succeeded=False,
            )

        # Resolution failed or conflicts remain — preserve worktree
        detail = (
            f"Remaining conflicts: {remaining_conflicts}"
            if remaining_conflicts
            else "Resolution agent failed"
        )
        record_event(
            record,
            ImplementationEventType.MERGE_RESOLVE_FAILED,
            task=task.id,
            detail=detail,
        )
        save_record(record, cwd)
        return MergeResult(
            success=False,
            conflicts=result.conflicts,
            conflict_files=result.conflict_files,
            resolution_attempted=True,
            resolution_succeeded=False,
        )


def _preserve_results(
    results_path: str,
    workflow_name: str,
    task_id: str,
    cwd: str,
    session_dir: str | None = None,
    preserve_session: bool = False,
) -> None:
    """Copy results.json (always) and session file (on failure) to
    docs/workflows/.sessions/<workflow>/ for crash recovery.
    """
    sessions_dir = os.path.join(
        os.path.abspath(cwd),
        "docs", "workflows", ".sessions", workflow_name,
    )
    os.makedirs(sessions_dir, exist_ok=True)

    # Always copy results.json if it exists
    dest = os.path.join(sessions_dir, f"{task_id}.results.json")
    if os.path.exists(results_path):
        shutil.copy2(results_path, dest)

    # On failure, also copy session .jsonl if session_dir is provided
    if preserve_session and session_dir and os.path.isdir(session_dir):
        for fname in os.listdir(session_dir):
            if fname.endswith(".jsonl"):
                src = os.path.join(session_dir, fname)
                session_dest = os.path.join(
                    sessions_dir, f"{task_id}.session.jsonl",
                )
                shutil.copy2(src, session_dest)
                break  # Copy only the first .jsonl
