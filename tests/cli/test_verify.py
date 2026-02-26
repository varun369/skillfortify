"""Tests for ``skillfortify verify`` command.

Verifies:
    - Verifying a clean skill file (exit code 0).
    - Verifying a malicious skill file (exit code 1).
    - Verifying a non-existent or unparseable file (exit code 2).
    - JSON output format.
    - Capability inference display.
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


class TestVerifyCleanSkill:
    """Tests for verifying clean (safe) skills."""

    def test_clean_skill_exits_with_code_0(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Verifying a clean skill should exit with code 0."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(cli, ["verify", str(skill_file)])
        assert result.exit_code == 0

    def test_clean_skill_shows_safe(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Clean skill verification should show SAFE status."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(cli, ["verify", str(skill_file)])
        assert "SAFE" in result.output

    def test_clean_skill_json_output(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Clean skill JSON output should show is_safe=true."""
        skill_file = clean_claude_skill_dir / ".claude" / "skills" / "helper.md"
        result = runner.invoke(
            cli, ["verify", str(skill_file), "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_safe"] is True
        assert data["format"] == "claude"


class TestVerifyMaliciousSkill:
    """Tests for verifying malicious skills."""

    def test_malicious_skill_exits_with_code_1(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Verifying a malicious skill should exit with code 1."""
        skill_file = (
            malicious_claude_skill_dir / ".claude" / "skills" / "exfiltrator.md"
        )
        result = runner.invoke(cli, ["verify", str(skill_file)])
        assert result.exit_code == 1

    def test_malicious_skill_shows_findings(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Malicious skill verification should display findings."""
        skill_file = (
            malicious_claude_skill_dir / ".claude" / "skills" / "exfiltrator.md"
        )
        result = runner.invoke(cli, ["verify", str(skill_file)])
        assert "UNSAFE" in result.output

    def test_malicious_skill_json_has_findings(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Malicious skill JSON output should contain findings."""
        skill_file = (
            malicious_claude_skill_dir / ".claude" / "skills" / "exfiltrator.md"
        )
        result = runner.invoke(
            cli, ["verify", str(skill_file), "--format", "json"]
        )
        data = json.loads(result.output)
        assert data["is_safe"] is False
        assert len(data["findings"]) > 0


class TestVerifyNonExistent:
    """Tests for verifying files that cannot be parsed."""

    def test_nonexistent_file_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Verifying a non-existent file should fail."""
        fake = tmp_path / "nonexistent.md"
        result = runner.invoke(cli, ["verify", str(fake)])
        # Click will catch the path-not-exists error before our code
        assert result.exit_code != 0

    def test_non_skill_file_exits_with_code_2(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Verifying a file that is not a recognized skill should exit 2."""
        plain_file = tmp_path / "readme.txt"
        plain_file.write_text("This is not a skill file.")
        result = runner.invoke(cli, ["verify", str(plain_file)])
        assert result.exit_code == 2

    def test_non_skill_json_error(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-skill file JSON should contain error message."""
        plain_file = tmp_path / "readme.txt"
        plain_file.write_text("This is not a skill file.")
        result = runner.invoke(
            cli, ["verify", str(plain_file), "--format", "json"]
        )
        data = json.loads(result.output)
        assert "error" in data
