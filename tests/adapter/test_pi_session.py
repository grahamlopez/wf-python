"""Tests for adapters.pi_session — pi session .jsonl file parsing."""

import unittest

from adapters.pi_session import parse


class TestPiSessionParse(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_parse_session_file(self):
        """Parses a pi session .jsonl file into results dict."""

    @unittest.skip("Phase 3")
    def test_extracts_messages(self):
        """Messages are extracted from the session log."""

    @unittest.skip("Phase 3")
    def test_extracts_usage(self):
        """Usage is accumulated across session entries."""

    @unittest.skip("Phase 3")
    def test_extracts_tool_calls(self):
        """Tool calls in the session are preserved in messages."""

    @unittest.skip("Phase 3")
    def test_missing_session_dir(self):
        """Handles missing session directory gracefully."""


if __name__ == "__main__":
    unittest.main()
