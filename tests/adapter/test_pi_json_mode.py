"""Tests for adapters.pi_json_mode — pi --mode json stdout parsing."""

import unittest

from adapters.pi_json_mode import parse


class TestPiJsonModeParse(unittest.TestCase):
    @unittest.skip("Phase 3")
    def test_parse_basic_output(self):
        """Parses a basic pi JSON mode output with messages and usage."""

    @unittest.skip("Phase 3")
    def test_extracts_tool_calls(self):
        """Tool call content blocks are preserved in messages."""

    @unittest.skip("Phase 3")
    def test_extracts_usage(self):
        """Usage fields (input, output, cacheRead, etc.) are extracted."""

    @unittest.skip("Phase 3")
    def test_extracts_model_and_provider(self):
        """Model and provider are extracted from the output."""

    @unittest.skip("Phase 3")
    def test_empty_output(self):
        """Empty stdout returns a default/error results dict."""

    @unittest.skip("Phase 3")
    def test_malformed_json_line(self):
        """Handles malformed JSON lines gracefully."""


if __name__ == "__main__":
    unittest.main()
