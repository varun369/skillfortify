"""npm registry scanner for agent tool packages.

Searches the npm registry for packages matching agent-skill keywords
(@modelcontextprotocol, mcp-server, agent-skill) and analyses each for
suspicious lifecycle scripts, typosquatting, and malicious patterns.

Usage::

    scanner = NpmScanner()
    results, stats = await scanner.scan_registry(limit=50, keyword="mcp-server")
"""

from __future__ import annotations

import logging
from typing import Any

from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.registry.base import RegistryEntry, RegistryScanner
from skillfortify.registry.http_client import fetch_json
from skillfortify.registry.patterns import (
    check_npm_scripts,
    matches_to_findings,
    typosquat_to_findings,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NPM_SEARCH_URL: str = "https://registry.npmjs.org/-/v1/search"
NPM_PACKAGE_URL: str = "https://registry.npmjs.org/{package}"

DEFAULT_KEYWORDS: list[str] = [
    "@modelcontextprotocol",
    "mcp-server",
    "agent-skill",
]

KNOWN_MALICIOUS_PACKAGES: frozenset[str] = frozenset({
    "mcp-server-malicious-test",
    "agent-skill-backdoor",
    "@fakemcp/server",
})


# ---------------------------------------------------------------------------
# npm Scanner
# ---------------------------------------------------------------------------


class NpmScanner(RegistryScanner):
    """Scanner for the npm registry."""

    @property
    def registry_name(self) -> str:
        """Return the human-readable registry name."""
        return "npm"

    async def fetch_entries(
        self, *, limit: int = 100, keyword: str = ""
    ) -> list[RegistryEntry]:
        """Search npm for agent-tool packages.

        Args:
            limit: Maximum number of entries to return.
            keyword: Search keyword (e.g. "mcp-server").

        Returns:
            List of RegistryEntry objects from npm.
        """
        keywords = [keyword] if keyword else DEFAULT_KEYWORDS
        entries: list[RegistryEntry] = []
        seen: set[str] = set()
        for kw in keywords:
            if len(entries) >= limit:
                break
            for pkg in await _search_npm(kw, limit=limit - len(entries)):
                if pkg.name not in seen:
                    seen.add(pkg.name)
                    entries.append(pkg)
        return entries[:limit]

    async def scan_entry(self, entry: RegistryEntry) -> AnalysisResult:
        """Analyse a single npm package for security issues.

        Args:
            entry: The npm registry entry to scan.

        Returns:
            AnalysisResult with findings.
        """
        findings: list[Finding] = []

        if entry.name.lower() in KNOWN_MALICIOUS_PACKAGES:
            findings.append(Finding(
                skill_name=entry.name, severity=Severity.CRITICAL,
                message=f"Package '{entry.name}' is in the known-malicious list",
                attack_class="known_malicious",
                finding_type="blocklist_match", evidence=entry.name,
            ))

        findings.extend(typosquat_to_findings(entry.name))

        metadata = await _fetch_package_metadata(entry.name)
        if metadata:
            findings.extend(_check_scripts(entry.name, metadata))
            findings.extend(_check_provenance(entry.name, metadata))

        if entry.description:
            findings.extend(matches_to_findings(entry.name, entry.description))

        return AnalysisResult(
            skill_name=f"npm:{entry.name}",
            is_safe=len(findings) == 0,
            findings=findings,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _search_npm(keyword: str, *, limit: int = 50) -> list[RegistryEntry]:
    """Search npm registry for packages matching a keyword."""
    params = {"text": keyword, "size": str(min(limit, 250))}
    data = await fetch_json(NPM_SEARCH_URL, params=params)
    if not isinstance(data, dict):
        return []
    entries: list[RegistryEntry] = []
    for obj in data.get("objects", []):
        entry = _npm_object_to_entry(obj)
        if entry:
            entries.append(entry)
    return entries[:limit]


def _npm_object_to_entry(obj: Any) -> RegistryEntry | None:
    """Convert an npm search result object to a RegistryEntry."""
    if not isinstance(obj, dict):
        return None
    package = obj.get("package", {})
    if not isinstance(package, dict):
        return None
    name = package.get("name", "")
    if not name:
        return None
    publisher = package.get("publisher", {})
    author_name = publisher.get("username", "") if isinstance(publisher, dict) else ""
    links = package.get("links", {})
    url = links.get("npm", f"https://www.npmjs.com/package/{name}") if isinstance(links, dict) else ""
    return RegistryEntry(
        name=str(name), url=str(url),
        description=str(package.get("description", ""))[:500],
        author=str(author_name),
        version=str(package.get("version", "")),
        stars=0, last_updated=str(package.get("date", "")),
    )


async def _fetch_package_metadata(name: str) -> dict[str, Any]:
    """Fetch full npm package metadata."""
    url = NPM_PACKAGE_URL.format(package=name)
    data = await fetch_json(url)
    return data if isinstance(data, dict) else {}


def _check_scripts(name: str, metadata: dict[str, Any]) -> list[Finding]:
    """Check npm package for suspicious lifecycle scripts."""
    latest = metadata.get("dist-tags", {}).get("latest", "")
    version_data = metadata.get("versions", {}).get(latest, {})
    scripts = version_data.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    findings: list[Finding] = []
    for m in check_npm_scripts(scripts):
        findings.append(Finding(
            skill_name=name,
            severity=Severity.CRITICAL if m.is_critical else Severity.HIGH,
            message=m.description, attack_class=m.category,
            finding_type="script_analysis", evidence=m.evidence,
        ))
    return findings


def _check_provenance(name: str, metadata: dict[str, Any]) -> list[Finding]:
    """Check package provenance metadata."""
    if not metadata.get("repository"):
        return [Finding(
            skill_name=name, severity=Severity.LOW,
            message="Package has no linked source repository",
            attack_class="missing_provenance",
            finding_type="metadata_check", evidence="repository=None",
        )]
    return []
