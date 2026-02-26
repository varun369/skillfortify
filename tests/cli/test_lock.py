"""Tests for ``skillfortify lock`` command.

Verifies:
    - Locking an empty directory (exit code 2).
    - Locking a directory with skills generates skill-lock.json.
    - Lockfile content is valid JSON with expected structure.
    - Custom output path works.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillfortify.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CliRunner for invoking commands."""
    return CliRunner()


class TestLockEmptyDirectory:
    """Tests for locking directories with no skills."""

    def test_empty_dir_exits_with_code_2(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Locking an empty directory should exit with code 2."""
        result = runner.invoke(cli, ["lock", str(empty_dir)])
        assert result.exit_code == 2

    def test_empty_dir_shows_message(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Empty lock should display informative message."""
        result = runner.invoke(cli, ["lock", str(empty_dir)])
        assert "No skills found" in result.output


class TestLockWithSkills:
    """Tests for locking directories that contain skills."""

    def test_creates_lockfile(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Lock should create skill-lock.json in the target directory."""
        result = runner.invoke(cli, ["lock", str(clean_claude_skill_dir)])
        assert result.exit_code == 0
        lockfile = clean_claude_skill_dir / "skill-lock.json"
        assert lockfile.exists()

    def test_lockfile_is_valid_json(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Generated lockfile should be valid JSON."""
        runner.invoke(cli, ["lock", str(clean_claude_skill_dir)])
        lockfile = clean_claude_skill_dir / "skill-lock.json"
        data = json.loads(lockfile.read_text())
        assert "lockfile_version" in data
        assert "skills" in data
        assert "metadata" in data

    def test_lockfile_contains_skill(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Lockfile should contain the discovered skill."""
        runner.invoke(cli, ["lock", str(clean_claude_skill_dir)])
        lockfile = clean_claude_skill_dir / "skill-lock.json"
        data = json.loads(lockfile.read_text())
        skills = data["skills"]
        assert len(skills) >= 1
        # The skill name should be present as a key
        assert "helper" in skills

    def test_lockfile_has_integrity_hash(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Each skill in the lockfile should have a SHA-256 integrity hash."""
        runner.invoke(cli, ["lock", str(clean_claude_skill_dir)])
        lockfile = clean_claude_skill_dir / "skill-lock.json"
        data = json.loads(lockfile.read_text())
        for skill_data in data["skills"].values():
            assert skill_data["integrity"].startswith("sha256:")

    def test_lockfile_shows_resolution_summary(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Lock output should display a resolution summary."""
        result = runner.invoke(cli, ["lock", str(clean_claude_skill_dir)])
        assert "successful" in result.output.lower() or "Lockfile written" in result.output


class TestLockCustomOutput:
    """Tests for the --output option."""

    def test_custom_output_path(
        self, runner: CliRunner, clean_claude_skill_dir: Path, tmp_path: Path
    ) -> None:
        """Lock with --output should write to the specified path."""
        custom_path = tmp_path / "custom-lock.json"
        result = runner.invoke(
            cli, ["lock", str(clean_claude_skill_dir), "-o", str(custom_path)]
        )
        assert result.exit_code == 0
        assert custom_path.exists()
        data = json.loads(custom_path.read_text())
        assert "skills" in data

    def test_multi_format_lockfile(
        self, runner: CliRunner, multi_format_skill_dir: Path
    ) -> None:
        """Lock should include skills from multiple formats."""
        result = runner.invoke(cli, ["lock", str(multi_format_skill_dir)])
        assert result.exit_code == 0
        lockfile = multi_format_skill_dir / "skill-lock.json"
        data = json.loads(lockfile.read_text())
        assert len(data["skills"]) >= 2
