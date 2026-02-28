"""Base classes and data models for registry scanning.

Defines the ``RegistryScanner`` abstract base class that all concrete
scanners (MCP, PyPI, npm) implement, along with the ``RegistryEntry``
and ``RegistryStats`` data models for scan results.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skillfortify.core.analyzer.models import AnalysisResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegistryEntry:
    """A single entry discovered in a remote skill registry.

    Attributes:
        name: Package or skill name as listed in the registry.
        url: Canonical URL for the registry entry (e.g. PyPI page, npm page).
        description: Short description from registry metadata.
        author: Author or maintainer name.
        version: Latest version string.
        stars: Star / download count (0 if unavailable).
        last_updated: ISO-8601 date string of the last update.
    """

    name: str
    url: str
    description: str = ""
    author: str = ""
    version: str = ""
    stars: int = 0
    last_updated: str = ""


@dataclass
class RegistryStats:
    """Aggregate statistics from a registry scan run.

    Attributes:
        registry_name: Human-readable name of the scanned registry.
        total_entries: Number of entries discovered in the registry.
        scanned: Number of entries that were actually analyzed.
        safe: Number of entries that passed analysis (no findings).
        unsafe: Number of entries with one or more findings.
        critical_findings: Total count of CRITICAL severity findings.
    """

    registry_name: str
    total_entries: int = 0
    scanned: int = 0
    safe: int = 0
    unsafe: int = 0
    critical_findings: int = 0


# ---------------------------------------------------------------------------
# Abstract base scanner
# ---------------------------------------------------------------------------


class RegistryScanner(ABC):
    """Abstract base class for remote registry scanners.

    Subclasses must implement ``fetch_entries`` and ``scan_entry``.
    The ``scan_registry`` method orchestrates full scans using those
    two primitives.
    """

    @property
    @abstractmethod
    def registry_name(self) -> str:
        """Human-readable name of this registry (e.g. 'MCP Registry')."""

    @abstractmethod
    async def fetch_entries(
        self, *, limit: int = 100, keyword: str = ""
    ) -> list[RegistryEntry]:
        """Fetch entries from the remote registry.

        Args:
            limit: Maximum number of entries to return.
            keyword: Optional search keyword to filter results.

        Returns:
            List of discovered registry entries.
        """

    @abstractmethod
    async def scan_entry(self, entry: RegistryEntry) -> AnalysisResult:
        """Analyze a single registry entry for security issues.

        Args:
            entry: The registry entry to analyze.

        Returns:
            AnalysisResult with findings (may be empty if safe).
        """

    async def scan_registry(
        self, *, limit: int = 100, keyword: str = ""
    ) -> tuple[list[AnalysisResult], RegistryStats]:
        """Fetch and scan entries, returning results and aggregate stats.

        This is the primary entry point for running a full registry scan.
        Network errors during individual entry scans are logged but do not
        abort the entire scan.

        Args:
            limit: Maximum number of entries to fetch and scan.
            keyword: Optional search keyword.

        Returns:
            Tuple of (list of AnalysisResult, RegistryStats).
        """
        entries = await self.fetch_entries(limit=limit, keyword=keyword)
        results: list[AnalysisResult] = []
        stats = RegistryStats(
            registry_name=self.registry_name,
            total_entries=len(entries),
        )

        for entry in entries:
            try:
                result = await self.scan_entry(entry)
                results.append(result)
                stats.scanned += 1
                if result.is_safe:
                    stats.safe += 1
                else:
                    stats.unsafe += 1
                    stats.critical_findings += sum(
                        1 for f in result.findings if f.severity.name == "CRITICAL"
                    )
            except Exception:
                logger.warning("Failed to scan entry: %s", entry.name, exc_info=True)

        return results, stats
