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
    def test_parse_headless_json_mode(self):
        """Recorded pi --mode json stdout parsed into correct results dict."""
        import json

        profile = PiProfile()
        messages = [
            {
                "id": "msg-user-1",
                "role": "user",
                "content": [{"type": "text", "text": "Summarize progress."}],
            },
            {
                "id": "msg-assistant-1",
                "role": "assistant",
                "content": [{"type": "text", "text": "Drafting summary."}],
            },
            {
                "id": "msg-assistant-2",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Done."},
                    {
                        "type": "toolCall",
                        "name": "report_result",
                        "arguments": {"summary": "Summary", "notes": ""},
                    },
                ],
            },
        ]

        stdout = "\n".join(
            json.dumps(event)
            for event in [
                {"type": "session", "id": "session-123"},
                {
                    "type": "message_end",
                    "message": {
                        "id": "msg-user-1",
                        "role": "user",
                        "content": messages[0]["content"],
                    },
                },
                {
                    "type": "message_end",
                    "message": {
                        "id": "msg-assistant-1",
                        "role": "assistant",
                        "model": "pi-sonnet-4.5",
                        "provider": "anthropic",
                        "content": messages[1]["content"],
                        "usage": {
                            "input": 20,
                            "output": 8,
                            "cacheRead": 1,
                            "cacheWrite": 0,
                            "cost": {"total": 0.004},
                        },
                    },
                },
                {
                    "type": "message_end",
                    "message": {
                        "id": "msg-assistant-2",
                        "role": "assistant",
                        "model": "pi-sonnet-4.5",
                        "provider": "anthropic",
                        "content": messages[2]["content"],
                        "usage": {
                            "input": 10,
                            "output": 5,
                            "cacheRead": 2,
                            "cacheWrite": 1,
                            "cost": {"total": 0.003},
                        },
                    },
                },
                {"type": "agent_end", "messages": messages, "exitCode": 0},
            ]
        )

        result = profile.parse_headless_output(stdout)
        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["messages"], messages)
        self.assertEqual(result["model"], "pi-sonnet-4.5")
        self.assertEqual(result["provider"], "anthropic")
        self.assertEqual(
            result["usage"],
            {
                "input": 30,
                "output": 13,
                "cacheRead": 3,
                "cacheWrite": 1,
                "cost": 0.007,
                "turns": 2,
            },
        )

    def test_parse_session_output(self):
        """Recorded pi session .jsonl parsed into correct results dict."""
        import json
        import os
        import tempfile

        profile = PiProfile()
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = os.path.join(tmpdir, "session.jsonl")
            results_file = os.path.join(tmpdir, "results.json")
            entries = [
                {
                    "type": "message",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": "Status?"}],
                    },
                },
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Working."}],
                        "usage": {
                            "input": 12,
                            "output": 4,
                            "cacheRead": 1,
                            "cacheWrite": 0,
                            "cost": {"total": 0.002},
                            "turns": 1,
                        },
                        "model": "pi-haiku-4.5",
                        "provider": "anthropic",
                    },
                },
                {
                    "type": "message",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Ready."}],
                        "usage": {
                            "input": 8,
                            "output": 3,
                            "cacheRead": 0,
                            "cacheWrite": 1,
                            "cost": {"total": 0.0015},
                            "turns": 1,
                        },
                        "model": "pi-haiku-4.5",
                        "provider": "anthropic",
                    },
                },
            ]
            with open(session_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")

            result = profile.parse_session_output(tmpdir, results_file)
            self.assertEqual(result["exitCode"], 0)
            self.assertEqual([m["role"] for m in result["messages"]], [
                "user",
                "assistant",
                "assistant",
            ])
            self.assertEqual(result["messages"][1]["content"][0]["text"], "Working.")
            self.assertEqual(result["model"], "pi-haiku-4.5")
            self.assertEqual(result["provider"], "anthropic")
            self.assertEqual(
                result["usage"],
                {
                    "input": 20,
                    "output": 7,
                    "cacheRead": 1,
                    "cacheWrite": 1,
                    "cost": 0.0035,
                    "turns": 2,
                },
            )


if __name__ == "__main__":
    unittest.main()
