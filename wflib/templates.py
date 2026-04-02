"""Reusable prompt fragments with variable substitution.

Harness-agnostic - any wrapper can discover and render them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SHIPPED_DIR = str(Path(__file__).parent.parent / "templates")
PROJECT_DIR = "docs/workflows/templates"


@dataclass
class Template:
    name: str                              # filename without .md
    description: str                       # from YAML frontmatter
    body: str                              # raw body with placeholders
    source: str                            # "shipped" | "project"
    path: str                              # absolute path to the file


def list_templates(cwd: str) -> list[Template]:
    """Discover templates from both shipped and project directories.
    Project-level overrides shipped defaults with the same name.
    Returns sorted by name.
    """
    raise NotImplementedError("list_templates: not yet implemented")


def load_template(name: str, cwd: str) -> Template:
    """Load a template by name. Project-level first, then shipped.
    Raises FileNotFoundError if not found in either location.
    """
    raise NotImplementedError("load_template: not yet implemented")


def render_template(template: Template, args: list[str]) -> str:
    """Render a template with argument substitution.
    $1, $2, ... replaced by positional args (empty string if missing).
    $@ replaced by all args joined with spaces.
    Returns the rendered body (frontmatter stripped).
    """
    raise NotImplementedError("render_template: not yet implemented")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (metadata, body).
    If no frontmatter, returns ({}, full content).
    """
    raise NotImplementedError("parse_frontmatter: not yet implemented")
