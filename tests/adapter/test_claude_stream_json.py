"""Tests for adapters.claude_stream_json — Claude Code stream-json output parsing."""

import unittest

from adapters.claude_stream_json import parse


class TestClaudeStreamJsonParse(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_parse_basic_output(self):
        """Parses a basic stream-json output with messages and usage."""

    @unittest.skip("Phase 3")
    def test_extracts_tool_use(self):
        """tool_use events are converted to toolCall content blocks."""

    @unittest.skip("Phase 3")
    def test_extracts_usage(self):
        """Usage fields are extracted from the stream."""

    @unittest.skip("Phase 3")
    def test_extracts_model(self):
        """Model is extracted from the output."""

    @unittest.skip("Phase 3")
    def test_empty_output(self):
        """Empty stdout returns a default/error results dict."""

    @unittest.skip("Phase 3")
    def test_malformed_json_line(self):
        """Handles malformed JSON lines gracefully."""


if __name__ == "__main__":
    unittest.main()
