"""Tests for ``skillfortify sbom`` command.

Verifies:
    - SBOM generation for empty directories (exit code 2).
    - SBOM generation for directories with skills (exit code 0).
    - Generated ASBOM is valid CycloneDX 1.6 JSON.
    - Custom output path.
    - Summary display.
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


class TestSbomEmptyDirectory:
    """Tests for SBOM generation on empty directories."""

    def test_empty_dir_exits_with_code_2(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """SBOM on empty directory should exit with code 2."""
        result = runner.invoke(cli, ["sbom", str(empty_dir)])
        assert result.exit_code == 2

    def test_empty_dir_shows_message(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Empty SBOM should display informative message."""
        result = runner.invoke(cli, ["sbom", str(empty_dir)])
        assert "No skills found" in result.output


class TestSbomGeneration:
    """Tests for successful SBOM generation."""

    def test_creates_asbom_file(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """SBOM should create asbom.cdx.json in the target directory."""
        result = runner.invoke(cli, ["sbom", str(clean_claude_skill_dir)])
        assert result.exit_code == 0
        asbom_file = clean_claude_skill_dir / "asbom.cdx.json"
        assert asbom_file.exists()

    def test_asbom_is_valid_cyclonedx(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Generated ASBOM should be valid CycloneDX 1.6 JSON."""
        runner.invoke(cli, ["sbom", str(clean_claude_skill_dir)])
        asbom_file = clean_claude_skill_dir / "asbom.cdx.json"
        data = json.loads(asbom_file.read_text())
        assert data["bomFormat"] == "CycloneDX"
        assert data["specVersion"] == "1.6"
        assert "components" in data
        assert "metadata" in data

    def test_asbom_contains_skill_components(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """ASBOM should contain a component for each discovered skill."""
        runner.invoke(cli, ["sbom", str(clean_claude_skill_dir)])
        asbom_file = clean_claude_skill_dir / "asbom.cdx.json"
        data = json.loads(asbom_file.read_text())
        assert len(data["components"]) >= 1
        comp = data["components"][0]
        assert "name" in comp
        assert "purl" in comp

    def test_asbom_has_skillfortify_properties(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """ASBOM components should have skillfortify-specific properties."""
        runner.invoke(cli, ["sbom", str(clean_claude_skill_dir)])
        asbom_file = clean_claude_skill_dir / "asbom.cdx.json"
        data = json.loads(asbom_file.read_text())
        comp = data["components"][0]
        prop_names = [p["name"] for p in comp["properties"]]
        assert "skillfortify:format" in prop_names
        assert "skillfortify:is-safe" in prop_names

    def test_output_shows_summary(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """SBOM output should display a summary."""
        result = runner.invoke(cli, ["sbom", str(clean_claude_skill_dir)])
        assert "ASBOM written to" in result.output


class TestSbomCustomOutput:
    """Tests for the --output option."""

    def test_custom_output_path(
        self, runner: CliRunner, clean_claude_skill_dir: Path, tmp_path: Path
    ) -> None:
        """SBOM with --output should write to the specified path."""
        custom_path = tmp_path / "my-sbom.json"
        result = runner.invoke(
            cli,
            ["sbom", str(clean_claude_skill_dir), "-o", str(custom_path)],
        )
        assert result.exit_code == 0
        assert custom_path.exists()
        data = json.loads(custom_path.read_text())
        assert data["bomFormat"] == "CycloneDX"


class TestSbomProjectMetadata:
    """Tests for --project-name and --project-version options."""

    def test_custom_project_name(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """SBOM should use the specified project name."""
        runner.invoke(
            cli,
            ["sbom", str(clean_claude_skill_dir),
             "--project-name", "my-agent"],
        )
        asbom_file = clean_claude_skill_dir / "asbom.cdx.json"
        data = json.loads(asbom_file.read_text())
        assert data["metadata"]["component"]["name"] == "my-agent"

    def test_custom_project_version(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """SBOM should use the specified project version."""
        runner.invoke(
            cli,
            ["sbom", str(clean_claude_skill_dir),
             "--project-version", "2.1.0"],
        )
        asbom_file = clean_claude_skill_dir / "asbom.cdx.json"
        data = json.loads(asbom_file.read_text())
        assert data["metadata"]["component"]["version"] == "2.1.0"
