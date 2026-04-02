"""Tests for profiles.pi — command construction + recorded output through pi adapters."""

import unittest

from profiles.pi import PiProfile
from wflib.types import ModelsConfig


class TestPiHeadlessCommand(unittest.TestCase):
    def test_basic_command_structure(self):
        """Headless command starts with pi --mode json -p --no-session --no-extensions."""
        profile = PiProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=[],
            prompt="Hello",
        )
        self.assertEqual(
            cmd[:6],
            ["pi", "--mode", "json", "-p", "--no-session", "--no-extensions"],
        )

    def test_appends_system_prompt(self):
        """Command includes --append-system-prompt with the system prompt file."""
        profile = PiProfile()
        system_prompt = "/tmp/system.md"
        cmd = profile.build_headless_cmd(
            system_prompt_file=system_prompt,
            model=None,
            tools=[],
            prompt="Hello",
        )
        idx = cmd.index("--append-system-prompt")
        self.assertEqual(cmd[idx + 1], system_prompt)

    def test_loads_research_and_web_fetch(self):
        """Command includes -e flags for research.ts and web-fetch/index.ts."""
        profile = PiProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=[],
            prompt="Hello",
        )
        self.assertIn(f"{profile._ext_dir}/research.ts", cmd)
        self.assertIn(f"{profile._ext_dir}/web-fetch/index.ts", cmd)

    def test_loads_tool_extensions(self):
        """Requested tools are loaded as -e flags."""
        profile = PiProfile()
        tools = ["report-result", "record-brainstorm"]
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=tools,
            prompt="Hello",
        )
        tool_paths = profile.get_tool_paths()
        for tool in tools:
            tool_path = tool_paths[tool]
            self.assertIn(tool_path, cmd)
            self.assertEqual(cmd[cmd.index(tool_path) - 1], "-e")

    def test_model_flag(self):
        """Model is resolved and passed as --model."""
        profile = PiProfile()
        cmd = profile.build_headless_cmd(
            system_prompt_file="/tmp/system.md",
            model="sonnet",
            tools=[],
            prompt="Hello",
            models_config=ModelsConfig(),
        )
        model_index = cmd.index("--model")
        self.assertEqual(cmd[model_index + 1], "claude-sonnet-4-5")


class TestPiTmuxWrapper(unittest.TestCase):
    def test_wrapper_script_structure(self):
        """Wrapper script has shebang, trap, pi invocation, adapter call, exit-code write."""
        profile = PiProfile()
        wrapper = profile.build_tmux_wrapper(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=[],
            prompt_file="/tmp/prompt.md",
            session_dir="/tmp/session",
            exit_code_file="/tmp/exit-code",
            results_file="/tmp/results.json",
        )
        self.assertIn("#!/bin/bash", wrapper)
        self.assertIn("trap _cleanup", wrapper)
        self.assertIn("pi ", wrapper)
        self.assertIn(
            f"python3 {profile._wf_dir}/adapters/pi_session.py /tmp/session /tmp/results.json",
            wrapper,
        )
        self.assertIn('echo $? > "$RESULT_FILE"', wrapper)

    def test_auto_close_extension(self):
        """Auto-close > 0 adds the auto-quit.ts extension."""
        profile = PiProfile()
        wrapper = profile.build_tmux_wrapper(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=[],
            prompt_file="/tmp/prompt.md",
            session_dir="/tmp/session",
            exit_code_file="/tmp/exit-code",
            results_file="/tmp/results.json",
            auto_close=15,
        )
        self.assertIn(f"{profile._ext_dir}/planner/auto-quit.ts", wrapper)
        self.assertIn("export PI_AUTO_CLOSE_DELAY=15", wrapper)

    def test_session_dir_flag(self):
        """Wrapper includes --session-dir for tmux sessions."""
        profile = PiProfile()
        session_dir = "/tmp/session"
        wrapper = profile.build_tmux_wrapper(
            system_prompt_file="/tmp/system.md",
            model=None,
            tools=[],
            prompt_file="/tmp/prompt.md",
            session_dir=session_dir,
            exit_code_file="/tmp/exit-code",
            results_file="/tmp/results.json",
        )
        self.assertIn(f"--session-dir {session_dir}", wrapper)


class TestPiRecordedOutput(unittest.TestCase):
    @unittest.skip("Phase 3: depends on adapter implementation")
    def test_parse_headless_json_mode(self):
        """Recorded pi --mode json stdout parsed into correct results dict."""

    @unittest.skip("Phase 3: depends on adapter implementation")
    def test_parse_session_output(self):
        """Recorded pi session .jsonl parsed into correct results dict."""


if __name__ == "__main__":
    unittest.main()
