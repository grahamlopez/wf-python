"""Tests for adapters.pi_session — pi session .jsonl file parsing."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from adapters.pi_session import parse


def _write_session_file(session_dir: str, name: str, entries: list[dict]) -> str:
    path = os.path.join(session_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return path


def _message_entry(
    role: str,
    content: list[dict],
    *,
    usage: dict | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> dict:
    message = {"role": role, "content": content}
    if usage is not None:
        message["usage"] = usage
    if model is not None:
        message["model"] = model
    if provider is not None:
        message["provider"] = provider
    return {"type": "message", "message": message}


class TestPiSessionParse(unittest.TestCase):
    def test_parse_session_file(self):
        """Parses a pi session .jsonl file into results dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = os.path.join(tmpdir, "results.json")
            expected = {
                "exitCode": 0,
                "messages": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "From results"}],
                    }
                ],
                "usage": {
                    "input": 3,
                    "output": 1,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "cost": 0.01,
                    "turns": 1,
                },
                "model": "stored-model",
                "provider": "stored-provider",
            }
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(expected, f)

            self.assertEqual(parse(tmpdir, results_file), expected)

            os.remove(results_file)
            old_entries = [
                _message_entry(
                    "assistant",
                    [{"type": "text", "text": "Old response"}],
                    model="old-model",
                    provider="old-provider",
                )
            ]
            new_entries = [
                _message_entry(
                    "assistant",
                    [{"type": "text", "text": "New response"}],
                    model="pi-model",
                    provider="pi-provider",
                )
            ]
            old_path = _write_session_file(tmpdir, "old.jsonl", old_entries)
            new_path = _write_session_file(tmpdir, "new.jsonl", new_entries)
            os.utime(old_path, (1, 1))
            os.utime(new_path, (2, 2))

            parsed = parse(tmpdir, results_file)
            self.assertEqual(parsed["messages"][0]["content"][0]["text"], "New response")
            self.assertEqual(parsed["model"], "pi-model")
            self.assertEqual(parsed["provider"], "pi-provider")

    def test_extracts_messages(self):
        """Messages are extracted from the session log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                _message_entry(
                    "user",
                    [{"type": "text", "text": "Hello"}],
                ),
                {"type": "event", "detail": "ignored"},
                _message_entry(
                    "assistant",
                    [{"type": "text", "text": "Hi there"}],
                ),
            ]
            _write_session_file(tmpdir, "session.jsonl", entries)

            parsed = parse(tmpdir)
            self.assertEqual([m["role"] for m in parsed["messages"]], ["user", "assistant"])
            self.assertEqual(parsed["messages"][0]["content"][0]["text"], "Hello")

    def test_extracts_usage(self):
        """Usage is accumulated across session entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            usage_one = {
                "input": 10,
                "output": 5,
                "cacheRead": 2,
                "cacheWrite": 1,
                "cost": {
                    "input": 0.01,
                    "output": 0.02,
                    "cacheRead": 0.0,
                    "cacheWrite": 0.0,
                    "total": 0.03,
                },
                "turns": 1,
            }
            usage_two = {
                "input": 7,
                "output": 4,
                "cacheRead": 1,
                "cacheWrite": 0,
                "cost": {
                    "input": 0.005,
                    "output": 0.01,
                    "cacheRead": 0.0,
                    "cacheWrite": 0.0,
                    "total": 0.015,
                },
                "turns": 1,
            }
            entries = [
                _message_entry(
                    "assistant",
                    [{"type": "text", "text": "First"}],
                    usage=usage_one,
                ),
                _message_entry(
                    "assistant",
                    [{"type": "text", "text": "Second"}],
                    usage=usage_two,
                ),
            ]
            _write_session_file(tmpdir, "session.jsonl", entries)

            parsed = parse(tmpdir)
            usage = parsed["usage"]
            self.assertEqual(usage["input"], 17)
            self.assertEqual(usage["output"], 9)
            self.assertEqual(usage["cacheRead"], 3)
            self.assertEqual(usage["cacheWrite"], 1)
            self.assertAlmostEqual(usage["cost"], 0.045)
            self.assertEqual(usage["turns"], 2)

    def test_extracts_tool_calls(self):
        """Tool calls in the session are preserved in messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = [
                _message_entry(
                    "assistant",
                    [
                        {
                            "type": "toolCall",
                            "name": "report_result",
                            "arguments": {"summary": "Done", "notes": "All set"},
                        }
                    ],
                )
            ]
            _write_session_file(tmpdir, "session.jsonl", entries)

            parsed = parse(tmpdir)
            content = parsed["messages"][0]["content"]
            self.assertEqual(content[0]["type"], "toolCall")
            self.assertEqual(content[0]["name"], "report_result")
            self.assertEqual(content[0]["arguments"]["summary"], "Done")

    def test_missing_session_dir(self):
        """Handles missing session directory gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_dir = os.path.join(tmpdir, "does-not-exist")
            parsed = parse(missing_dir)
            self.assertEqual(parsed["exitCode"], 1)
            self.assertEqual(parsed["messages"], [])
            self.assertEqual(parsed["usage"], {
                "input": 0,
                "output": 0,
                "cacheRead": 0,
                "cacheWrite": 0,
                "cost": 0.0,
                "turns": 0,
            })


if __name__ == "__main__":
    unittest.main()
