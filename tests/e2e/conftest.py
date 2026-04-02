"""E2E conftest.py — fixtures for end-to-end workflow tests.

Provides the `project_from_fixture` fixture which:
1. Copies the fixture's repo/ directory to a temporary directory
2. Runs git init + git add -A + git commit to create a real git repo
3. Makes mock_agent.py executable
4. Sets WF_TEST_SCENARIO and WF_RESULTS_PATH environment variables
5. Returns the project path
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_MOCK_AGENT = Path(__file__).resolve().parent / "mock_agent.py"


@pytest.fixture
def project_from_fixture(tmp_path, monkeypatch):
    """Return a factory that sets up a fixture project in a temp directory.

    Usage in tests::

        def test_something(project_from_fixture):
            project = project_from_fixture("simple-split")
            # project is a Path to a temp dir with a git repo initialized
    """

    def _setup(fixture_name: str) -> Path:
        fixture_dir = _FIXTURES_DIR / fixture_name
        if not fixture_dir.is_dir():
            raise FileNotFoundError(
                f"Fixture directory not found: {fixture_dir}"
            )

        # Copy repo/ contents to tmpdir as the project root
        project_dir = tmp_path / fixture_name
        repo_src = fixture_dir / "repo"
        if repo_src.is_dir():
            shutil.copytree(repo_src, project_dir)
        else:
            project_dir.mkdir(parents=True)

        # Copy non-repo fixture files (plan.json, scenario.json, expected/)
        # into a _fixtures/ subdirectory within the project
        fixtures_dest = project_dir / "_fixtures"
        fixtures_dest.mkdir(exist_ok=True)
        for item in fixture_dir.iterdir():
            if item.name == "repo":
                continue
            dest = fixtures_dest / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Initialize a git repo
        subprocess.run(
            ["git", "init"],
            cwd=project_dir, check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=project_dir, check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@test.com",
             "commit", "-m", "Initial commit"],
            cwd=project_dir, check=True,
            capture_output=True,
        )

        # Make mock_agent.py executable
        mock_agent_path = _MOCK_AGENT
        mock_agent_path.chmod(
            mock_agent_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )

        # Set environment variables
        scenario_path = fixtures_dest / "scenario.json"
        results_path = project_dir / "results.json"
        monkeypatch.setenv("WF_TEST_SCENARIO", str(scenario_path))
        monkeypatch.setenv("WF_RESULTS_PATH", str(results_path))

        return project_dir

    return _setup
