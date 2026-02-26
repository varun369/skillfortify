"""Tests for ``skillfortify trust`` command.

Verifies:
    - Trust score computation for a clean skill.
    - Trust score computation for a malicious skill.
    - JSON output format.
    - Trust level display.
    - Non-parseable file handling.
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


class TestTrustCleanSkill:
    """Tests for trust score of clean skills."""

    def test_clean_skill_exits_with_code_0(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Trust command on a clean skill should exit with code 0."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(cli, ["trust", str(skill_file)])
        assert result.exit_code == 0

    def test_clean_skill_shows_trust_level(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Trust output should display a trust level."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(cli, ["trust", str(skill_file)])
        # Should show one of the trust level names
        assert any(
            level in result.output
            for level in ["UNSIGNED", "SIGNED", "COMMUNITY_VERIFIED", "FORMALLY_VERIFIED"]
        )

    def test_clean_skill_json_output(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Trust JSON output should contain all score fields."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(
            cli, ["trust", str(skill_file), "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "skill_name" in data
        assert "intrinsic_score" in data
        assert "effective_score" in data
        assert "level" in data
        assert "signals" in data

    def test_clean_skill_high_behavioral_signal(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Clean skill should have high behavioral signal (1.0)."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(
            cli, ["trust", str(skill_file), "--format", "json"]
        )
        data = json.loads(result.output)
        assert data["signals"]["behavioral"] == 1.0


class TestTrustMaliciousSkill:
    """Tests for trust score of malicious skills."""

    def test_malicious_skill_lower_behavioral(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Malicious skill should have lower behavioral signal."""
        skill_file = (
            malicious_claude_skill_dir / ".claude" / "skills" / "exfiltrator.md"
        )
        result = runner.invoke(
            cli, ["trust", str(skill_file), "--format", "json"]
        )
        data = json.loads(result.output)
        # Findings should reduce the behavioral signal below 1.0
        assert data["signals"]["behavioral"] < 1.0

    def test_malicious_skill_lower_score(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Malicious skill should have lower intrinsic score than clean."""
        skill_file = (
            malicious_claude_skill_dir / ".claude" / "skills" / "exfiltrator.md"
        )
        result = runner.invoke(
            cli, ["trust", str(skill_file), "--format", "json"]
        )
        data = json.loads(result.output)
        # Default baselines are 0.5 for provenance/community/historical
        # Behavioral will be < 1.0 due to findings
        # So intrinsic < 0.3*0.5 + 0.3*1.0 + 0.2*0.5 + 0.2*0.5 = 0.65
        assert data["intrinsic_score"] < 0.65


class TestTrustNonParseable:
    """Tests for trust on non-parseable files."""

    def test_non_skill_exits_with_code_2(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Trust on a non-skill file should exit with code 2."""
        plain_file = tmp_path / "readme.txt"
        plain_file.write_text("Not a skill.")
        result = runner.invoke(cli, ["trust", str(plain_file)])
        assert result.exit_code == 2

    def test_non_skill_json_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-skill trust JSON should contain error."""
        plain_file = tmp_path / "readme.txt"
        plain_file.write_text("Not a skill.")
        result = runner.invoke(
            cli, ["trust", str(plain_file), "--format", "json"]
        )
        data = json.loads(result.output)
        assert "error" in data
