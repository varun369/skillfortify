"""Tests for ``skillfortify scan`` command.

Verifies:
    - Scanning empty directories (exit code 2).
    - Scanning directories with clean skills (exit code 0).
    - Scanning directories with malicious skills (exit code 1).
    - JSON output format.
    - Severity threshold filtering.
    - Multi-format skill discovery.
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


class TestScanEmptyDirectory:
    """Tests for scanning directories with no skills."""

    def test_empty_dir_exits_with_code_2(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Scanning an empty directory should exit with code 2."""
        result = runner.invoke(cli, ["scan", str(empty_dir)])
        assert result.exit_code == 2

    def test_empty_dir_shows_no_skills_message(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Empty scan should display 'No skills found' message."""
        result = runner.invoke(cli, ["scan", str(empty_dir)])
        assert "No skills found" in result.output

    def test_empty_dir_json_format(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Empty scan with JSON format should output valid JSON."""
        result = runner.invoke(cli, ["scan", str(empty_dir), "--format", "json"])
        assert result.exit_code == 2
        data = json.loads(result.output)
        assert data["skills"] == []


class TestScanCleanSkills:
    """Tests for scanning directories with clean (safe) skills."""

    def test_clean_skill_exits_with_code_0(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Scanning a clean skill should exit with code 0."""
        result = runner.invoke(cli, ["scan", str(clean_claude_skill_dir)])
        assert result.exit_code == 0

    def test_clean_skill_text_output(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Clean scan text output should show SAFE status."""
        result = runner.invoke(cli, ["scan", str(clean_claude_skill_dir)])
        assert "SAFE" in result.output

    def test_clean_skill_json_output(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Clean scan JSON output should show is_safe=true."""
        result = runner.invoke(
            cli, ["scan", str(clean_claude_skill_dir), "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["is_safe"] is True
        assert data[0]["findings_count"] == 0


class TestScanMaliciousSkills:
    """Tests for scanning directories with malicious skills."""

    def test_malicious_skill_exits_with_code_1(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Scanning a malicious skill should exit with code 1."""
        result = runner.invoke(cli, ["scan", str(malicious_claude_skill_dir)])
        assert result.exit_code == 1

    def test_malicious_skill_text_output_shows_unsafe(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Malicious scan text output should show UNSAFE status."""
        result = runner.invoke(cli, ["scan", str(malicious_claude_skill_dir)])
        assert "UNSAFE" in result.output

    def test_malicious_skill_json_has_findings(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Malicious scan JSON output should contain findings."""
        result = runner.invoke(
            cli, ["scan", str(malicious_claude_skill_dir), "--format", "json"]
        )
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["is_safe"] is False
        assert data[0]["findings_count"] > 0
        assert len(data[0]["findings"]) > 0


class TestScanSeverityThreshold:
    """Tests for the --severity-threshold option."""

    def test_critical_threshold_filters_lower(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Setting critical threshold should filter out non-critical findings."""
        result = runner.invoke(
            cli,
            ["scan", str(malicious_claude_skill_dir),
             "--severity-threshold", "critical", "--format", "json"],
        )
        data = json.loads(result.output)
        for skill in data:
            for finding in skill.get("findings", []):
                assert finding["severity"] == "CRITICAL"


class TestScanMultiFormat:
    """Tests for scanning directories with multiple skill formats."""

    def test_discovers_multiple_formats(
        self, runner: CliRunner, multi_format_skill_dir: Path
    ) -> None:
        """Scan should discover skills from both Claude and MCP formats."""
        result = runner.invoke(
            cli,
            ["scan", str(multi_format_skill_dir), "--format", "json"],
        )
        data = json.loads(result.output)
        assert len(data) >= 2

    def test_mcp_skill_scanned(
        self, runner: CliRunner, clean_mcp_skill_dir: Path
    ) -> None:
        """Scan should discover and analyze MCP server configurations."""
        result = runner.invoke(
            cli, ["scan", str(clean_mcp_skill_dir), "--format", "json"],
        )
        data = json.loads(result.output)
        assert len(data) >= 1
