"""Tests for adapters.claude_stream_json — Claude Code stream-json output parsing."""

import json
import unittest

from adapters.claude_stream_json import parse


def _usage(**overrides: int | float) -> dict:
    base = {
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
        "cost": 0.0,
        "turns": 0,
    }
    base.update(overrides)
    return base


class TestClaudeStreamJsonParse(unittest.TestCase):
    def test_parse_basic_output(self):
        """Parses a basic stream-json output with messages and usage."""
        stdout = "\n".join([
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": []}}),
            json.dumps({"type": "text", "text": "Hello "}),
            json.dumps({"type": "text", "text": "world"}),
            json.dumps({
                "type": "result",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input_tokens": 12,
                    "output_tokens": 5,
                    "cache_read_input_tokens": 2,
                    "cache_creation_input_tokens": 3,
                },
            }),
        ])

        result = parse(stdout)

        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(
            result["messages"],
            [{
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello "},
                    {"type": "text", "text": "world"},
                ],
            }],
        )
        self.assertEqual(
            result["usage"],
            _usage(input=12, output=5, cacheRead=2, cacheWrite=3, turns=1),
        )
        self.assertEqual(result["model"], "claude-sonnet-4-5")

    def test_extracts_tool_use(self):
        """tool_use events are converted to toolCall content blocks."""
        stdout = "\n".join([
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": []}}),
            json.dumps({
                "type": "tool_use",
                "name": "report_result",
                "input": {"summary": "Done", "notes": ""},
            }),
            json.dumps({"type": "result", "model": "claude-haiku-4-5", "usage": {}}),
        ])

        result = parse(stdout)

        self.assertEqual(
            result["messages"],
            [{
                "role": "assistant",
                "content": [
                    {
                        "type": "toolCall",
                        "name": "report_result",
                        "arguments": {"summary": "Done", "notes": ""},
                    }
                ],
            }],
        )

    def test_extracts_usage(self):
        """Usage fields are extracted from the stream."""
        stdout = "\n".join([
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": []}}),
            json.dumps({"type": "text", "text": "Usage please"}),
            json.dumps({
                "type": "result",
                "model": "claude-sonnet-4-5",
                "usage": {
                    "input_tokens": 40,
                    "output_tokens": 10,
                    "cache_read_input_tokens": 7,
                    "cache_creation_input_tokens": 9,
                },
            }),
        ])

        result = parse(stdout)

        self.assertEqual(
            result["usage"],
            _usage(input=40, output=10, cacheRead=7, cacheWrite=9, turns=1),
        )

    def test_extracts_model(self):
        """Model is extracted from the output."""
        stdout = "\n".join([
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": []}}),
            json.dumps({"type": "text", "text": "Model test"}),
            json.dumps({
                "type": "result",
                "model": "claude-opus-4",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }),
        ])

        result = parse(stdout)

        self.assertEqual(result["model"], "claude-opus-4")

    def test_empty_output(self):
        """Empty stdout returns a default/error results dict."""
        result = parse("")

        self.assertEqual(result["exitCode"], 1)
        self.assertEqual(result["messages"], [])
        self.assertEqual(result["usage"], _usage())
        self.assertIsNone(result["model"])

    def test_malformed_json_line(self):
        """Handles malformed JSON lines gracefully."""
        stdout = "\n".join([
            "{not json}",
            json.dumps({"type": "assistant", "message": {"role": "assistant", "content": []}}),
            json.dumps({"type": "text", "text": "Recovered"}),
            json.dumps({"type": "result", "model": "claude-sonnet-4-5", "usage": {}}),
        ])

        result = parse(stdout)

        self.assertEqual(
            result["messages"],
            [{
                "role": "assistant",
                "content": [{"type": "text", "text": "Recovered"}],
            }],
        )


if __name__ == "__main__":
    unittest.main()
