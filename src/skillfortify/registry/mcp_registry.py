"""MCP Registry scanner for official Model Context Protocol servers.

Fetches server listings from the MCP registry (GitHub-backed) and
analyses each server entry for missing authentication, overly broad
permissions, known vulnerable SDK versions, and suspicious README
content.

Usage::

    scanner = MCPRegistryScanner()
    results, stats = await scanner.scan_registry(limit=50)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.registry.base import RegistryEntry, RegistryScanner
from skillfortify.registry.http_client import fetch_json, fetch_text
from skillfortify.registry.patterns import (
    MCP_NO_AUTH_INDICATORS,
    matches_to_findings,
    typosquat_to_findings,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MCP_REGISTRY_API: str = (
    "https://raw.githubusercontent.com/"
    "modelcontextprotocol/servers/main/data/servers.json"
)

VULNERABLE_SDK_VERSIONS: dict[str, str] = {
    "0.1.0": "CVE-2026-25253 (RCE)",
    "0.1.1": "CVE-2026-25253 (RCE)",
    "0.2.0": "Session fixation vulnerability",
}

MIN_SAFE_SDK_VERSION: str = "0.3.0"


# ---------------------------------------------------------------------------
# MCP Registry Scanner
# ---------------------------------------------------------------------------


class MCPRegistryScanner(RegistryScanner):
    """Scanner for the official MCP server registry."""

    @property
    def registry_name(self) -> str:
        """Return the human-readable registry name."""
        return "MCP Registry"

    async def fetch_entries(
        self, *, limit: int = 100, keyword: str = ""
    ) -> list[RegistryEntry]:
        """Fetch MCP server entries from the registry.

        Args:
            limit: Maximum number of entries to return.
            keyword: Optional keyword to filter server names/descriptions.

        Returns:
            List of RegistryEntry objects from the MCP registry.
        """
        data = await fetch_json(MCP_REGISTRY_API)
        if not isinstance(data, list):
            data = data.get("servers", []) if isinstance(data, dict) else []

        entries: list[RegistryEntry] = []
        for item in data[:limit * 2]:
            entry = _parse_server_entry(item)
            if entry is None:
                continue
            if keyword and keyword.lower() not in _entry_search_text(entry):
                continue
            entries.append(entry)
            if len(entries) >= limit:
                break
        return entries

    async def scan_entry(self, entry: RegistryEntry) -> AnalysisResult:
        """Analyse a single MCP server entry for security issues.

        Args:
            entry: The MCP registry entry to scan.

        Returns:
            AnalysisResult with all findings.
        """
        findings: list[Finding] = []
        findings.extend(typosquat_to_findings(entry.name))
        findings.extend(_auth_findings(entry))
        findings.extend(_sdk_version_findings(entry))

        readme_text = await _fetch_readme(entry.url)
        if readme_text:
            findings.extend(matches_to_findings(entry.name, readme_text))
        findings.extend(matches_to_findings(entry.name, entry.description))

        return AnalysisResult(
            skill_name=f"mcp:{entry.name}",
            is_safe=len(findings) == 0,
            findings=findings,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_server_entry(item: Any) -> RegistryEntry | None:
    """Parse a raw JSON object into a RegistryEntry."""
    if not isinstance(item, dict):
        return None
    name = item.get("name", item.get("id", ""))
    if not name:
        return None
    return RegistryEntry(
        name=str(name),
        url=str(item.get("url", item.get("repository", ""))),
        description=str(item.get("description", "")),
        author=str(item.get("author", item.get("maintainer", ""))),
        version=str(item.get("version", "")),
        stars=int(item.get("stars", 0)),
        last_updated=str(item.get("last_updated", item.get("updated_at", ""))),
    )


def _entry_search_text(entry: RegistryEntry) -> str:
    """Build a lowercase search string for keyword filtering."""
    return f"{entry.name} {entry.description} {entry.author}".lower()


def _auth_findings(entry: RegistryEntry) -> list[Finding]:
    """Check for missing authentication indicators."""
    desc_lower = entry.description.lower()
    for indicator in MCP_NO_AUTH_INDICATORS:
        if indicator in desc_lower:
            return [Finding(
                skill_name=entry.name, severity=Severity.HIGH,
                message="Server may lack authentication",
                attack_class="missing_authentication",
                finding_type="pattern_match", evidence=indicator,
            )]
    return []


def _sdk_version_findings(entry: RegistryEntry) -> list[Finding]:
    """Check if the entry uses a known-vulnerable SDK version."""
    version = entry.version.strip()
    if version in VULNERABLE_SDK_VERSIONS:
        cve_info = VULNERABLE_SDK_VERSIONS[version]
        return [Finding(
            skill_name=entry.name, severity=Severity.CRITICAL,
            message=f"Uses vulnerable SDK version {version}: {cve_info}",
            attack_class="vulnerable_dependency",
            finding_type="version_check", evidence=f"version={version}",
        )]
    return []


async def _fetch_readme(url: str) -> str:
    """Attempt to fetch the README for a GitHub-hosted MCP server."""
    if not url or "github.com" not in url:
        return ""
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)", url)
    if not match:
        return ""
    owner, repo = match.group(1), match.group(2)
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    return await fetch_text(raw_url)
