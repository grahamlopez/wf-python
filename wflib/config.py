"""Configuration loading, merging, and resolution.

Implements the 5-level precedence chain:
    CLI flags > init-time overrides > project config > user config > baked-in defaults
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import fields

from wflib.types import (
    AgentConfig,
    AutomationConfig,
    AutomationLevel,
    ExecuteConfig,
    ModelConfig,
    ModelsConfig,
    UIConfig,
    WorkflowConfig,
    _dataclass_to_dict,
    _dict_to_dataclass,
)

USER_CONFIG_PATH = "~/.config/wf/config.toml"
PROJECT_CONFIG_NAME = ".wf/config.toml"

# --- Baked-in defaults ---

DEFAULTS = WorkflowConfig()  # all dataclass defaults


# --- Exception ---

class ConfigError(Exception):
    """Raised on config validation failures (unknown keys, invalid values, malformed TOML)."""
    pass


# --- Known config structure for validation ---

# Map section name -> set of valid keys (None = dynamic keys allowed)
_KNOWN_SECTIONS: dict[str, set[str] | None] = {
    "model": {f.name for f in fields(ModelConfig)},
    "automation": {f.name for f in fields(AutomationConfig)},
    "execute": {f.name for f in fields(ExecuteConfig)},
    "ui": {f.name for f in fields(UIConfig)},
    "agent": {f.name for f in fields(AgentConfig)},
    "models": None,  # aliases + profiles are dynamic
}

# Keys in TOML that use dashes but map to underscored Python field names
_DASH_TO_UNDERSCORE = {
    "auto-review": "auto_review",
    "auto-close": "auto_close",
}

_UNDERSCORE_TO_DASH = {v: k for k, v in _DASH_TO_UNDERSCORE.items()}


# --- Internal helpers ---

def _normalize_toml_dict(d: dict) -> dict:
    """Normalize a raw TOML dict for merging.

    Converts known dash-case keys to snake_case within config sections.
    Converts the 'models' section from TOML flat format (string values = aliases,
    dict values = profiles) to the structured format (_aliases, _profiles) used
    by _config_to_merge_dict, so that deep-merging works correctly.
    """
    result = {}
    for section_key, section_val in d.items():
        if section_key in ("model", "automation", "execute", "ui", "agent") and isinstance(section_val, dict):
            result[section_key] = {
                _DASH_TO_UNDERSCORE.get(k, k): v
                for k, v in section_val.items()
            }
        elif section_key == "models" and isinstance(section_val, dict):
            # Split flat TOML format into structured _aliases/_profiles
            aliases = {}
            profiles = {}
            for k, v in section_val.items():
                if isinstance(v, dict):
                    profiles[k] = v
                else:
                    aliases[k] = v
            result["models"] = {"_aliases": aliases, "_profiles": profiles}
        else:
            result[section_key] = section_val
    return result


def _validate_keys(d: dict) -> list[str]:
    """Validate that all keys in a config dict are known.
    Returns list of error messages.
    """
    errors = []
    for section, val in d.items():
        if section not in _KNOWN_SECTIONS:
            errors.append(f"Unknown config section: '{section}'")
            continue
        allowed_keys = _KNOWN_SECTIONS[section]
        if allowed_keys is None:
            continue  # models section: dynamic keys
        if isinstance(val, dict):
            for key in val:
                if key not in allowed_keys:
                    errors.append(f"Unknown config key: '{section}.{key}'")
    return errors


# --- Validation rules (single source of truth) ---

# Each rule: (section, key) -> validator function.
# Validators accept a value of any type and return an error string or None.
# For TOML dict values the type is native (int, bool, str).
# For string values from CLI/set_config_value, _coerce_string_value
# converts first.

_VALID_AUTOMATION_LEVELS = {"interactive", "supervised", "automatic"}


def _validate_int_ge(threshold: int, label: str):
    """Return a validator that checks value is int >= threshold."""
    def validate(value) -> str | None:
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{label} must be an integer >= {threshold}"
        if value < threshold:
            return f"{label} must be an integer >= {threshold}"
        return None
    return validate


def _validate_bool(label: str):
    """Return a validator that checks value is bool."""
    def validate(value) -> str | None:
        if not isinstance(value, bool):
            return f"{label} must be a boolean"
        return None
    return validate


def _validate_automation_level(key: str):
    """Return a validator that checks value is a valid automation level."""
    def validate(value) -> str | None:
        if value not in _VALID_AUTOMATION_LEVELS:
            return (
                f"automation.{key} must be one of "
                f"'interactive', 'supervised', 'automatic', got '{value}'"
            )
        return None
    return validate


def _validate_model_value(key: str):
    """Return a validator that checks value is a non-empty string or None/null."""
    def validate(value) -> str | None:
        if value is not None and (not isinstance(value, str) or value == ""):
            return f"model.{key} must be a non-empty string or null"
        return None
    return validate


# Build the validation rule registry
_VALIDATION_RULES: dict[tuple[str, str], callable] = {}

# execute section
_VALIDATION_RULES[("execute", "concurrency")] = _validate_int_ge(1, "execute.concurrency")
_VALIDATION_RULES[("execute", "worktrees")] = _validate_bool("execute.worktrees")
_VALIDATION_RULES[("execute", "auto_review")] = _validate_bool("execute.auto_review")

# ui section
_VALIDATION_RULES[("ui", "auto_close")] = _validate_int_ge(0, "ui.auto_close")
_VALIDATION_RULES[("ui", "tmux")] = _validate_bool("ui.tmux")

# automation section (dynamic keys, all share the same rule pattern)
for _auto_key in ("brainstorm", "plan", "implement", "review", "close"):
    _VALIDATION_RULES[("automation", _auto_key)] = _validate_automation_level(_auto_key)

# model section (dynamic keys, all share the same rule pattern)
for _model_key in ("brainstorm", "plan", "implement", "review", "fixup", "close"):
    _VALIDATION_RULES[("model", _model_key)] = _validate_model_value(_model_key)


def _coerce_string_value(section: str, subkey: str, value: str):
    """Coerce a string value (from CLI / set_config_value) to its native type
    for validation. Returns the coerced value.
    Raises ConfigError if the string can't be coerced.
    """
    rule_key = (section, subkey)
    if rule_key not in _VALIDATION_RULES:
        return value  # unknown key or models section — return as-is

    # Determine expected type from the section
    if section == "execute" and subkey == "concurrency":
        try:
            return int(value)
        except ValueError:
            raise ConfigError("execute.concurrency must be an integer >= 1")
    if section == "ui" and subkey == "auto_close":
        try:
            return int(value)
        except ValueError:
            raise ConfigError("ui.auto_close must be an integer >= 0")
    if section in ("execute", "ui") and subkey in ("worktrees", "auto_review", "tmux"):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        raise ConfigError(f"{section}.{subkey} must be a boolean")
    return value  # strings pass through


def _validate_values(d: dict) -> list[str]:
    """Validate config values in a dict. Returns list of error messages."""
    errors = []
    for section, section_val in d.items():
        if not isinstance(section_val, dict):
            continue
        for key, val in section_val.items():
            rule = _VALIDATION_RULES.get((section, key))
            if rule is not None:
                err = rule(val)
                if err:
                    errors.append(err)
    return errors


def _validate_single_key_value(section: str, subkey: str, value: str) -> None:
    """Validate a single key=value for set_config_value.
    Raises ConfigError on unknown key or invalid value.
    Coerces the string value to its native type, then validates using
    the same rules as _validate_values (single source of truth).
    """
    if section not in _KNOWN_SECTIONS:
        raise ConfigError(f"Unknown config section: '{section}'")
    allowed = _KNOWN_SECTIONS[section]
    if allowed is not None and subkey not in allowed:
        raise ConfigError(f"Unknown config key: '{section}.{subkey}'")

    # Coerce string to native type (raises ConfigError on bad format)
    coerced = _coerce_string_value(section, subkey, value)

    # Validate using the shared rule
    rule = _VALIDATION_RULES.get((section, subkey))
    if rule is not None:
        err = rule(coerced)
        if err:
            raise ConfigError(err)


def _section_to_dict(obj) -> dict:
    """Convert a dataclass section to a dict with enum values as strings."""
    from enum import Enum as _Enum
    return {
        f.name: (v.value if isinstance(v, _Enum) else v)
        for f in fields(obj)
        for v in [getattr(obj, f.name)]
    }


def _config_to_merge_dict(config: WorkflowConfig) -> dict:
    """Convert a WorkflowConfig to a flat merge-format dict (snake_case keys,
    enum values as strings, models section with aliases and profiles separate).
    """
    result = {}
    result["model"] = _section_to_dict(config.model)
    result["automation"] = _section_to_dict(config.automation)
    result["execute"] = _section_to_dict(config.execute)
    result["ui"] = _section_to_dict(config.ui)
    result["agent"] = _section_to_dict(config.agent)

    # models: keep aliases and profiles as separate sub-dicts to avoid
    # key collisions between alias names and profile names.
    result["models"] = {
        "_aliases": dict(config.models.aliases),
        "_profiles": dict(config.models.profiles),
    }

    return result


def _merge_dict_to_config(d: dict) -> WorkflowConfig:
    """Convert a merge-format dict to a WorkflowConfig.
    Handles AutomationLevel conversion and models section splitting.
    """
    # model
    model_kwargs = {}
    for k, v in d.get("model", {}).items():
        model_kwargs[k] = v
    model = ModelConfig(**model_kwargs)

    # automation (string → enum)
    auto_kwargs = {}
    for k, v in d.get("automation", {}).items():
        if isinstance(v, str):
            auto_kwargs[k] = AutomationLevel(v)
        else:
            auto_kwargs[k] = v
    automation = AutomationConfig(**auto_kwargs)

    # execute
    execute = ExecuteConfig(**d.get("execute", {}))

    # ui
    ui = UIConfig(**d.get("ui", {}))

    # agent
    agent = AgentConfig(**d.get("agent", {}))

    # models: reconstruct from structured sub-dicts or legacy flat format
    models_raw = d.get("models", {})
    if "_aliases" in models_raw or "_profiles" in models_raw:
        # Structured format (from _config_to_merge_dict)
        aliases = dict(models_raw.get("_aliases", {}))
        profiles = dict(models_raw.get("_profiles", {}))
    else:
        # Flat format from TOML: string values are aliases, dict values are profiles
        aliases = {}
        profiles = {}
        for k, v in models_raw.items():
            if isinstance(v, dict):
                profiles[k] = v
            else:
                aliases[k] = v
    models = ModelsConfig(aliases=aliases, profiles=profiles)

    return WorkflowConfig(
        model=model,
        automation=automation,
        execute=execute,
        ui=ui,
        agent=agent,
        models=models,
    )


def _find_repo_root(cwd: str) -> str | None:
    """Walk up from cwd looking for a .git/ directory. Returns the directory
    containing .git/, or None if not found.
    """
    current = os.path.abspath(cwd)
    while True:
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None  # hit filesystem root
        current = parent


def _format_toml_value(value: str, section: str, subkey: str) -> str:
    """Format a string value for TOML output based on the key's expected type."""
    if section == "execute" and subkey == "concurrency":
        return value  # integer, no quotes
    if section == "ui" and subkey == "auto_close":
        return value  # integer, no quotes
    if section in ("execute", "ui") and subkey in ("worktrees", "auto_review", "tmux"):
        return value.lower()  # boolean, no quotes
    # Everything else is a string
    return f'"{value}"'


def _toml_key_name(subkey: str) -> str:
    """Convert a Python field name to the canonical TOML key name."""
    return _UNDERSCORE_TO_DASH.get(subkey, subkey)


def _toml_key_variants(subkey: str) -> list[str]:
    """Return all forms of a key to search for in a TOML file (underscore and dash)."""
    variants = [subkey]
    if subkey in _UNDERSCORE_TO_DASH:
        variants.append(_UNDERSCORE_TO_DASH[subkey])
    if subkey in _DASH_TO_UNDERSCORE:
        variants.append(_DASH_TO_UNDERSCORE[subkey])
    return variants


# --- Loading ---

def load_user_config() -> dict:
    """Load ~/.config/wf/config.toml. Returns raw dict.
    Returns {} if file doesn't exist. Raises on parse error.
    """
    filepath = os.path.expanduser(USER_CONFIG_PATH)
    if not os.path.isfile(filepath):
        return {}
    try:
        with open(filepath, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Malformed TOML in {filepath}: {exc}") from exc


def load_project_config(cwd: str) -> dict:
    """Load .wf/config.toml from the project root.
    Walks up from cwd to find the repo root (looks for .git/).
    Returns {} if file doesn't exist. Raises on parse error.
    """
    repo_root = _find_repo_root(cwd)
    if repo_root is None:
        return {}
    filepath = os.path.join(repo_root, PROJECT_CONFIG_NAME)
    if not os.path.isfile(filepath):
        return {}
    try:
        with open(filepath, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Malformed TOML in {filepath}: {exc}") from exc


def parse_overrides(overrides: list[str]) -> dict:
    """Parse --set key=value flags into a nested dict.
    Supports dotted keys: 'model.plan=claude-opus-4' becomes
    {'model': {'plan': 'claude-opus-4'}}.
    Raises ValueError on malformed input.
    """
    result: dict = {}
    for item in overrides:
        if "=" not in item:
            raise ValueError(f"Malformed override (missing '='): '{item}'")
        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Malformed override (empty key): '{item}'")

        if key.count(".") != 1:
            raise ValueError(f"Override key must be in 'section.key' format: '{key}'")

        section, subkey = key.split(".", 1)
        subkey = _DASH_TO_UNDERSCORE.get(subkey, subkey)
        if section not in result:
            result[section] = {}
        result[section][subkey] = value
    return result


# --- Merging ---

def merge_configs(*layers: dict) -> dict:
    """Deep-merge config dicts, left to right (last wins).
    Only merges dicts - scalars and lists are replaced, not merged.
    """
    if not layers:
        return {}
    result = {}
    for layer in layers:
        result = _deep_merge(result, layer)
    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge two dicts. Returns a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


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
    # 1. Baked-in defaults as merge dict
    defaults_dict = _config_to_merge_dict(DEFAULTS)

    # 2. User config
    user_raw = load_user_config()
    user_dict = _normalize_toml_dict(user_raw)

    # 3. Project config
    project_raw = load_project_config(cwd)
    project_dict = _normalize_toml_dict(project_raw)

    # 4. Overrides
    overrides_dict = parse_overrides(overrides) if overrides else {}

    # Validate keys in user, project, overrides (not defaults — those are always valid)
    for label, d in [("user config", user_dict), ("project config", project_dict), ("overrides", overrides_dict)]:
        errors = _validate_keys(d)
        if errors:
            raise ConfigError(f"Invalid {label}: {'; '.join(errors)}")

    # Coerce override string values to native types before validation
    for section, section_val in overrides_dict.items():
        if not isinstance(section_val, dict):
            continue
        for subkey, raw_value in section_val.items():
            if isinstance(raw_value, str):
                section_val[subkey] = _coerce_string_value(section, subkey, raw_value)

    # Merge all layers
    merged = merge_configs(defaults_dict, user_dict, project_dict, overrides_dict)

    # Validate values on the merged result (excluding defaults-only sections)
    # We validate only the non-default layers, then the merged result
    for label, d in [("user config", user_dict), ("project config", project_dict), ("overrides", overrides_dict)]:
        errors = _validate_values(d)
        if errors:
            raise ConfigError(f"Invalid {label}: {'; '.join(errors)}")

    # Convert to WorkflowConfig
    return _merge_dict_to_config(merged)


def apply_cli_overrides(
    config: WorkflowConfig,
    **kwargs,
) -> WorkflowConfig:
    """Apply ephemeral CLI flag overrides to a config snapshot.
    Returns a new WorkflowConfig (does not mutate the input).
    """
    d = _config_to_merge_dict(config)

    # Map CLI keyword args to config paths
    _CLI_MAPPINGS = {
        "model_brainstorm": ("model", "brainstorm"),
        "model_plan": ("model", "plan"),
        "model_implement": ("model", "implement"),
        "model_review": ("model", "review"),
        "model_fixup": ("model", "fixup"),
        "model_close": ("model", "close"),
        "concurrency": ("execute", "concurrency"),
        "worktrees": ("execute", "worktrees"),
        "auto_review": ("execute", "auto_review"),
        "auto_close": ("ui", "auto_close"),
        "tmux": ("ui", "tmux"),
        "profile": ("agent", "profile"),
    }

    for kwarg, (section, key) in _CLI_MAPPINGS.items():
        if kwarg in kwargs and kwargs[kwarg] is not None:
            value = kwargs[kwarg]
            rule = _VALIDATION_RULES.get((section, key))
            if rule is not None:
                err = rule(value)
                if err:
                    raise ConfigError(err)
            d[section][key] = value

    return _merge_dict_to_config(d)


def config_to_dict(config: WorkflowConfig) -> dict:
    """Serialize a WorkflowConfig to a dict for JSON storage in the record."""
    return _dataclass_to_dict(config)


def config_from_dict(data: dict) -> WorkflowConfig:
    """Deserialize a WorkflowConfig from a record's workflow.config dict."""
    return _dict_to_dataclass(WorkflowConfig, data)


# --- Inspection ---

def _flatten_dict(d: dict, prefix: str = "") -> list[tuple[str, object]]:
    """Flatten a nested dict to a list of (dotted_key, value) pairs."""
    items = []
    for key, val in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            items.extend(_flatten_dict(val, full_key))
        else:
            items.append((full_key, val))
    return items


def show_resolved(config: WorkflowConfig) -> str:
    """Format a resolved config for display (wf config list)."""
    d = _config_to_merge_dict(config)
    lines = []
    for key, val in _flatten_dict(d):
        if val is None:
            lines.append(f"{key} = <not set>")
        else:
            lines.append(f"{key} = {val}")
    return "\n".join(lines)


def show_with_origins(
    cwd: str,
    overrides: list[str] | None = None,
) -> str:
    """Format the config showing each value's source level.
    e.g. 'model.plan = claude-sonnet-4-5  (project)'
    """
    defaults_dict = _config_to_merge_dict(DEFAULTS)
    user_dict = _normalize_toml_dict(load_user_config())
    project_dict = _normalize_toml_dict(load_project_config(cwd))
    overrides_dict = parse_overrides(overrides) if overrides else {}

    # Flatten each layer
    default_flat = dict(_flatten_dict(defaults_dict))
    user_flat = dict(_flatten_dict(user_dict))
    project_flat = dict(_flatten_dict(project_dict))
    override_flat = dict(_flatten_dict(overrides_dict))

    # Merge to get all keys
    merged = merge_configs(defaults_dict, user_dict, project_dict, overrides_dict)
    merged_flat = _flatten_dict(merged)

    lines = []
    for key, val in merged_flat:
        # Determine origin (highest precedence that set this key)
        if key in override_flat:
            origin = "override"
        elif key in project_flat:
            origin = "project"
        elif key in user_flat:
            origin = "user"
        else:
            origin = "default"
        if val is None:
            lines.append(f"{key} = <not set>  ({origin})")
        else:
            lines.append(f"{key} = {val}  ({origin})")
    return "\n".join(lines)


# --- Editing (for wf config set) ---

def set_config_value(path: str, key: str, value: str, scope: str = "user") -> None:
    """Set a value in a config file. scope is 'user' or 'project'.
    Creates the file if it doesn't exist.

    `path` is the project root directory (used to locate .wf/config.toml for
    project scope), not a dotted config path or file path.
    """
    # Determine file path
    if scope == "user":
        filepath = os.path.expanduser(USER_CONFIG_PATH)
    elif scope == "project":
        filepath = os.path.join(path, PROJECT_CONFIG_NAME)
    else:
        raise ConfigError(f"Invalid scope: '{scope}'")

    # Parse dotted key
    parts = key.split(".", 1)
    if len(parts) != 2:
        raise ConfigError(f"Key must be in 'section.key' format: '{key}'")
    section, subkey = parts

    # Validate key is known and value is valid
    _validate_single_key_value(section, subkey, value)

    # Format value for TOML
    toml_val = _format_toml_value(value, section, subkey)
    toml_key = _toml_key_name(subkey)

    # Read existing file or start empty
    if os.path.isfile(filepath):
        with open(filepath) as f:
            content = f.read()
    else:
        content = ""

    lines = content.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    # Find the section and set the value
    lines = _set_in_toml(lines, section, toml_key, subkey, toml_val)

    # Create parent dirs if needed
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Write back
    with open(filepath, "w") as f:
        f.writelines(lines)


def _set_in_toml(
    lines: list[str], section: str, toml_key: str, subkey: str, toml_val: str
) -> list[str]:
    """Find the [section] header in TOML lines and set key=value.
    If section doesn't exist, append it. If key doesn't exist in section, append it.
    If key exists, replace the line. Preserves comments and formatting.
    """
    result = list(lines)
    key_variants = _toml_key_variants(subkey)

    # Find section header
    section_idx = None
    section_end = None  # index of the line after the last line in this section
    for i, line in enumerate(result):
        stripped = line.strip()
        if stripped == f"[{section}]":
            section_idx = i
        elif section_idx is not None and stripped.startswith("[") and stripped.endswith("]"):
            # We've found the next section header
            section_end = i
            break

    if section_idx is None:
        # Section doesn't exist; append it
        if result and result[-1].strip():
            result.append("\n")
        result.append(f"[{section}]\n")
        result.append(f"{toml_key} = {toml_val}\n")
        return result

    if section_end is None:
        section_end = len(result)

    # Look for the key within the section
    for i in range(section_idx + 1, section_end):
        stripped = result[i].strip()
        # Check if this line sets any variant of our key
        for variant in key_variants:
            if stripped.startswith(f"{variant} ") or stripped.startswith(f"{variant}="):
                # Replace this line
                result[i] = f"{toml_key} = {toml_val}\n"
                return result

    # Key not found in section; insert before the next section (or at end)
    result.insert(section_end, f"{toml_key} = {toml_val}\n")
    return result
