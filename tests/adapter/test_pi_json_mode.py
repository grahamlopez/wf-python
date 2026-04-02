"""Tests for adapters.pi_json_mode — pi --mode json stdout parsing."""

import json
import unittest

from adapters.pi_json_mode import parse


def _build_sample_output(*, include_tool_call: bool = True, include_malformed: bool = False) -> str:
    messages = [
        {
            "id": "msg-user-1",
            "role": "user",
            "content": [{"type": "text", "text": "Add structured logging."}],
        },
        {
            "id": "msg-assistant-1",
            "role": "assistant",
            "content": [{"type": "text", "text": "Got it."}],
        },
        {
            "id": "msg-assistant-2",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "All set."},
                {
                    "type": "toolCall",
                    "name": "report_result",
                    "arguments": {"summary": "Added logging", "notes": ""},
                },
            ]
            if include_tool_call
            else [{"type": "text", "text": "All set."}],
        },
    ]

    events = [
        {"type": "session", "id": "session-1"},
        {
            "type": "message_end",
            "message": {
                "id": "msg-user-1",
                "role": "user",
                "content": [{"type": "text", "text": "Add structured logging."}],
            },
        },
        {
            "type": "message_end",
            "message": {
                "id": "msg-assistant-1",
                "role": "assistant",
                "model": "pi-sonnet-4.5",
                "provider": "anthropic",
                "content": [{"type": "text", "text": "Got it."}],
                "usage": {
                    "input": 120,
                    "output": 30,
                    "cacheRead": 5,
                    "cacheWrite": 2,
                    "cost": {
                        "input": 0.001,
                        "output": 0.002,
                        "cacheRead": 0.0,
                        "cacheWrite": 0.0,
                        "total": 0.003,
                    },
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
                    "input": 80,
                    "output": 20,
                    "cacheRead": 3,
                    "cacheWrite": 1,
                    "cost": {
                        "input": 0.0006,
                        "output": 0.0004,
                        "cacheRead": 0.0,
                        "cacheWrite": 0.0,
                        "total": 0.001,
                    },
                },
            },
        },
        {"type": "agent_end", "messages": messages, "exitCode": 0},
    ]

    lines = [json.dumps(event) for event in events]
    if include_malformed:
        lines.insert(2, "{not-json}")
    return "\n".join(lines)


class TestPiJsonModeParse(unittest.TestCase):
    def test_parse_basic_output(self):
        """Parses a basic pi JSON mode output with messages and usage."""
        stdout = _build_sample_output(include_tool_call=False)
        result = parse(stdout)
        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(len(result["messages"]), 3)
        self.assertEqual(result["messages"][0]["role"], "user")

    def test_extracts_tool_calls(self):
        """Tool call content blocks are preserved in messages."""
        stdout = _build_sample_output(include_tool_call=True)
        result = parse(stdout)
        tool_blocks = [
            block
            for block in result["messages"][2]["content"]
            if block.get("type") == "toolCall"
        ]
        self.assertEqual(len(tool_blocks), 1)
        self.assertEqual(tool_blocks[0]["name"], "report_result")

    def test_extracts_usage(self):
        """Usage fields (input, output, cacheRead, etc.) are extracted."""
        stdout = _build_sample_output()
        result = parse(stdout)
        self.assertEqual(
            {
                "input": result["usage"]["input"],
                "output": result["usage"]["output"],
                "cacheRead": result["usage"]["cacheRead"],
                "cacheWrite": result["usage"]["cacheWrite"],
                "turns": result["usage"]["turns"],
            },
            {
                "input": 200,
                "output": 50,
                "cacheRead": 8,
                "cacheWrite": 3,
                "turns": 2,
            },
        )
        self.assertAlmostEqual(result["usage"]["cost"], 0.004, places=6)

    def test_extracts_model_and_provider(self):
        """Model and provider are extracted from the output."""
        stdout = _build_sample_output()
        result = parse(stdout)
        self.assertEqual(result["model"], "pi-sonnet-4.5")
        self.assertEqual(result["provider"], "anthropic")

    def test_empty_output(self):
        """Empty stdout returns a default/error results dict."""
        result = parse("")
        self.assertEqual(
            result,
            {
                "exitCode": 1,
                "messages": [],
                "usage": {
                    "input": 0,
                    "output": 0,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "cost": 0,
                    "turns": 0,
                },
                "model": None,
                "provider": None,
            },
        )

    def test_malformed_json_line(self):
        """Handles malformed JSON lines gracefully."""
        stdout = _build_sample_output(include_malformed=True)
        result = parse(stdout)
        self.assertEqual(result["usage"]["turns"], 2)
        self.assertEqual(result["messages"][0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
