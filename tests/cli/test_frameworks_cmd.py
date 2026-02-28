"""Tests for ``skillfortify frameworks`` command.

Verifies:
    - Command exits with code 0.
    - Output contains all 22 frameworks.
    - Output includes version header.
    - Output includes format identifiers.
    - Output includes detection patterns.
    - format_frameworks_table() is a pure function that never raises.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from skillfortify import __version__
from skillfortify.cli.frameworks_cmd import (
    _FRAMEWORKS,
    format_frameworks_table,
    frameworks_command,
)
from skillfortify.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CliRunner for invoking commands."""
    return CliRunner()


class TestFrameworksCommandBasic:
    """Basic invocation tests for the frameworks command."""

    def test_exits_with_code_0(self, runner: CliRunner) -> None:
        """Frameworks command is informational and always exits 0."""
        result = runner.invoke(cli, ["frameworks"])
        assert result.exit_code == 0

    def test_output_not_empty(self, runner: CliRunner) -> None:
        """Frameworks command should produce non-empty output."""
        result = runner.invoke(cli, ["frameworks"])
        assert len(result.output.strip()) > 0

    def test_contains_version(self, runner: CliRunner) -> None:
        """Output should include the current SkillFortify version."""
        result = runner.invoke(cli, ["frameworks"])
        assert __version__ in result.output

    def test_contains_framework_count(self, runner: CliRunner) -> None:
        """Output should state 22 supported frameworks."""
        result = runner.invoke(cli, ["frameworks"])
        assert "22" in result.output


class TestFrameworksCommandContent:
    """Verify all 22 framework entries appear in output."""

    def test_all_framework_names_present(self, runner: CliRunner) -> None:
        """Every framework human-readable name must appear."""
        result = runner.invoke(cli, ["frameworks"])
        for name, _, _ in _FRAMEWORKS:
            assert name in result.output, f"Missing framework: {name}"

    def test_all_format_ids_present(self, runner: CliRunner) -> None:
        """Every framework format identifier must appear."""
        result = runner.invoke(cli, ["frameworks"])
        for _, fmt, _ in _FRAMEWORKS:
            assert fmt in result.output, f"Missing format id: {fmt}"

    def test_all_detection_hints_present(self, runner: CliRunner) -> None:
        """Every framework detection pattern must appear."""
        result = runner.invoke(cli, ["frameworks"])
        for _, _, det in _FRAMEWORKS:
            assert det in result.output, f"Missing detection hint: {det}"

    def test_frameworks_count_matches_22(self) -> None:
        """The internal _FRAMEWORKS tuple must have exactly 22 entries."""
        assert len(_FRAMEWORKS) == 22

    def test_contains_scan_hint(self, runner: CliRunner) -> None:
        """Output should include a hint to run skillfortify scan."""
        result = runner.invoke(cli, ["frameworks"])
        assert "skillfortify scan" in result.output


class TestFormatFrameworksTable:
    """Tests for the pure format_frameworks_table() function."""

    def test_returns_string(self) -> None:
        """format_frameworks_table must return a string."""
        result = format_frameworks_table()
        assert isinstance(result, str)

    def test_never_raises(self) -> None:
        """The function must never raise on normal invocation."""
        table = format_frameworks_table()
        assert len(table) > 0

    def test_has_header_and_rows(self) -> None:
        """Output should have a header line plus 22 data rows."""
        table = format_frameworks_table()
        lines = [l for l in table.split("\n") if l.strip()]
        # At minimum: title + header + divider + 22 rows + hint = 26
        assert len(lines) >= 26

    def test_row_numbering_starts_at_1(self) -> None:
        """First framework row should be numbered 1."""
        table = format_frameworks_table()
        assert "  1  " in table or "  1 " in table

    def test_row_numbering_ends_at_22(self) -> None:
        """Last framework row should be numbered 22."""
        table = format_frameworks_table()
        assert " 22 " in table


class TestFrameworksDirectCommand:
    """Test the Click command object directly."""

    def test_direct_invoke(self, runner: CliRunner) -> None:
        """Invoke the command object directly (not via cli group)."""
        result = runner.invoke(frameworks_command)
        assert result.exit_code == 0
        assert "Claude Code Skills" in result.output
