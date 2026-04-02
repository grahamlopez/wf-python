"""Configuration loading, merging, and resolution.

Implements the 5-level precedence chain:
    CLI flags > init-time overrides > project config > user config > baked-in defaults
"""

from __future__ import annotations

import tomllib

from wflib.types import WorkflowConfig

USER_CONFIG_PATH = "~/.config/wf/config.toml"
PROJECT_CONFIG_NAME = ".wf/config.toml"

# --- Baked-in defaults ---

DEFAULTS = WorkflowConfig()  # all dataclass defaults


# --- Loading ---

def load_user_config() -> dict:
    """Load ~/.config/wf/config.toml. Returns raw dict.
    Returns {} if file doesn't exist. Raises on parse error.
    """
    raise NotImplementedError("load_user_config: not yet implemented")


def load_project_config(cwd: str) -> dict:
    """Load .wf/config.toml from the project root.
    Walks up from cwd to find the repo root (looks for .git/).
    Returns {} if file doesn't exist. Raises on parse error.
    """
    raise NotImplementedError("load_project_config: not yet implemented")


def parse_overrides(overrides: list[str]) -> dict:
    """Parse --set key=value flags into a nested dict.
    Supports dotted keys: 'model.plan=claude-opus-4' becomes
    {'model': {'plan': 'claude-opus-4'}}.
    Raises ValueError on malformed input.
    """
    raise NotImplementedError("parse_overrides: not yet implemented")


# --- Merging ---

def merge_configs(*layers: dict) -> dict:
    """Deep-merge config dicts, left to right (last wins).
    Only merges dicts - scalars and lists are replaced, not merged.
    """
    raise NotImplementedError("merge_configs: not yet implemented")


# --- Resolution ---

def resolve_config(
    cwd: str,
    overrides: list[str] | None = None,
) -> WorkflowConfig:
    """Build a fully-resolved WorkflowConfig by merging all levels:
    baked-in defaults < user config < project config < overrides.
    This is called once at wf init time. The result is stored in the record.

    Raises ConfigError on any validation failure.
    """
    raise NotImplementedError("resolve_config: not yet implemented")


def apply_cli_overrides(
    config: WorkflowConfig,
    **kwargs,
) -> WorkflowConfig:
    """Apply ephemeral CLI flag overrides to a config snapshot.
    Returns a new WorkflowConfig (does not mutate the input).
    """
    raise NotImplementedError("apply_cli_overrides: not yet implemented")


def config_to_dict(config: WorkflowConfig) -> dict:
    """Serialize a WorkflowConfig to a dict for JSON storage in the record."""
    raise NotImplementedError("config_to_dict: not yet implemented")


def config_from_dict(data: dict) -> WorkflowConfig:
    """Deserialize a WorkflowConfig from a record's workflow.config dict."""
    raise NotImplementedError("config_from_dict: not yet implemented")


# --- Inspection ---

def show_resolved(config: WorkflowConfig) -> str:
    """Format a resolved config for display (wf config list)."""
    raise NotImplementedError("show_resolved: not yet implemented")


def show_with_origins(
    cwd: str,
    overrides: list[str] | None = None,
) -> str:
    """Format the config showing each value's source level.
    e.g. 'model.plan = claude-sonnet-4-5  (project)'
    """
    raise NotImplementedError("show_with_origins: not yet implemented")


# --- Editing (for wf config set) ---

def set_config_value(path: str, key: str, value: str, scope: str = "user") -> None:
    """Set a value in a config file. scope is 'user' or 'project'.
    Creates the file if it doesn't exist.
    """
    raise NotImplementedError("set_config_value: not yet implemented")
