"""Tests for ``skillfortify dashboard`` command.

Verifies:
    - Dashboard generation for empty directories (exit code 2).
    - Dashboard generation with skills produces HTML file.
    - Custom output path via --output.
    - Custom title via --title.
    - Generated HTML contains expected structure.
    - --open flag does not crash (browser open is mocked).
    - DashboardGenerator.render() returns valid HTML on empty input.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from skillfortify.cli.main import cli
from skillfortify.dashboard.generator import DashboardGenerator


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CliRunner for invoking commands."""
    return CliRunner()


class TestDashboardEmptyDirectory:
    """Tests for dashboard generation on directories with no skills."""

    def test_empty_dir_exits_with_code_2(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Dashboard on empty directory should exit with code 2."""
        result = runner.invoke(cli, ["dashboard", str(empty_dir)])
        assert result.exit_code == 2

    def test_empty_dir_shows_message(
        self, runner: CliRunner, empty_dir: Path
    ) -> None:
        """Empty dashboard should display informative message."""
        result = runner.invoke(cli, ["dashboard", str(empty_dir)])
        assert "No skills found" in result.output


class TestDashboardGeneration:
    """Tests for successful dashboard generation."""

    def test_creates_html_file(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Dashboard should create an HTML file in the target directory."""
        result = runner.invoke(cli, ["dashboard", str(clean_claude_skill_dir)])
        assert result.exit_code == 0
        html_file = clean_claude_skill_dir / "skillfortify-report.html"
        assert html_file.exists()

    def test_html_is_valid_structure(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Generated HTML should contain expected structure."""
        runner.invoke(cli, ["dashboard", str(clean_claude_skill_dir)])
        html_file = clean_claude_skill_dir / "skillfortify-report.html"
        content = html_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<title>" in content
        assert "SkillFortify" in content

    def test_html_contains_scan_data(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Generated HTML should embed scan data as JSON."""
        runner.invoke(cli, ["dashboard", str(clean_claude_skill_dir)])
        html_file = clean_claude_skill_dir / "skillfortify-report.html"
        content = html_file.read_text(encoding="utf-8")
        assert "__SKILLFORTIFY_DATA__" in content

    def test_output_shows_summary(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Dashboard output should display a summary line."""
        result = runner.invoke(cli, ["dashboard", str(clean_claude_skill_dir)])
        assert "Dashboard generated" in result.output
        assert "Skills:" in result.output

    def test_malicious_skill_generates_report(
        self, runner: CliRunner, malicious_claude_skill_dir: Path
    ) -> None:
        """Dashboard should work for directories with unsafe skills."""
        result = runner.invoke(
            cli, ["dashboard", str(malicious_claude_skill_dir)]
        )
        assert result.exit_code == 0
        html_file = malicious_claude_skill_dir / "skillfortify-report.html"
        assert html_file.exists()


class TestDashboardCustomOutput:
    """Tests for the --output option."""

    def test_custom_output_path(
        self, runner: CliRunner, clean_claude_skill_dir: Path, tmp_path: Path
    ) -> None:
        """Dashboard with --output should write to the specified path."""
        custom = tmp_path / "my-report.html"
        result = runner.invoke(
            cli,
            ["dashboard", str(clean_claude_skill_dir), "-o", str(custom)],
        )
        assert result.exit_code == 0
        assert custom.exists()

    def test_custom_output_nested_dir(
        self, runner: CliRunner, clean_claude_skill_dir: Path, tmp_path: Path
    ) -> None:
        """Dashboard should create parent directories for output path."""
        nested = tmp_path / "sub" / "dir" / "report.html"
        result = runner.invoke(
            cli,
            ["dashboard", str(clean_claude_skill_dir), "-o", str(nested)],
        )
        assert result.exit_code == 0
        assert nested.exists()


class TestDashboardCustomTitle:
    """Tests for the --title option."""

    def test_custom_title_in_html(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Custom title should appear in the generated HTML."""
        runner.invoke(
            cli,
            ["dashboard", str(clean_claude_skill_dir), "--title", "My Audit"],
        )
        html_file = clean_claude_skill_dir / "skillfortify-report.html"
        content = html_file.read_text(encoding="utf-8")
        assert "My Audit" in content

    def test_html_escapes_title(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """HTML special chars in title should be escaped."""
        runner.invoke(
            cli,
            ["dashboard", str(clean_claude_skill_dir),
             "--title", "<script>alert(1)</script>"],
        )
        html_file = clean_claude_skill_dir / "skillfortify-report.html"
        content = html_file.read_text(encoding="utf-8")
        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;" in content


class TestDashboardOpenFlag:
    """Tests for the --open flag (browser launch)."""

    def test_open_flag_calls_webbrowser(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """--open flag should call webbrowser.open."""
        with patch("skillfortify.cli.dashboard_cmd.webbrowser.open") as mock:
            result = runner.invoke(
                cli,
                ["dashboard", str(clean_claude_skill_dir), "--open"],
            )
            assert result.exit_code == 0
            mock.assert_called_once()

    def test_without_open_flag_no_browser(
        self, runner: CliRunner, clean_claude_skill_dir: Path
    ) -> None:
        """Without --open, webbrowser should NOT be called."""
        with patch("skillfortify.cli.dashboard_cmd.webbrowser.open") as mock:
            runner.invoke(
                cli, ["dashboard", str(clean_claude_skill_dir)]
            )
            mock.assert_not_called()


class TestDashboardGeneratorUnit:
    """Unit tests for the DashboardGenerator class."""

    def test_render_empty_inputs(self) -> None:
        """render() with empty lists should return valid HTML."""
        gen = DashboardGenerator()
        html = gen.render([], [])
        assert "<!DOCTYPE html>" in html
        assert "0" in html  # zero counts

    def test_render_custom_title(self) -> None:
        """render() should use the custom title."""
        gen = DashboardGenerator(title="Test Title")
        html = gen.render([], [])
        assert "Test Title" in html

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write() should create the output file."""
        gen = DashboardGenerator()
        out = tmp_path / "test.html"
        result = gen.write(out)
        assert out.exists()
        assert result == out.resolve()
