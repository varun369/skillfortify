"""Prepare scan data for embedding in the HTML dashboard.

Transforms ``AnalysisResult`` and ``ParsedSkill`` objects into plain
dictionaries that can be safely serialised to JSON and embedded inside
the self-contained HTML report.

All public functions are pure transformations -- no side effects, no I/O.
They never raise on empty or malformed input; degenerate cases produce
sensible defaults (empty lists, zero counts).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from skillfortify.core.analyzer.models import AnalysisResult, Finding
from skillfortify.parsers.base import ParsedSkill


# -- Supported frameworks (22 parsers) ------------------------------------

SUPPORTED_FRAMEWORKS: tuple[str, ...] = (
    "claude",
    "mcp_config",
    "mcp_server",
    "openclaw",
    "openai_agents",
    "google_adk",
    "langchain",
    "crewai",
    "autogen",
    "dify",
    "composio",
    "semantic_kernel",
    "llamaindex",
    "n8n",
    "flowise",
    "mastra",
    "pydanticai",
    "agno",
    "camel",
    "metagpt",
    "haystack",
    "anthropic_sdk",
)


def prepare_executive_summary(
    results: list[AnalysisResult],
    skills: list[ParsedSkill],
) -> dict[str, Any]:
    """Build the executive-summary section data.

    Args:
        results: Analysis results (may be empty).
        skills: Parsed skills (may be empty).

    Returns:
        Dict with keys: total_skills, safe_count, unsafe_count,
        critical_count, high_count, medium_count, low_count,
        frameworks_detected, scan_timestamp.
    """
    total = len(results)
    safe = sum(1 for r in results if r.is_safe)
    unsafe = total - safe

    severity_counts = _count_severities(results)

    frameworks = _detect_frameworks(skills)

    return {
        "total_skills": total,
        "safe_count": safe,
        "unsafe_count": unsafe,
        "critical_count": severity_counts.get("CRITICAL", 0),
        "high_count": severity_counts.get("HIGH", 0),
        "medium_count": severity_counts.get("MEDIUM", 0),
        "low_count": severity_counts.get("LOW", 0),
        "frameworks_detected": frameworks,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
    }


def prepare_findings_table(
    results: list[AnalysisResult],
    skills: list[ParsedSkill],
) -> list[dict[str, str]]:
    """Flatten all findings into a list of row-dicts for the table.

    Args:
        results: Analysis results (may be empty).
        skills: Parsed skills used to look up format per skill name.

    Returns:
        List of dicts with keys: skill_name, format, severity,
        message, attack_class, finding_type, evidence.
    """
    format_map = {s.name: s.format for s in skills}
    rows: list[dict[str, str]] = []
    for result in results:
        for finding in result.findings:
            rows.append(_finding_to_row(finding, format_map))
    return rows


def prepare_capabilities_matrix(
    results: list[AnalysisResult],
) -> list[dict[str, Any]]:
    """Build the capabilities matrix: which resources each skill accesses.

    Args:
        results: Analysis results (may be empty).

    Returns:
        List of dicts with keys: skill_name, capabilities (dict of
        resource -> access level name).
    """
    matrix: list[dict[str, Any]] = []
    for result in results:
        caps = _extract_capabilities(result)
        if caps:
            matrix.append({
                "skill_name": result.skill_name,
                "capabilities": caps,
            })
    return matrix


def prepare_framework_coverage(
    skills: list[ParsedSkill],
) -> list[dict[str, Any]]:
    """Count skills per detected framework.

    Args:
        skills: Parsed skills (may be empty).

    Returns:
        List of dicts with keys: framework, count. Sorted by count desc.
    """
    counts: dict[str, int] = {}
    for skill in skills:
        fmt = skill.format or "unknown"
        counts[fmt] = counts.get(fmt, 0) + 1
    return sorted(
        [{"framework": k, "count": v} for k, v in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )


def encode_dashboard_json(
    results: list[AnalysisResult],
    skills: list[ParsedSkill],
) -> str:
    """Produce the complete JSON payload for the dashboard template.

    This is the single entry point that ``DashboardGenerator`` calls.

    Args:
        results: Analysis results (may be empty).
        skills: Parsed skills (may be empty).

    Returns:
        A JSON string (compact) safe for embedding in a ``<script>`` tag.
    """
    payload: dict[str, Any] = {
        "summary": prepare_executive_summary(results, skills),
        "findings": prepare_findings_table(results, skills),
        "capabilities": prepare_capabilities_matrix(results),
        "framework_coverage": prepare_framework_coverage(skills),
    }
    return json.dumps(payload, separators=(",", ":"))


# -- Private helpers -------------------------------------------------------


def _count_severities(
    results: list[AnalysisResult],
) -> dict[str, int]:
    """Count findings by severity name across all results."""
    counts: dict[str, int] = {}
    for result in results:
        for finding in result.findings:
            name = finding.severity.name
            counts[name] = counts.get(name, 0) + 1
    return counts


def _detect_frameworks(skills: list[ParsedSkill]) -> list[str]:
    """Return the unique set of detected framework format strings."""
    seen: set[str] = set()
    for skill in skills:
        if skill.format:
            seen.add(skill.format)
    return sorted(seen)


def _finding_to_row(
    finding: Finding,
    format_map: dict[str, str],
) -> dict[str, str]:
    """Convert a single Finding into a table-row dict."""
    return {
        "skill_name": finding.skill_name,
        "format": format_map.get(finding.skill_name, "unknown"),
        "severity": finding.severity.name,
        "message": finding.message,
        "attack_class": finding.attack_class,
        "finding_type": finding.finding_type,
        "evidence": _truncate(finding.evidence, 120),
    }


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _extract_capabilities(
    result: AnalysisResult,
) -> dict[str, str]:
    """Extract capability resource -> access level name from a result."""
    if result.inferred_capabilities is None:
        return {}
    caps: dict[str, str] = {}
    for cap in result.inferred_capabilities:
        caps[cap.resource] = cap.access.name
    return caps
