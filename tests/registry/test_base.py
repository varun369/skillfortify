"""Tests for registry base classes: RegistryEntry, RegistryStats, RegistryScanner.

Validates the abstract base class contract, dataclass construction,
and the scan_registry orchestration logic with a concrete test scanner.
"""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError

import pytest

from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.registry.base import RegistryEntry, RegistryScanner, RegistryStats


# ---------------------------------------------------------------------------
# Concrete test scanner (for testing the ABC's scan_registry method)
# ---------------------------------------------------------------------------


class _MockScanner(RegistryScanner):
    """Minimal concrete scanner for testing base class behaviour."""

    def __init__(
        self,
        entries: list[RegistryEntry] | None = None,
        scan_results: dict[str, AnalysisResult] | None = None,
        scan_error_names: set[str] | None = None,
    ) -> None:
        self._entries = entries or []
        self._scan_results = scan_results or {}
        self._scan_error_names = scan_error_names or set()

    @property
    def registry_name(self) -> str:
        return "MockRegistry"

    async def fetch_entries(
        self, *, limit: int = 100, keyword: str = ""
    ) -> list[RegistryEntry]:
        result = self._entries[:limit]
        if keyword:
            result = [e for e in result if keyword.lower() in e.name.lower()]
        return result

    async def scan_entry(self, entry: RegistryEntry) -> AnalysisResult:
        if entry.name in self._scan_error_names:
            raise RuntimeError(f"Simulated scan error for {entry.name}")
        if entry.name in self._scan_results:
            return self._scan_results[entry.name]
        return AnalysisResult(skill_name=entry.name, is_safe=True)


# ---------------------------------------------------------------------------
# RegistryEntry tests
# ---------------------------------------------------------------------------


class TestRegistryEntry:
    """Tests for the RegistryEntry dataclass."""

    def test_create_minimal(self) -> None:
        """Entry with only required fields."""
        entry = RegistryEntry(name="test-skill", url="https://example.com")
        assert entry.name == "test-skill"
        assert entry.url == "https://example.com"
        assert entry.description == ""
        assert entry.stars == 0

    def test_create_full(self) -> None:
        """Entry with all fields populated."""
        entry = RegistryEntry(
            name="cool-tool",
            url="https://github.com/owner/repo",
            description="A cool tool",
            author="author",
            version="1.0.0",
            stars=42,
            last_updated="2026-02-27",
        )
        assert entry.stars == 42
        assert entry.version == "1.0.0"
        assert entry.last_updated == "2026-02-27"

    def test_frozen(self) -> None:
        """RegistryEntry is immutable."""
        entry = RegistryEntry(name="x", url="y")
        with pytest.raises(FrozenInstanceError):
            entry.name = "z"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Two entries with same fields are equal."""
        a = RegistryEntry(name="a", url="b")
        b = RegistryEntry(name="a", url="b")
        assert a == b


# ---------------------------------------------------------------------------
# RegistryStats tests
# ---------------------------------------------------------------------------


class TestRegistryStats:
    """Tests for the RegistryStats dataclass."""

    def test_defaults(self) -> None:
        """Stats initialise with zero counters."""
        stats = RegistryStats(registry_name="Test")
        assert stats.registry_name == "Test"
        assert stats.total_entries == 0
        assert stats.scanned == 0
        assert stats.safe == 0
        assert stats.unsafe == 0
        assert stats.critical_findings == 0

    def test_mutable(self) -> None:
        """Stats are mutable (counters get incremented during scan)."""
        stats = RegistryStats(registry_name="Test")
        stats.scanned += 1
        assert stats.scanned == 1


# ---------------------------------------------------------------------------
# RegistryScanner ABC + scan_registry tests
# ---------------------------------------------------------------------------


class TestRegistryScanner:
    """Tests for the RegistryScanner abstract base class."""

    def test_cannot_instantiate_abc(self) -> None:
        """ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RegistryScanner()  # type: ignore[abstract]

    def test_scan_registry_empty(self) -> None:
        """scan_registry with no entries returns empty results."""
        scanner = _MockScanner(entries=[])
        results, stats = asyncio.run(scanner.scan_registry(limit=10))
        assert results == []
        assert stats.total_entries == 0
        assert stats.scanned == 0

    def test_scan_registry_all_safe(self) -> None:
        """scan_registry counts safe entries correctly."""
        entries = [
            RegistryEntry(name="safe-a", url="https://a.com"),
            RegistryEntry(name="safe-b", url="https://b.com"),
        ]
        scanner = _MockScanner(entries=entries)
        results, stats = asyncio.run(scanner.scan_registry())
        assert len(results) == 2
        assert stats.scanned == 2
        assert stats.safe == 2
        assert stats.unsafe == 0

    def test_scan_registry_with_unsafe(self) -> None:
        """scan_registry counts unsafe entries correctly."""
        entries = [RegistryEntry(name="bad", url="https://x.com")]
        scan_results = {
            "bad": AnalysisResult(
                skill_name="bad",
                is_safe=False,
                findings=[
                    Finding(
                        skill_name="bad",
                        severity=Severity.CRITICAL,
                        message="Bad!",
                        attack_class="test",
                        finding_type="test",
                        evidence="test",
                    )
                ],
            )
        }
        scanner = _MockScanner(entries=entries, scan_results=scan_results)
        results, stats = asyncio.run(scanner.scan_registry())
        assert stats.unsafe == 1
        assert stats.critical_findings == 1

    def test_scan_registry_handles_errors(self) -> None:
        """scan_registry logs and skips entries that fail to scan."""
        entries = [
            RegistryEntry(name="good", url="https://a.com"),
            RegistryEntry(name="error", url="https://b.com"),
        ]
        scanner = _MockScanner(entries=entries, scan_error_names={"error"})
        results, stats = asyncio.run(scanner.scan_registry())
        assert len(results) == 1
        assert stats.scanned == 1
        assert stats.total_entries == 2

    def test_scan_registry_respects_limit(self) -> None:
        """fetch_entries limit is passed through."""
        entries = [
            RegistryEntry(name=f"pkg-{i}", url=f"https://{i}.com")
            for i in range(10)
        ]
        scanner = _MockScanner(entries=entries)
        results, stats = asyncio.run(scanner.scan_registry(limit=3))
        assert len(results) == 3
        assert stats.total_entries == 3

    def test_scan_registry_with_keyword(self) -> None:
        """fetch_entries keyword filtering works."""
        entries = [
            RegistryEntry(name="mcp-server-a", url="https://a.com"),
            RegistryEntry(name="langchain-tool-b", url="https://b.com"),
        ]
        scanner = _MockScanner(entries=entries)
        results, stats = asyncio.run(
            scanner.scan_registry(keyword="mcp")
        )
        assert len(results) == 1
        assert results[0].skill_name == "mcp-server-a"
