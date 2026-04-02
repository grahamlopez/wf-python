"""Tests for wflib.completions — shell completion script generation, dynamic completions."""

import unittest

from wflib.completions import (
    COMPONENT_NAMES,
    FLAGS,
    SUBCOMMANDS,
    complete,
    generate_bash,
    generate_fish,
    generate_zsh,
)


class TestGenerateBash(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_contains_subcommands(self):
        """Generated bash script includes all wf subcommands."""

    @unittest.skip("Phase 4")
    def test_contains_wf_complete_call(self):
        """Generated script calls wf --complete for dynamic completions."""

    @unittest.skip("Phase 4")
    def test_is_valid_bash(self):
        """Generated script is syntactically valid bash."""


class TestGenerateZsh(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_contains_subcommands(self):
        """Generated zsh script includes all wf subcommands."""

    @unittest.skip("Phase 4")
    def test_uses_arguments_style(self):
        """Generated script uses zsh _arguments or _describe."""


class TestGenerateFish(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_contains_complete_commands(self):
        """Generated fish script uses 'complete -c wf' commands."""


class TestDynamicComplete(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_complete_subcommands(self):
        """Bare 'wf' completes to subcommand names."""

    @unittest.skip("Phase 4")
    def test_complete_workflow_names(self):
        """'wf execute' completes to workflow names from docs/workflows/."""

    @unittest.skip("Phase 4")
    def test_complete_template_names(self):
        """'wf template show' completes to template names."""

    @unittest.skip("Phase 4")
    def test_complete_schema_components(self):
        """'wf schema --component' completes to component names."""

    @unittest.skip("Phase 4")
    def test_no_model_completions(self):
        """'wf execute --model' returns no completions (harness-specific)."""


class TestStaticData(unittest.TestCase):
    @unittest.skip("Phase 4")
    def test_subcommands_list(self):
        """SUBCOMMANDS contains all wf subcommands."""

    @unittest.skip("Phase 4")
    def test_flags_per_subcommand(self):
        """FLAGS dict has entries for subcommands that accept flags."""

    @unittest.skip("Phase 4")
    def test_component_names(self):
        """COMPONENT_NAMES lists all schema component names."""


if __name__ == "__main__":
    unittest.main()
