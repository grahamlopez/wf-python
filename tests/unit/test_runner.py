"""Tests for runner result extraction helpers."""

import json
import os
import tempfile
import unittest

from wflib.runner import (
    _read_agent_results,
    extract_report_result,
    extract_summary_fallback,
)


class TestExtractReportResult(unittest.TestCase):
    def test_extract_report_result_found(self):
        """extract_report_result wraps report_result tool call in ReportResult."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "Done"},
                {"type": "toolCall", "name": "report_result", "arguments": {
                    "summary": "Implemented feature",
                    "notes": "No issues",
                }},
            ]}
        ]
        result = extract_report_result(messages)
        self.assertIsNotNone(result)
        self.assertEqual(result.summary, "Implemented feature")
        self.assertEqual(result.notes, "No issues")

    def test_extract_report_result_missing(self):
        """extract_report_result returns None when tool call missing."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "Just text"}
            ]}
        ]
        self.assertIsNone(extract_report_result(messages))


class TestExtractSummaryFallback(unittest.TestCase):
    def test_extract_summary_fallback_last_500_chars(self):
        """extract_summary_fallback returns last 500 chars of assistant text."""
        long_text = "a" * 600
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": long_text}
            ]}
        ]
        result = extract_summary_fallback(messages)
        self.assertEqual(result, long_text[-500:])

    def test_extract_summary_fallback_empty_messages(self):
        """extract_summary_fallback returns empty string with no assistant text."""
        self.assertEqual(extract_summary_fallback([]), "")


class TestReadAgentResults(unittest.TestCase):
    def test_read_agent_results_valid_report_result(self):
        """_read_agent_results parses report_result and preserves messages."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "toolCall", "name": "report_result", "arguments": {
                    "summary": "Did the thing",
                    "notes": "All good",
                }}
            ]}
        ]
        usage = {
            "input": 10,
            "output": 5,
            "cacheRead": 2,
            "cacheWrite": 1,
            "cost": 0.12,
            "turns": 1,
        }
        data = {
            "exitCode": 0,
            "messages": messages,
            "usage": usage,
            "model": "test-model",
            "provider": "test-provider",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "results.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)

            result = _read_agent_results(path)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.summary, "Did the thing")
        self.assertEqual(result.notes, "All good")
        self.assertEqual(result.model, "test-model")
        self.assertEqual(result.provider, "test-provider")
        self.assertEqual(result.messages, messages)
        self.assertEqual(result.usage.input, 10)
        self.assertEqual(result.usage.output, 5)
        self.assertEqual(result.usage.cache_read, 2)
        self.assertEqual(result.usage.cache_write, 1)
        self.assertEqual(result.usage.cost, 0.12)
        self.assertEqual(result.usage.turns, 1)

    def test_read_agent_results_fallback_summary(self):
        """_read_agent_results falls back to assistant text when tool call missing."""
        messages = [
            {"role": "assistant", "content": [
                {"type": "text", "text": "Fallback summary"}
            ]}
        ]
        data = {"exitCode": 0, "messages": messages, "usage": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "results.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)

            result = _read_agent_results(path)

        self.assertEqual(result.summary, "Fallback summary")
        self.assertEqual(result.notes, "")

    def test_read_agent_results_empty_messages(self):
        """_read_agent_results returns empty summary when messages are empty."""
        data = {"exitCode": 0, "messages": [], "usage": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "results.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)

            result = _read_agent_results(path)

        self.assertEqual(result.summary, "")
        self.assertEqual(result.notes, "")
        self.assertEqual(result.messages, [])

    def test_read_agent_results_missing_file(self):
        """_read_agent_results returns error AgentResult when file missing."""
        result = _read_agent_results("/tmp/does-not-exist-results.json")
        self.assertIsNotNone(result.error)
        self.assertIn("Results file not found", result.error)

    def test_read_agent_results_malformed_json(self):
        """_read_agent_results returns error AgentResult on malformed JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "results.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{this is not json}")

            result = _read_agent_results(path)

        self.assertIsNotNone(result.error)
        self.assertIn("Malformed JSON", result.error)


if __name__ == "__main__":
    unittest.main()
