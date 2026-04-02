"""Tests for wflib.config — config loading, merging, resolution, precedence chain."""

import os
import tempfile
import unittest
from unittest.mock import patch

from wflib.config import (
    ConfigError,
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
from wflib.types import (
    AutomationConfig,
    AutomationLevel,
    ExecuteConfig,
    ModelConfig,
    ModelsConfig,
    UIConfig,
    WorkflowConfig,
)


class TestLoadUserConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_returns_empty_when_no_file(self):
        """Returns {} when ~/.config/wf/config.toml does not exist."""
        fake_path = os.path.join(self.tmp, "nonexistent", "config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_path):
            result = load_user_config()
        self.assertEqual(result, {})

    def test_parses_valid_toml(self):
        """Parses a valid TOML config into a dict."""
        config_file = os.path.join(self.tmp, "config.toml")
        with open(config_file, "w") as f:
            f.write('[model]\nplan = "claude-opus-4"\n')
        with patch("wflib.config.USER_CONFIG_PATH", config_file):
            result = load_user_config()
        self.assertEqual(result, {"model": {"plan": "claude-opus-4"}})

    def test_raises_on_invalid_toml(self):
        """Raises ConfigError on malformed TOML."""
        config_file = os.path.join(self.tmp, "config.toml")
        with open(config_file, "w") as f:
            f.write("[model\nbroken syntax")
        with patch("wflib.config.USER_CONFIG_PATH", config_file):
            with self.assertRaises(ConfigError):
                load_user_config()


class TestLoadProjectConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_returns_empty_when_no_file(self):
        """Returns {} when .wf/config.toml does not exist."""
        # Create a fake repo root with .git but no .wf/config.toml
        os.makedirs(os.path.join(self.tmp, ".git"))
        result = load_project_config(self.tmp)
        self.assertEqual(result, {})

    def test_finds_config_at_repo_root(self):
        """Walks up from cwd to find .git/, loads .wf/config.toml there."""
        os.makedirs(os.path.join(self.tmp, ".git"))
        os.makedirs(os.path.join(self.tmp, ".wf"))
        config_file = os.path.join(self.tmp, ".wf", "config.toml")
        with open(config_file, "w") as f:
            f.write('[execute]\nconcurrency = 8\n')

        # cwd is a subdirectory
        subdir = os.path.join(self.tmp, "src", "deep", "nested")
        os.makedirs(subdir)
        result = load_project_config(subdir)
        self.assertEqual(result, {"execute": {"concurrency": 8}})

    def test_raises_on_invalid_toml(self):
        """Raises ConfigError on malformed TOML."""
        os.makedirs(os.path.join(self.tmp, ".git"))
        os.makedirs(os.path.join(self.tmp, ".wf"))
        config_file = os.path.join(self.tmp, ".wf", "config.toml")
        with open(config_file, "w") as f:
            f.write("[bad\nsyntax")
        with self.assertRaises(ConfigError):
            load_project_config(self.tmp)

    def test_returns_empty_when_no_git(self):
        """Returns {} when no .git/ directory is found."""
        # tmp dir with no .git
        result = load_project_config(self.tmp)
        self.assertEqual(result, {})


class TestParseOverrides(unittest.TestCase):
    def test_simple_key_value(self):
        """Parses 'key=value' into a flat nested dict."""
        result = parse_overrides(["concurrency=8"])
        self.assertEqual(result, {"concurrency": "8"})

    def test_dotted_key(self):
        """Parses 'model.plan=opus' into {'model': {'plan': 'opus'}}."""
        result = parse_overrides(["model.plan=opus"])
        self.assertEqual(result, {"model": {"plan": "opus"}})

    def test_multiple_overrides(self):
        """Multiple overrides are merged."""
        result = parse_overrides(["model.plan=opus", "model.review=sonnet"])
        self.assertEqual(result, {"model": {"plan": "opus", "review": "sonnet"}})

    def test_raises_on_malformed(self):
        """Raises ValueError on input without '='."""
        with self.assertRaises(ValueError):
            parse_overrides(["model.plan"])

    def test_value_with_equals(self):
        """Values containing '=' are preserved."""
        result = parse_overrides(["key=a=b"])
        self.assertEqual(result, {"key": "a=b"})

    def test_empty_list(self):
        """Empty list returns empty dict."""
        self.assertEqual(parse_overrides([]), {})


class TestMergeConfigs(unittest.TestCase):
    def test_last_wins(self):
        """Later dicts override earlier ones for scalar values."""
        a = {"model": {"plan": "opus"}}
        b = {"model": {"plan": "sonnet"}}
        result = merge_configs(a, b)
        self.assertEqual(result["model"]["plan"], "sonnet")

    def test_deep_merge_dicts(self):
        """Nested dicts are merged, not replaced."""
        a = {"model": {"plan": "opus", "review": "haiku"}}
        b = {"model": {"plan": "sonnet"}}
        result = merge_configs(a, b)
        self.assertEqual(result["model"]["plan"], "sonnet")
        self.assertEqual(result["model"]["review"], "haiku")

    def test_scalars_replace_not_merge(self):
        """Non-dict values are replaced, not merged."""
        a = {"execute": {"concurrency": 4}}
        b = {"execute": {"concurrency": 8}}
        result = merge_configs(a, b)
        self.assertEqual(result["execute"]["concurrency"], 8)

    def test_lists_are_replaced(self):
        """Lists are replaced wholesale, not concatenated."""
        a = {"items": [1, 2, 3]}
        b = {"items": [4, 5]}
        result = merge_configs(a, b)
        self.assertEqual(result["items"], [4, 5])

    def test_empty_inputs(self):
        """No inputs returns empty dict."""
        self.assertEqual(merge_configs(), {})

    def test_three_layers(self):
        """Three layers merge correctly."""
        a = {"x": 1, "y": 2}
        b = {"y": 3, "z": 4}
        c = {"x": 5}
        result = merge_configs(a, b, c)
        self.assertEqual(result, {"x": 5, "y": 3, "z": 4})

    def test_new_keys_added(self):
        """New keys from later dicts are added."""
        a = {"model": {"plan": "opus"}}
        b = {"execute": {"concurrency": 8}}
        result = merge_configs(a, b)
        self.assertEqual(result["model"]["plan"], "opus")
        self.assertEqual(result["execute"]["concurrency"], 8)


class TestResolveConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Create a fake repo root
        os.makedirs(os.path.join(self.tmp, ".git"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _mock_user_config(self, data_str):
        """Write a user config toml and return path for patching."""
        config_file = os.path.join(self.tmp, "user_config.toml")
        with open(config_file, "w") as f:
            f.write(data_str)
        return config_file

    def _write_project_config(self, data_str):
        """Write a project config toml in the fake repo."""
        os.makedirs(os.path.join(self.tmp, ".wf"), exist_ok=True)
        with open(os.path.join(self.tmp, ".wf", "config.toml"), "w") as f:
            f.write(data_str)

    def test_defaults_only(self):
        """resolve_config with no config files returns baked-in defaults."""
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            config = resolve_config(self.tmp)
        defaults = WorkflowConfig()
        self.assertEqual(config.execute.concurrency, defaults.execute.concurrency)
        self.assertEqual(config.automation.brainstorm, defaults.automation.brainstorm)
        self.assertIsNone(config.model.plan)

    def test_precedence_chain(self):
        """user < project < overrides precedence is respected."""
        user_path = self._mock_user_config(
            '[model]\nplan = "from-user"\nreview = "from-user"\n'
        )
        self._write_project_config(
            '[model]\nplan = "from-project"\n'
        )
        with patch("wflib.config.USER_CONFIG_PATH", user_path):
            config = resolve_config(
                self.tmp,
                overrides=["model.plan=from-override"],
            )
        # override > project > user
        self.assertEqual(config.model.plan, "from-override")
        # project didn't set review, so user wins
        self.assertEqual(config.model.review, "from-user")

    def test_unknown_key_raises(self):
        """Unknown keys in config files are hard errors."""
        user_path = self._mock_user_config(
            '[model]\nnonexistent = "bad"\n'
        )
        with patch("wflib.config.USER_CONFIG_PATH", user_path):
            with self.assertRaises(ConfigError):
                resolve_config(self.tmp)

    def test_unknown_section_raises(self):
        """Unknown top-level sections raise ConfigError."""
        user_path = self._mock_user_config(
            '[bogus_section]\nfoo = "bar"\n'
        )
        with patch("wflib.config.USER_CONFIG_PATH", user_path):
            with self.assertRaises(ConfigError):
                resolve_config(self.tmp)

    def test_invalid_value_raises(self):
        """Invalid values (e.g., negative concurrency) raise ConfigError."""
        self._write_project_config("[execute]\nconcurrency = -1\n")
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            with self.assertRaises(ConfigError):
                resolve_config(self.tmp)

    def test_valid_automation_levels(self):
        """Only 'interactive', 'supervised', 'automatic' are accepted."""
        # Valid levels should work
        self._write_project_config(
            '[automation]\nbrainstorm = "automatic"\nplan = "supervised"\n'
        )
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            config = resolve_config(self.tmp)
        self.assertEqual(config.automation.brainstorm, AutomationLevel.AUTOMATIC)
        self.assertEqual(config.automation.plan, AutomationLevel.SUPERVISED)

    def test_invalid_automation_level_raises(self):
        """Invalid automation level raises ConfigError."""
        self._write_project_config(
            '[automation]\nbrainstorm = "turbo"\n'
        )
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            with self.assertRaises(ConfigError):
                resolve_config(self.tmp)

    def test_dash_keys_normalized(self):
        """TOML keys with dashes (auto-review) are normalized to underscores."""
        self._write_project_config("[execute]\nauto-review = false\n")
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            config = resolve_config(self.tmp)
        self.assertFalse(config.execute.auto_review)

    def test_models_section_aliases(self):
        """Models section aliases are loaded correctly."""
        self._write_project_config(
            '[models]\nfast = "claude-haiku-4-5"\nbig = "claude-opus-4"\n'
        )
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            config = resolve_config(self.tmp)
        self.assertEqual(config.models.aliases["fast"], "claude-haiku-4-5")
        self.assertEqual(config.models.aliases["big"], "claude-opus-4")


class TestApplyCliOverrides(unittest.TestCase):
    def test_returns_new_config(self):
        """Does not mutate the input config."""
        original = WorkflowConfig()
        original_concurrency = original.execute.concurrency
        result = apply_cli_overrides(original, concurrency=16)
        # Original unchanged
        self.assertEqual(original.execute.concurrency, original_concurrency)
        # Result has override
        self.assertEqual(result.execute.concurrency, 16)

    def test_overrides_model(self):
        """CLI --model overrides config.model.implement."""
        config = WorkflowConfig()
        result = apply_cli_overrides(config, model_implement="claude-opus-4")
        self.assertEqual(result.model.implement, "claude-opus-4")

    def test_overrides_concurrency(self):
        """CLI --concurrency overrides config.execute.concurrency."""
        config = WorkflowConfig()
        result = apply_cli_overrides(config, concurrency=2)
        self.assertEqual(result.execute.concurrency, 2)

    def test_none_values_ignored(self):
        """None kwargs don't override existing values."""
        config = WorkflowConfig(
            model=ModelConfig(plan="original"),
        )
        result = apply_cli_overrides(config, model_plan=None, concurrency=2)
        self.assertEqual(result.model.plan, "original")
        self.assertEqual(result.execute.concurrency, 2)

    def test_preserves_non_overridden(self):
        """Non-overridden values are preserved."""
        config = WorkflowConfig(
            model=ModelConfig(plan="opus", review="haiku"),
            execute=ExecuteConfig(concurrency=4),
        )
        result = apply_cli_overrides(config, model_plan="sonnet")
        self.assertEqual(result.model.plan, "sonnet")
        self.assertEqual(result.model.review, "haiku")
        self.assertEqual(result.execute.concurrency, 4)


class TestConfigSerialization(unittest.TestCase):
    def test_round_trip(self):
        """config_to_dict -> config_from_dict produces equivalent config."""
        config = WorkflowConfig(
            model=ModelConfig(plan="opus", implement="sonnet"),
            automation=AutomationConfig(
                brainstorm=AutomationLevel.AUTOMATIC,
                implement=AutomationLevel.SUPERVISED,
            ),
            execute=ExecuteConfig(concurrency=8, worktrees=False),
            ui=UIConfig(auto_close=60, tmux=False),
        )
        d = config_to_dict(config)
        restored = config_from_dict(d)
        self.assertEqual(restored.model.plan, config.model.plan)
        self.assertEqual(restored.model.implement, config.model.implement)
        self.assertEqual(restored.automation.brainstorm, config.automation.brainstorm)
        self.assertEqual(restored.automation.implement, config.automation.implement)
        self.assertEqual(restored.execute.concurrency, config.execute.concurrency)
        self.assertEqual(restored.execute.worktrees, config.execute.worktrees)
        self.assertEqual(restored.ui.auto_close, config.ui.auto_close)
        self.assertEqual(restored.ui.tmux, config.ui.tmux)

    def test_round_trip_defaults(self):
        """Default config round-trips cleanly."""
        config = WorkflowConfig()
        d = config_to_dict(config)
        restored = config_from_dict(d)
        self.assertEqual(restored.execute.concurrency, config.execute.concurrency)
        self.assertEqual(restored.automation.brainstorm, config.automation.brainstorm)
        self.assertIsNone(restored.model.plan)

    def test_camel_case_keys(self):
        """config_to_dict produces camelCase keys."""
        config = WorkflowConfig()
        d = config_to_dict(config)
        # autoClose, autoReview should be camelCase
        self.assertIn("autoClose", d["ui"])
        self.assertIn("autoReview", d["execute"])

    def test_round_trip_with_models(self):
        """Models config round-trips through dict."""
        config = WorkflowConfig(
            models=ModelsConfig(
                aliases={"fast": "claude-haiku-4-5"},
                profiles={"pi": {"gpt-4o": "openai/gpt-4o"}},
            )
        )
        d = config_to_dict(config)
        restored = config_from_dict(d)
        self.assertEqual(restored.models.aliases, config.models.aliases)
        self.assertEqual(restored.models.profiles, config.models.profiles)

    def test_models_alias_profile_same_key_survives(self):
        """An alias and a profile with the same key both survive round-trip."""
        config = WorkflowConfig(
            models=ModelsConfig(
                aliases={"fast": "claude-haiku-4-5"},
                profiles={"fast": {"gpt-4o": "openai/gpt-4o"}},
            )
        )
        d = config_to_dict(config)
        restored = config_from_dict(d)
        self.assertEqual(restored.models.aliases["fast"], "claude-haiku-4-5")
        self.assertEqual(restored.models.profiles["fast"], {"gpt-4o": "openai/gpt-4o"})


class TestSetConfigValue(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_set_new_value_user(self):
        """Sets a value in a user config file, creates file if needed."""
        fake_user = os.path.join(self.tmp, "wf", "config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            set_config_value(self.tmp, "model.plan", "claude-opus-4", scope="user")
        self.assertTrue(os.path.isfile(fake_user))
        with open(fake_user) as f:
            content = f.read()
        self.assertIn("[model]", content)
        self.assertIn("plan", content)
        self.assertIn("claude-opus-4", content)

    def test_set_new_value_project(self):
        """Sets a value in a project config file."""
        set_config_value(self.tmp, "execute.concurrency", "8", scope="project")
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        self.assertTrue(os.path.isfile(filepath))
        with open(filepath) as f:
            content = f.read()
        self.assertIn("[execute]", content)
        self.assertIn("concurrency = 8", content)

    def test_unknown_key_raises(self):
        """Raises ConfigError on unknown keys."""
        with self.assertRaises(ConfigError):
            set_config_value(self.tmp, "bogus.key", "value", scope="project")

    def test_unknown_section_raises(self):
        """Raises ConfigError on unknown sections."""
        with self.assertRaises(ConfigError):
            set_config_value(self.tmp, "nonexistent.foo", "bar", scope="project")

    def test_preserves_comments(self):
        """Existing comments and formatting are preserved."""
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        os.makedirs(os.path.dirname(filepath))
        with open(filepath, "w") as f:
            f.write("# My project config\n[model]\n# Model for planning\nplan = \"old-model\"\n")

        set_config_value(self.tmp, "model.plan", "new-model", scope="project")
        with open(filepath) as f:
            content = f.read()
        self.assertIn("# My project config", content)
        self.assertIn("# Model for planning", content)
        self.assertIn("new-model", content)
        self.assertNotIn("old-model", content)

    def test_updates_existing_key(self):
        """Updating an existing key replaces the value, doesn't duplicate."""
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        os.makedirs(os.path.dirname(filepath))
        with open(filepath, "w") as f:
            f.write('[execute]\nconcurrency = 4\nworktrees = true\n')

        set_config_value(self.tmp, "execute.concurrency", "8", scope="project")
        with open(filepath) as f:
            content = f.read()
        self.assertIn("concurrency = 8", content)
        # Should not have duplicate
        self.assertEqual(content.count("concurrency"), 1)

    def test_adds_new_section(self):
        """Adds a new section if it doesn't exist."""
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        os.makedirs(os.path.dirname(filepath))
        with open(filepath, "w") as f:
            f.write('[model]\nplan = "opus"\n')

        set_config_value(self.tmp, "execute.concurrency", "8", scope="project")
        with open(filepath) as f:
            content = f.read()
        self.assertIn("[model]", content)
        self.assertIn("[execute]", content)
        self.assertIn("concurrency = 8", content)

    def test_boolean_value_formatting(self):
        """Boolean values are formatted correctly in TOML."""
        set_config_value(self.tmp, "execute.worktrees", "false", scope="project")
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        with open(filepath) as f:
            content = f.read()
        self.assertIn("worktrees = false", content)

    def test_invalid_concurrency_raises(self):
        """Setting negative concurrency raises ConfigError."""
        with self.assertRaises(ConfigError):
            set_config_value(self.tmp, "execute.concurrency", "-1", scope="project")

    def test_invalid_automation_raises(self):
        """Setting invalid automation level raises ConfigError."""
        with self.assertRaises(ConfigError):
            set_config_value(self.tmp, "automation.brainstorm", "turbo", scope="project")

    def test_models_aliases_allowed(self):
        """Models section allows dynamic alias keys."""
        set_config_value(self.tmp, "models.fast", "claude-haiku-4-5", scope="project")
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        with open(filepath) as f:
            content = f.read()
        self.assertIn("[models]", content)
        self.assertIn("fast", content)

    def test_dash_key_update_from_underscore(self):
        """Setting auto_review finds and updates the TOML auto-review key."""
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        os.makedirs(os.path.dirname(filepath))
        with open(filepath, "w") as f:
            f.write('[execute]\nauto-review = true\n')

        set_config_value(self.tmp, "execute.auto_review", "false", scope="project")
        with open(filepath) as f:
            content = f.read()
        # Should update the existing dash-form key, not add a duplicate
        self.assertIn("auto-review = false", content)
        self.assertEqual(content.count("auto-review"), 1)
        self.assertNotIn("auto_review", content)

    def test_underscore_key_update_from_dash_input(self):
        """Setting auto_close updates the TOML auto-close variant."""
        filepath = os.path.join(self.tmp, ".wf", "config.toml")
        os.makedirs(os.path.dirname(filepath))
        with open(filepath, "w") as f:
            f.write('[ui]\nauto-close = 30\n')

        set_config_value(self.tmp, "ui.auto_close", "60", scope="project")
        with open(filepath) as f:
            content = f.read()
        self.assertIn("auto-close = 60", content)
        self.assertEqual(content.count("auto-close"), 1)


class TestShowResolved(unittest.TestCase):
    def test_basic_output(self):
        """show_resolved returns formatted config string."""
        config = WorkflowConfig()
        output = show_resolved(config)
        self.assertIn("execute.concurrency = 4", output)
        self.assertIn("automation.brainstorm = interactive", output)
        self.assertIn("model.plan = <not set>", output)

    def test_custom_values(self):
        """show_resolved shows custom values."""
        config = WorkflowConfig(
            model=ModelConfig(plan="opus"),
            execute=ExecuteConfig(concurrency=8),
        )
        output = show_resolved(config)
        self.assertIn("model.plan = opus", output)
        self.assertIn("execute.concurrency = 8", output)


class TestShowWithOrigins(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, ".git"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_defaults_show_default_origin(self):
        """Default values are annotated with (default)."""
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            output = show_with_origins(self.tmp)
        self.assertIn("(default)", output)
        self.assertIn("execute.concurrency = 4", output)

    def test_override_origin(self):
        """Overridden values are annotated with (override)."""
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            output = show_with_origins(
                self.tmp, overrides=["model.plan=opus"]
            )
        self.assertIn("model.plan = opus  (override)", output)

    def test_project_origin(self):
        """Project config values are annotated with (project)."""
        os.makedirs(os.path.join(self.tmp, ".wf"))
        with open(os.path.join(self.tmp, ".wf", "config.toml"), "w") as f:
            f.write('[execute]\nconcurrency = 8\n')
        fake_user = os.path.join(self.tmp, "no_user_config.toml")
        with patch("wflib.config.USER_CONFIG_PATH", fake_user):
            output = show_with_origins(self.tmp)
        self.assertIn("execute.concurrency = 8  (project)", output)


if __name__ == "__main__":
    unittest.main()
