"""Tests for wflib.config — config loading, merging, resolution, precedence chain."""

import unittest

from wflib.config import (
    apply_cli_overrides,
    config_from_dict,
    config_to_dict,
    load_project_config,
    load_user_config,
    merge_configs,
    parse_overrides,
    resolve_config,
    set_config_value,
    show_resolved,
    show_with_origins,
)


class TestLoadUserConfig(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_returns_empty_when_no_file(self):
        """Returns {} when ~/.config/wf/config.toml does not exist."""

    @unittest.skip("Phase 1")
    def test_parses_valid_toml(self):
        """Parses a valid TOML config into a dict."""

    @unittest.skip("Phase 1")
    def test_raises_on_invalid_toml(self):
        """Raises on malformed TOML."""


class TestLoadProjectConfig(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_returns_empty_when_no_file(self):
        """Returns {} when .wf/config.toml does not exist."""

    @unittest.skip("Phase 1")
    def test_finds_config_at_repo_root(self):
        """Walks up from cwd to find .git/, loads .wf/config.toml there."""

    @unittest.skip("Phase 1")
    def test_raises_on_invalid_toml(self):
        """Raises on malformed TOML."""


class TestParseOverrides(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_simple_key_value(self):
        """Parses 'key=value' into {'key': 'value'}."""

    @unittest.skip("Phase 1")
    def test_dotted_key(self):
        """Parses 'model.plan=opus' into {'model': {'plan': 'opus'}}."""

    @unittest.skip("Phase 1")
    def test_raises_on_malformed(self):
        """Raises ValueError on input without '='."""


class TestMergeConfigs(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_last_wins(self):
        """Later dicts override earlier ones for scalar values."""

    @unittest.skip("Phase 1")
    def test_deep_merge_dicts(self):
        """Nested dicts are merged, not replaced."""

    @unittest.skip("Phase 1")
    def test_scalars_replace_not_merge(self):
        """Non-dict values are replaced, not merged."""


class TestResolveConfig(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_defaults_only(self):
        """resolve_config with no config files returns baked-in defaults."""

    @unittest.skip("Phase 1")
    def test_precedence_chain(self):
        """user < project < overrides precedence is respected."""

    @unittest.skip("Phase 1")
    def test_unknown_key_raises(self):
        """Unknown keys in config files are hard errors."""

    @unittest.skip("Phase 1")
    def test_invalid_value_raises(self):
        """Invalid values (e.g., negative concurrency) raise ConfigError."""

    @unittest.skip("Phase 1")
    def test_valid_automation_levels(self):
        """Only 'interactive', 'supervised', 'automatic' are accepted."""


class TestApplyCliOverrides(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_returns_new_config(self):
        """Does not mutate the input config."""

    @unittest.skip("Phase 1")
    def test_overrides_model(self):
        """CLI --model overrides config.model.implement."""

    @unittest.skip("Phase 1")
    def test_overrides_concurrency(self):
        """CLI --concurrency overrides config.execute.concurrency."""


class TestConfigSerialization(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_round_trip(self):
        """config_to_dict -> config_from_dict produces equivalent config."""


class TestSetConfigValue(unittest.TestCase):
    @unittest.skip("Phase 1")
    def test_set_new_value(self):
        """Sets a value in a config file, creates file if needed."""

    @unittest.skip("Phase 1")
    def test_unknown_key_raises(self):
        """Raises ConfigError on unknown keys."""

    @unittest.skip("Phase 1")
    def test_preserves_comments(self):
        """Existing comments and formatting are preserved."""


if __name__ == "__main__":
    unittest.main()
