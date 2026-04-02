"""Tests for wflib.help — topic lookup, prefix matching, content checks."""

import unittest

from wflib.help import TOPIC_MAP, TOPICS, get_help, help_command


class TestGetHelp(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_no_topic_returns_full_dump(self):
        """get_help(None) returns the full reference (~1200 lines)."""

    @unittest.skip("Phase 4")
    def test_specific_topic(self):
        """get_help('execute') returns execute topic help."""

    @unittest.skip("Phase 4")
    def test_prefix_matching(self):
        """get_help('exec') resolves to 'execute'."""

    @unittest.skip("Phase 4")
    def test_unknown_topic_does_not_raise(self):
        """get_help('nonexistent') returns a helpful message, not an error."""

    @unittest.skip("Phase 4")
    def test_topics_list(self):
        """get_help('topics') returns a list of available topics."""


class TestHelpContent(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_execute_mentions_concurrency(self):
        """Execute topic mentions --concurrency flag."""

    @unittest.skip("Phase 4")
    def test_init_mentions_set_flag(self):
        """Init topic mentions --set flag."""

    @unittest.skip("Phase 4")
    def test_models_topic_explains_resolution(self):
        """Models topic explains the two-stage resolution."""

    @unittest.skip("Phase 4")
    def test_recovery_topic_has_commands(self):
        """Recovery topic includes concrete investigation commands."""

    @unittest.skip("Phase 4")
    def test_debugging_topic_has_commands(self):
        """Debugging topic includes copy-pasteable shell commands."""


class TestTopicRegistry(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_topics_list_not_empty(self):
        """TOPICS list contains entries."""

    @unittest.skip("Phase 4")
    def test_topic_map_matches_topics(self):
        """Every entry in TOPICS is in TOPIC_MAP."""


if __name__ == "__main__":
    unittest.main()
