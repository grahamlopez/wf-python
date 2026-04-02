"""Tests for wflib.templates — frontmatter parsing, variable substitution, discovery."""

import unittest

from wflib.templates import (
    Template,
    list_templates,
    load_template,
    parse_frontmatter,
    render_template,
)


class TestParseFrontmatter(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_with_frontmatter(self):
        """Parses YAML frontmatter and returns (metadata, body)."""

    @unittest.skip("Phase 1")
    def test_without_frontmatter(self):
        """Returns ({}, full content) when no frontmatter delimiters."""

    @unittest.skip("Phase 1")
    def test_empty_frontmatter(self):
        """Handles empty frontmatter (--- followed immediately by ---)."""

    @unittest.skip("Phase 1")
    def test_description_extraction(self):
        """Extracts 'description' key from frontmatter."""


class TestRenderTemplate(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_positional_args(self):
        """$1, $2 replaced by positional args."""

    @unittest.skip("Phase 1")
    def test_all_args(self):
        """$@ replaced by all args joined with spaces."""

    @unittest.skip("Phase 1")
    def test_missing_arg_becomes_empty(self):
        """$2 becomes empty string if only 1 arg provided."""

    @unittest.skip("Phase 1")
    def test_frontmatter_stripped(self):
        """Rendered output does not include frontmatter."""


class TestListTemplates(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_discovers_shipped_templates(self):
        """Finds templates in the shipped templates/ directory."""

    @unittest.skip("Phase 1")
    def test_project_overrides_shipped(self):
        """Project-level template with same name overrides shipped default."""

    @unittest.skip("Phase 1")
    def test_sorted_by_name(self):
        """Returned list is sorted alphabetically by name."""


class TestLoadTemplate(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_loads_by_name(self):
        """Loads a template by name (without .md extension)."""

    @unittest.skip("Phase 1")
    def test_not_found_raises(self):
        """Raises FileNotFoundError for unknown template name."""


if __name__ == "__main__":
    unittest.main()
