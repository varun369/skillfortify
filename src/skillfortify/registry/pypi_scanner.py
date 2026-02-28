"""PyPI registry scanner for agent tool packages.

Searches the Python Package Index for packages matching agent-tool
keywords (mcp-server, langchain-tool, agent-tool, crewai-tool) and
analyses each for suspicious metadata, dangerous dependencies, and
known malicious patterns.

Usage::

    scanner = PyPIScanner()
    results, stats = await scanner.scan_registry(limit=50, keyword="mcp-server")
"""

from __future__ import annotations

import logging
from typing import Any

from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.registry.base import RegistryEntry, RegistryScanner
from skillfortify.registry.http_client import fetch_json
from skillfortify.registry.patterns import matches_to_findings, typosquat_to_findings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PYPI_JSON_API: str = "https://pypi.org/pypi/{package}/json"

DEFAULT_KEYWORDS: list[str] = [
    "mcp-server",
    "langchain-tool",
    "agent-tool",
    "crewai-tool",
]

KNOWN_MALICIOUS_PACKAGES: frozenset[str] = frozenset({
    "mcp-server-exploit",
    "langchain-malware",
    "agent-tool-backdoor",
})

SUSPICIOUS_DEPENDENCIES: frozenset[str] = frozenset({
    "pycryptoenv",
    "pycryptosys",
    "colorwin",
    "py-obfuscate",
    "stealer",
})


# ---------------------------------------------------------------------------
# PyPI Scanner
# ---------------------------------------------------------------------------


class PyPIScanner(RegistryScanner):
    """Scanner for the Python Package Index (PyPI)."""

    @property
    def registry_name(self) -> str:
        """Return the human-readable registry name."""
        return "PyPI"

    async def fetch_entries(
        self, *, limit: int = 100, keyword: str = ""
    ) -> list[RegistryEntry]:
        """Search PyPI for agent-tool packages.

        Args:
            limit: Maximum number of entries to return.
            keyword: Search keyword (e.g. "mcp-server").

        Returns:
            List of RegistryEntry objects from PyPI.
        """
        keywords = [keyword] if keyword else DEFAULT_KEYWORDS
        entries: list[RegistryEntry] = []
        seen: set[str] = set()
        for kw in keywords:
            if len(entries) >= limit:
                break
            for pkg in await _search_pypi(kw, limit=limit - len(entries)):
                if pkg.name not in seen:
                    seen.add(pkg.name)
                    entries.append(pkg)
        return entries[:limit]

    async def scan_entry(self, entry: RegistryEntry) -> AnalysisResult:
        """Analyse a single PyPI package for security issues.

        Args:
            entry: The PyPI registry entry to scan.

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
            findings.extend(_check_dependencies(entry.name, metadata))
            findings.extend(_check_metadata_patterns(entry.name, metadata))

        if entry.description:
            findings.extend(matches_to_findings(entry.name, entry.description))

        return AnalysisResult(
            skill_name=f"pypi:{entry.name}",
            is_safe=len(findings) == 0,
            findings=findings,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _search_pypi(keyword: str, *, limit: int = 50) -> list[RegistryEntry]:
    """Search PyPI for packages matching a keyword via the JSON API."""
    url = PYPI_JSON_API.format(package=keyword)
    data = await fetch_json(url)
    if not data or not isinstance(data, dict):
        return []
    info = data.get("info", {})
    return [_info_to_entry(info)] if info else []


async def _fetch_package_metadata(name: str) -> dict[str, Any]:
    """Fetch full package metadata from PyPI JSON API."""
    url = PYPI_JSON_API.format(package=name)
    data = await fetch_json(url)
    return data if isinstance(data, dict) else {}


def _info_to_entry(info: dict[str, Any]) -> RegistryEntry:
    """Convert PyPI package info dict to RegistryEntry."""
    name = str(info.get("name", ""))
    return RegistryEntry(
        name=name,
        url=str(info.get("project_url", f"https://pypi.org/project/{name}/")),
        description=str(info.get("summary", ""))[:500],
        author=str(info.get("author", info.get("maintainer", ""))),
        version=str(info.get("version", "")),
        stars=0, last_updated="",
    )


def _check_dependencies(name: str, metadata: dict[str, Any]) -> list[Finding]:
    """Flag suspicious dependencies in the package requirements."""
    findings: list[Finding] = []
    requires = (metadata.get("info", {}).get("requires_dist") or [])
    for req in requires:
        req_norm = req.split()[0].lower().replace("-", "").replace("_", "")
        for suspicious in SUSPICIOUS_DEPENDENCIES:
            if suspicious.lower().replace("-", "").replace("_", "") in req_norm:
                findings.append(Finding(
                    skill_name=name, severity=Severity.CRITICAL,
                    message=f"Suspicious dependency: {req.split()[0]}",
                    attack_class="malicious_dependency",
                    finding_type="dependency_check", evidence=req,
                ))
    return findings


def _check_metadata_patterns(name: str, metadata: dict[str, Any]) -> list[Finding]:
    """Check metadata for suspicious patterns (empty author, etc.)."""
    findings: list[Finding] = []
    info = metadata.get("info", {})
    author = info.get("author", "") or info.get("maintainer", "")
    if not author:
        findings.append(Finding(
            skill_name=name, severity=Severity.MEDIUM,
            message="Package has no declared author or maintainer",
            attack_class="missing_provenance",
            finding_type="metadata_check",
            evidence="author=None, maintainer=None",
        ))
    desc = info.get("description", "")
    if desc:
        findings.extend(matches_to_findings(name, desc[:5000]))
    return findings
