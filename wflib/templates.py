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


def _load_from_file(filepath: str, source: str) -> Template:
    """Load a Template from a .md file on disk."""
    p = Path(filepath)
    content = p.read_text()
    meta, body = parse_frontmatter(content)
    return Template(
        name=p.stem,
        description=meta.get("description", ""),
        body=body,
        source=source,
        path=str(p.resolve()),
    )


def list_templates(cwd: str) -> list[Template]:
    """Discover templates from both shipped and project directories.
    Project-level overrides shipped defaults with the same name.
    Returns sorted by name.
    """
    templates: dict[str, Template] = {}
    # Shipped first
    shipped = Path(SHIPPED_DIR)
    if shipped.is_dir():
        for f in shipped.iterdir():
            if f.suffix == ".md":
                t = _load_from_file(str(f), "shipped")
                templates[t.name] = t
    # Project overrides
    project = Path(cwd) / PROJECT_DIR
    if project.is_dir():
        for f in project.iterdir():
            if f.suffix == ".md":
                t = _load_from_file(str(f), "project")
                templates[t.name] = t
    return sorted(templates.values(), key=lambda t: t.name)


def load_template(name: str, cwd: str) -> Template:
    """Load a template by name. Project-level first, then shipped.
    Raises FileNotFoundError if not found in either location.
    """
    # Check project dir first
    project_file = Path(cwd) / PROJECT_DIR / f"{name}.md"
    if project_file.is_file():
        return _load_from_file(str(project_file), "project")
    # Then shipped
    shipped_file = Path(SHIPPED_DIR) / f"{name}.md"
    if shipped_file.is_file():
        return _load_from_file(str(shipped_file), "shipped")
    raise FileNotFoundError(f"Template not found: {name}")


def render_template(template: Template, args: list[str]) -> str:
    """Render a template with argument substitution.
    $1, $2, ... replaced by positional args (empty string if missing).
    $@ replaced by all args joined with spaces.
    Returns the rendered body (frontmatter stripped).
    """
    import re
    body = template.body
    # Replace $@ first (before positional, since $@ is distinct)
    body = body.replace("$@", " ".join(args))
    # Replace $1, $2, ... with positional args (highest first to avoid $1 matching in $10)
    def _replace_positional(m: re.Match) -> str:
        idx = int(m.group(1)) - 1
        return args[idx] if idx < len(args) else ""
    body = re.sub(r"\$(\d+)", _replace_positional, body)
    return body


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (metadata, body).
    If no frontmatter, returns ({}, full content).
    """
    if not content.startswith('---\n'):
        return {}, content
    end = content.find('\n---\n', 4)
    if end == -1:
        return {}, content
    meta = {}
    for line in content[4:end].split('\n'):
        k, _, v = line.partition(':')
        if v:
            meta[k.strip()] = v.strip()
    return meta, content[end + 5:]
