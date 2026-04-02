"""Pi Runner Profile.

Encodes everything needed to spawn and read results from the pi agent harness.
"""

from __future__ import annotations

from pathlib import Path
import shlex

from adapters import pi_json_mode, pi_session
from profiles import resolve_alias, wf_dir
from wflib.types import ModelsConfig


class PiProfile:
    name = "pi"

    # Built-in canonical name → exact pi model string.
    BUILTIN_MODEL_MAP: dict[str, str | None] = {
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
        """Map a model name to the exact pi-specific string."""
        canonical = resolve_alias(name, models_config)
        model_map = self._effective_map(models_config)
        if canonical in model_map:
            mapped = model_map[canonical]
            if mapped is None:
                raise ValueError(
                    f"Model '{name}' (canonical: '{canonical}') is not available "
                    "on the pi harness."
                )
            return mapped
        return canonical

    def list_models(self, models_config: ModelsConfig) -> list[tuple[str, str]]:
        """Return (canonical_name, harness_id) pairs for all models."""
        return [
            (name, harness_id)
            for name, harness_id in self._effective_map(models_config).items()
            if harness_id is not None
        ]

    def build_headless_cmd(self, *,
        system_prompt_file: str,
        model: str | None,
        tools: list[str],
        prompt: str,
        cmd_override: str | None = None,
        models_config: ModelsConfig | None = None,
    ) -> list[str]:
        """Build the full argv for headless pi execution."""
        cmd = cmd_override or "pi"
        args = [
            cmd,
            "--mode",
            "json",
            "-p",
            "--no-session",
            "--no-extensions",
            "--append-system-prompt",
            system_prompt_file,
        ]
        args += [
            "-e",
            f"{self._ext_dir}/research.ts",
            "-e",
            f"{self._ext_dir}/web-fetch/index.ts",
        ]
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
        """Generate a bash wrapper for tmux execution."""
        cmd = cmd_override or "pi"
        pi_args = [
            "--no-extensions",
            "--append-system-prompt",
            system_prompt_file,
            "--session-dir",
            session_dir,
        ]
        pi_args += [
            "-e",
            f"{self._ext_dir}/research.ts",
            "-e",
            f"{self._ext_dir}/web-fetch/index.ts",
        ]
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

        adapter_cmd = (
            f"python3 {self._wf_dir}/adapters/pi_session.py "
            f"{session_dir} {results_file}"
        )

        return f"""#!/bin/bash
RESULT_FILE='{exit_code_file}'
_cleanup() {{ if [ ! -f \"$RESULT_FILE\" ]; then echo 1 > \"$RESULT_FILE\"; fi }}
trap _cleanup EXIT HUP TERM INT
{f'export PI_AUTO_CLOSE_DELAY={auto_close}' if auto_close and auto_close > 0 else ''}
{cmd} {' '.join(shlex.quote(a) for a in pi_args)}
{adapter_cmd}
echo $? > \"$RESULT_FILE\"
"""

    def parse_headless_output(self, stdout: str) -> dict:
        """Parse captured stdout from headless mode."""
        return pi_json_mode.parse(stdout)

    def parse_session_output(self, session_dir: str, results_file: str) -> dict:
        """Parse session/results from tmux mode."""
        return pi_session.parse(session_dir, results_file)

    def get_tool_paths(self) -> dict[str, str]:
        """Map tool names to pi extension paths."""
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
        return wf_dir()

    @property
    def _ext_dir(self) -> str:
        """Pi extensions directory (~/.pi/agent/extensions)."""
        return str(Path.home() / ".pi" / "agent" / "extensions")
