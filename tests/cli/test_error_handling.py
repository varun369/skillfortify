"""Tests for CLI error handling edge cases.

Verifies graceful handling of:
    - Non-existent paths for scan command.
    - Non-existent files for verify command.
    - Scan invoked with no arguments.
    - Lock on an empty directory.
    - SBOM with permission denied on output path.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillfortify.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CliRunner for invoking commands."""
    return CliRunner()


class TestScanErrorHandling:
    """Tests for ``skillfortify scan`` error paths."""

    def test_nonexistent_path_graceful_error(
        self, runner: CliRunner
    ) -> None:
        """scan with non-existent path should produce an error, exit != 0."""
        result = runner.invoke(cli, ["scan", "/nonexistent/path/xyz"])
        # Click's exists=True on Path argument catches this before our code.
        assert result.exit_code == 2
        assert "Error" in result.output or "does not exist" in result.output

    def test_scan_no_arguments_shows_help(
        self, runner: CliRunner
    ) -> None:
        """scan with no arguments should display usage/help text."""
        result = runner.invoke(cli, ["scan"])
        assert result.exit_code == 2
        # Click displays "Missing argument" when a required arg is absent.
        assert "Missing argument" in result.output or "Usage" in result.output


class TestVerifyErrorHandling:
    """Tests for ``skillfortify verify`` error paths."""

    def test_nonexistent_file_graceful_error(
        self, runner: CliRunner
    ) -> None:
        """verify with a non-existent file should produce a graceful error."""
        result = runner.invoke(cli, ["verify", "/nonexistent/file.md"])
        assert result.exit_code == 2
        assert (
            "Error" in result.output
            or "does not exist" in result.output
        )


class TestLockErrorHandling:
    """Tests for ``skillfortify lock`` error paths."""

    def test_lock_empty_directory_exits_code_2(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """lock on an empty directory should report no skills and exit 2."""
        result = runner.invoke(cli, ["lock", str(tmp_path)])
        assert result.exit_code == 2
        assert "No skills found" in result.output


class TestSbomErrorHandling:
    """Tests for ``skillfortify sbom`` error paths."""

    def test_sbom_permission_denied_on_output(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """sbom with permission-denied output path should show an error.

        We create a read-only directory and try to write a file into it.
        The Lockfile.write / generator.write_json should fail gracefully.
        """
        # Create a Claude skill so sbom has something to process.
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text(
            "---\nname: test\n---\nA test skill.\n"
        )

        # Create a read-only directory for the output.
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        target_file = readonly_dir / "asbom.cdx.json"

        # Make it read-only so write fails.
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            result = runner.invoke(
                cli,
                ["sbom", str(tmp_path), "-o", str(target_file)],
            )
            # Should either exit non-zero or contain an error indication.
            # The actual behavior depends on whether Click catches the
            # OSError or it propagates. Both are acceptable error paths.
            assert result.exit_code != 0 or "Error" in result.output
        finally:
            # Restore permissions for cleanup.
            readonly_dir.chmod(stat.S_IRWXU)
