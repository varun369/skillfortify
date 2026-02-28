"""Tests for the ``skillfortify registry-scan`` CLI command.

All scanner methods are mocked — no real HTTP calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from skillfortify.cli.main import cli
from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.registry.base import RegistryEntry, RegistryStats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner() -> CliRunner:
    """Click CLI test runner."""
    return CliRunner()


def _safe_result() -> AnalysisResult:
    """A safe analysis result."""
    return AnalysisResult(skill_name="test:safe-pkg", is_safe=True)


def _unsafe_result() -> AnalysisResult:
    """An unsafe analysis result with one CRITICAL finding."""
    return AnalysisResult(
        skill_name="test:bad-pkg",
        is_safe=False,
        findings=[
            Finding(
                skill_name="bad-pkg",
                severity=Severity.CRITICAL,
                message="Known malicious",
                attack_class="known_malicious",
                finding_type="blocklist_match",
                evidence="bad-pkg",
            )
        ],
    )


def _mock_stats(name: str = "MockRegistry") -> RegistryStats:
    """Sample RegistryStats."""
    return RegistryStats(
        registry_name=name,
        total_entries=2,
        scanned=2,
        safe=1,
        unsafe=1,
        critical_findings=1,
    )


def _patch_scanner(registry_type: str, results: list, stats: RegistryStats) -> Any:
    """Create a context manager that patches the scanner for a given registry.

    Args:
        registry_type: 'mcp', 'pypi', or 'npm'.
        results: List of AnalysisResult to return.
        stats: RegistryStats to return.
    """
    mock_scanner = MagicMock()
    mock_scanner.scan_registry = AsyncMock(return_value=(results, stats))

    module_map = {
        "mcp": "skillfortify.cli.registry_cmd.MCPRegistryScanner",
        "pypi": "skillfortify.cli.registry_cmd.PyPIScanner",
        "npm": "skillfortify.cli.registry_cmd.NpmScanner",
    }

    # We need to patch the import path within registry_cmd
    target = f"skillfortify.registry.{_scanner_module(registry_type)}"
    return patch(
        module_map.get(registry_type, module_map["mcp"]),
        return_value=mock_scanner,
    )


def _scanner_module(registry_type: str) -> str:
    """Map registry type to scanner module path."""
    mapping = {
        "mcp": "mcp_registry.MCPRegistryScanner",
        "pypi": "pypi_scanner.PyPIScanner",
        "npm": "npm_scanner.NpmScanner",
    }
    return mapping.get(registry_type, "mcp_registry.MCPRegistryScanner")


# We need a simpler approach: patch _get_scanner directly
def _patch_get_scanner(results: list, stats: RegistryStats) -> Any:
    """Patch _get_scanner to return a mock scanner."""
    mock_scanner = MagicMock()
    mock_scanner.scan_registry = AsyncMock(return_value=(results, stats))
    return patch(
        "skillfortify.cli.registry_cmd._get_scanner",
        return_value=mock_scanner,
    )


# ---------------------------------------------------------------------------
# Tests: basic invocation
# ---------------------------------------------------------------------------


class TestRegistryScanCommand:
    """Tests for the registry-scan CLI command."""

    def test_help_text(self, runner: CliRunner) -> None:
        """Command shows help text with --help."""
        result = runner.invoke(cli, ["registry-scan", "--help"])
        assert result.exit_code == 0
        assert "registry" in result.output.lower()

    def test_mcp_text_output(self, runner: CliRunner) -> None:
        """MCP scan with text output works."""
        stats = _mock_stats("MCP Registry")
        with _patch_get_scanner([_safe_result()], stats):
            result = runner.invoke(cli, ["registry-scan", "mcp"])
        # Exit code 0 because all safe
        assert "MCP Registry" in result.output

    def test_pypi_text_output(self, runner: CliRunner) -> None:
        """PyPI scan with text output works."""
        stats = _mock_stats("PyPI")
        with _patch_get_scanner([_safe_result()], stats):
            result = runner.invoke(cli, ["registry-scan", "pypi"])
        assert "PyPI" in result.output

    def test_npm_text_output(self, runner: CliRunner) -> None:
        """npm scan with text output works."""
        stats = _mock_stats("npm")
        with _patch_get_scanner([_safe_result()], stats):
            result = runner.invoke(cli, ["registry-scan", "npm"])
        assert "npm" in result.output

    def test_json_output(self, runner: CliRunner) -> None:
        """JSON output is valid JSON with expected structure."""
        stats = _mock_stats("MCP Registry")
        with _patch_get_scanner([_safe_result()], stats):
            result = runner.invoke(
                cli, ["registry-scan", "mcp", "--format", "json"]
            )
        data = json.loads(result.output)
        assert "stats" in data
        assert "results" in data
        assert data["stats"]["registry_name"] == "MCP Registry"

    def test_unsafe_exit_code(self, runner: CliRunner) -> None:
        """Exit code 1 when unsafe entries found."""
        stats = _mock_stats()
        with _patch_get_scanner([_unsafe_result()], stats):
            result = runner.invoke(cli, ["registry-scan", "mcp"])
        assert result.exit_code == 1

    def test_safe_exit_code(self, runner: CliRunner) -> None:
        """Exit code 0 when all entries safe."""
        stats = RegistryStats(
            registry_name="Test", total_entries=1, scanned=1, safe=1
        )
        with _patch_get_scanner([_safe_result()], stats):
            result = runner.invoke(cli, ["registry-scan", "mcp"])
        assert result.exit_code == 0

    def test_limit_option(self, runner: CliRunner) -> None:
        """--limit option is accepted."""
        stats = _mock_stats()
        with _patch_get_scanner([], stats) as mock:
            result = runner.invoke(
                cli, ["registry-scan", "mcp", "--limit", "25"]
            )
        assert result.exit_code == 0

    def test_keyword_option(self, runner: CliRunner) -> None:
        """--keyword option is accepted."""
        stats = _mock_stats()
        with _patch_get_scanner([], stats):
            result = runner.invoke(
                cli, ["registry-scan", "pypi", "--keyword", "mcp-server"]
            )
        assert result.exit_code == 0

    def test_invalid_registry(self, runner: CliRunner) -> None:
        """Invalid registry name shows error."""
        result = runner.invoke(cli, ["registry-scan", "invalid"])
        assert result.exit_code != 0

    def test_json_findings_structure(self, runner: CliRunner) -> None:
        """JSON output includes finding details."""
        stats = _mock_stats()
        with _patch_get_scanner([_unsafe_result()], stats):
            result = runner.invoke(
                cli, ["registry-scan", "npm", "--format", "json"]
            )
        data = json.loads(result.output)
        assert len(data["results"]) == 1
        assert data["results"][0]["findings_count"] == 1
        assert data["results"][0]["findings"][0]["severity"] == "CRITICAL"
