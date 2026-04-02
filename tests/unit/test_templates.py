"""Tests for wflib.templates — frontmatter parsing, variable substitution, discovery."""

import os
import tempfile
import unittest

from wflib.templates import (
    SHIPPED_DIR,
    Template,
    list_templates,
    load_template,
    parse_frontmatter,
    render_template,
)


class TestParseFrontmatter(unittest.TestCase):
    def test_with_frontmatter(self):
        """Parses YAML frontmatter and returns (metadata, body)."""
        content = "---\ndescription: A test template\nauthor: tester\n---\nHello $1\n"
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta, {"description": "A test template", "author": "tester"})
        self.assertEqual(body, "Hello $1\n")

    def test_without_frontmatter(self):
        """Returns ({}, full content) when no frontmatter delimiters."""
        content = "Just plain text\nNo frontmatter here."
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta, {})
        self.assertEqual(body, content)

    def test_empty_frontmatter(self):
        """Handles empty frontmatter (--- followed immediately by ---) — treated as no frontmatter."""
        # parse_frontmatter starts searching for '\n---\n' at offset 4 (after the
        # opening '---\n'). In '---\n---\n...', the potential match starts at
        # offset 3 which is before the search start, so no closing delimiter is
        # found and the content is returned as-is.
        content = "---\n---\nBody text here."
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta, {})
        self.assertEqual(body, content)

    def test_frontmatter_with_empty_lines(self):
        """Frontmatter with only blank lines still parses (keys ignored if no colon value)."""
        content = "---\n\n---\nBody text here."
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta, {})
        self.assertEqual(body, "Body text here.")

    def test_description_extraction(self):
        """Extracts 'description' key from frontmatter."""
        content = "---\ndescription: Quality check a recent implementation\n---\nBody"
        meta, body = parse_frontmatter(content)
        self.assertEqual(meta["description"], "Quality check a recent implementation")
        self.assertEqual(body, "Body")


class TestRenderTemplate(unittest.TestCase):
    def test_positional_args(self):
        """$1, $2 replaced by positional args."""
        t = Template(name="test", description="", body="Hello $1, welcome to $2!", source="shipped", path="/tmp/test.md")
        result = render_template(t, ["Alice", "Wonderland"])
        self.assertEqual(result, "Hello Alice, welcome to Wonderland!")

    def test_all_args(self):
        """$@ replaced by all args joined with spaces."""
        t = Template(name="test", description="", body="Args: $@", source="shipped", path="/tmp/test.md")
        result = render_template(t, ["one", "two", "three"])
        self.assertEqual(result, "Args: one two three")

    def test_missing_arg_becomes_empty(self):
        """$2 becomes empty string if only 1 arg provided."""
        t = Template(name="test", description="", body="A=$1 B=$2 C=$3", source="shipped", path="/tmp/test.md")
        result = render_template(t, ["first"])
        self.assertEqual(result, "A=first B= C=")

    def test_frontmatter_stripped(self):
        """Rendered output does not include frontmatter."""
        # Template body should already have frontmatter stripped (by load_template/parse_frontmatter)
        # But verify the contract: render_template uses template.body which is post-frontmatter
        content = "---\ndescription: test\n---\nHello $1"
        meta, body = parse_frontmatter(content)
        t = Template(name="test", description=meta.get("description", ""), body=body, source="shipped", path="/tmp/test.md")
        result = render_template(t, ["world"])
        self.assertEqual(result, "Hello world")
        self.assertNotIn("---", result)

    def test_no_args(self):
        """$@ with no args becomes empty string."""
        t = Template(name="test", description="", body="Before $@ after", source="shipped", path="/tmp/test.md")
        result = render_template(t, [])
        self.assertEqual(result, "Before  after")

    def test_dollar_at_and_positional(self):
        """Both $@ and positional $1 work together."""
        t = Template(name="test", description="", body="First: $1\nAll: $@", source="shipped", path="/tmp/test.md")
        result = render_template(t, ["alpha", "beta"])
        self.assertEqual(result, "First: alpha\nAll: alpha beta")


class TestListTemplates(unittest.TestCase):
    def test_discovers_shipped_templates(self):
        """Finds templates in the shipped templates/ directory."""
        # Use a temp dir with no project templates so we get only shipped ones
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = list_templates(tmpdir)
            names = [t.name for t in templates]
            self.assertIn("brainstorm", names)
            self.assertIn("check-implementation", names)
            self.assertIn("execute-plan-step", names)
            self.assertIn("write-plan-to-file", names)
            for t in templates:
                self.assertEqual(t.source, "shipped")

    def test_project_overrides_shipped(self):
        """Project-level template with same name overrides shipped default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir = os.path.join(tmpdir, "docs", "workflows", "templates")
            os.makedirs(proj_dir)
            with open(os.path.join(proj_dir, "brainstorm.md"), "w") as f:
                f.write("---\ndescription: Custom brainstorm\n---\nCustom body $1\n")
            templates = list_templates(tmpdir)
            brainstorm = [t for t in templates if t.name == "brainstorm"][0]
            self.assertEqual(brainstorm.source, "project")
            self.assertEqual(brainstorm.description, "Custom brainstorm")
            self.assertIn("Custom body", brainstorm.body)

    def test_sorted_by_name(self):
        """Returned list is sorted alphabetically by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = list_templates(tmpdir)
            names = [t.name for t in templates]
            self.assertEqual(names, sorted(names))

    def test_project_adds_new_template(self):
        """Project-level templates that don't exist in shipped are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir = os.path.join(tmpdir, "docs", "workflows", "templates")
            os.makedirs(proj_dir)
            with open(os.path.join(proj_dir, "custom-prompt.md"), "w") as f:
                f.write("---\ndescription: My custom prompt\n---\nDo the thing.\n")
            templates = list_templates(tmpdir)
            names = [t.name for t in templates]
            self.assertIn("custom-prompt", names)
            custom = [t for t in templates if t.name == "custom-prompt"][0]
            self.assertEqual(custom.source, "project")


class TestLoadTemplate(unittest.TestCase):
    def test_loads_by_name(self):
        """Loads a template by name (without .md extension)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            t = load_template("brainstorm", tmpdir)
            self.assertEqual(t.name, "brainstorm")
            self.assertEqual(t.source, "shipped")
            self.assertTrue(len(t.body) > 0)

    def test_not_found_raises(self):
        """Raises FileNotFoundError for unknown template name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                load_template("nonexistent-template-xyz", tmpdir)

    def test_project_overrides_shipped(self):
        """Project-level template is loaded instead of shipped when both exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir = os.path.join(tmpdir, "docs", "workflows", "templates")
            os.makedirs(proj_dir)
            with open(os.path.join(proj_dir, "brainstorm.md"), "w") as f:
                f.write("---\ndescription: Overridden\n---\nProject body\n")
            t = load_template("brainstorm", tmpdir)
            self.assertEqual(t.source, "project")
            self.assertEqual(t.description, "Overridden")
            self.assertEqual(t.body, "Project body\n")

    def test_loads_project_only_template(self):
        """Loads a template that exists only in the project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proj_dir = os.path.join(tmpdir, "docs", "workflows", "templates")
            os.makedirs(proj_dir)
            with open(os.path.join(proj_dir, "my-custom.md"), "w") as f:
                f.write("Custom template body\n")
            t = load_template("my-custom", tmpdir)
            self.assertEqual(t.name, "my-custom")
            self.assertEqual(t.source, "project")
            self.assertEqual(t.description, "")


if __name__ == "__main__":
    unittest.main()
