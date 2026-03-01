"""Tests for the dashboard data preparation module.

Covers: executive summary generation, findings table flattening,
capabilities matrix extraction, framework coverage counting, and
JSON payload encoding. All functions must handle empty inputs gracefully.
"""

from __future__ import annotations

import json


from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.core.capabilities import CapabilitySet
from skillfortify.dashboard.data_prep import (
    SUPPORTED_FRAMEWORKS,
    encode_dashboard_json,
    prepare_capabilities_matrix,
    prepare_executive_summary,
    prepare_findings_table,
    prepare_framework_coverage,
)
from skillfortify.parsers.base import ParsedSkill


# -----------------------------------------------------------------------
# prepare_executive_summary
# -----------------------------------------------------------------------


class TestExecutiveSummary:
    """Tests for prepare_executive_summary()."""

    def test_empty_inputs(self) -> None:
        s = prepare_executive_summary([], [])
        assert s["total_skills"] == 0
        assert s["safe_count"] == 0
        assert s["unsafe_count"] == 0
        assert s["critical_count"] == 0
        assert s["frameworks_detected"] == []

    def test_all_safe(self, safe_result: AnalysisResult) -> None:
        s = prepare_executive_summary([safe_result], [])
        assert s["total_skills"] == 1
        assert s["safe_count"] == 1
        assert s["unsafe_count"] == 0

    def test_mixed(
        self, safe_result: AnalysisResult, unsafe_result: AnalysisResult,
    ) -> None:
        s = prepare_executive_summary([safe_result, unsafe_result], [])
        assert s["safe_count"] == 1
        assert s["unsafe_count"] == 1

    def test_severity_counts(
        self, all_severity_results: list[AnalysisResult],
    ) -> None:
        s = prepare_executive_summary(all_severity_results, [])
        assert s["critical_count"] == 1
        assert s["high_count"] == 1
        assert s["medium_count"] == 1
        assert s["low_count"] == 1

    def test_timestamp_iso_format(self) -> None:
        s = prepare_executive_summary([], [])
        assert "T" in s["scan_timestamp"]

    def test_frameworks_detected(
        self, multi_framework_skills: list[ParsedSkill],
    ) -> None:
        s = prepare_executive_summary([], multi_framework_skills)
        fws = s["frameworks_detected"]
        assert "claude" in fws
        assert "mcp_server" in fws
        assert "langchain" in fws


# -----------------------------------------------------------------------
# prepare_findings_table
# -----------------------------------------------------------------------


class TestFindingsTable:
    """Tests for prepare_findings_table()."""

    def test_empty(self) -> None:
        assert prepare_findings_table([], []) == []

    def test_findings_flattened(
        self, unsafe_result: AnalysisResult, unsafe_skill: ParsedSkill,
    ) -> None:
        rows = prepare_findings_table([unsafe_result], [unsafe_skill])
        assert len(rows) == 2
        assert rows[0]["skill_name"] == "data-exfil-tool"

    def test_format_lookup(
        self, unsafe_result: AnalysisResult, unsafe_skill: ParsedSkill,
    ) -> None:
        rows = prepare_findings_table([unsafe_result], [unsafe_skill])
        for row in rows:
            assert row["format"] == "claude"

    def test_missing_format_defaults(
        self, unsafe_result: AnalysisResult,
    ) -> None:
        rows = prepare_findings_table([unsafe_result], [])
        for row in rows:
            assert row["format"] == "unknown"

    def test_evidence_truncation(self) -> None:
        finding = Finding(
            skill_name="t", severity=Severity.LOW, message="m",
            attack_class="a", finding_type="p", evidence="z" * 200,
        )
        result = AnalysisResult(
            skill_name="t", is_safe=False, findings=[finding],
        )
        rows = prepare_findings_table([result], [])
        assert len(rows[0]["evidence"]) <= 120
        assert rows[0]["evidence"].endswith("...")

    def test_short_evidence_not_truncated(self) -> None:
        finding = Finding(
            skill_name="t", severity=Severity.LOW, message="m",
            attack_class="a", finding_type="p", evidence="short",
        )
        result = AnalysisResult(
            skill_name="t", is_safe=False, findings=[finding],
        )
        rows = prepare_findings_table([result], [])
        assert rows[0]["evidence"] == "short"

    def test_row_keys(self, unsafe_result: AnalysisResult) -> None:
        rows = prepare_findings_table([unsafe_result], [])
        expected_keys = {
            "skill_name", "format", "severity", "message",
            "attack_class", "finding_type", "evidence",
        }
        assert set(rows[0].keys()) == expected_keys


# -----------------------------------------------------------------------
# prepare_capabilities_matrix
# -----------------------------------------------------------------------


class TestCapabilitiesMatrix:
    """Tests for prepare_capabilities_matrix()."""

    def test_empty(self) -> None:
        assert prepare_capabilities_matrix([]) == []

    def test_no_inferred_capabilities(self) -> None:
        result = AnalysisResult(skill_name="x", is_safe=True)
        assert prepare_capabilities_matrix([result]) == []

    def test_empty_capability_set(self) -> None:
        result = AnalysisResult(
            skill_name="x", is_safe=True,
            inferred_capabilities=CapabilitySet(),
        )
        assert prepare_capabilities_matrix([result]) == []

    def test_capabilities_extracted(
        self, safe_result: AnalysisResult,
    ) -> None:
        matrix = prepare_capabilities_matrix([safe_result])
        assert len(matrix) == 1
        assert matrix[0]["skill_name"] == "weather-api"
        assert matrix[0]["capabilities"]["network"] == "READ"

    def test_multiple_capabilities(
        self, unsafe_result: AnalysisResult,
    ) -> None:
        matrix = prepare_capabilities_matrix([unsafe_result])
        caps = matrix[0]["capabilities"]
        assert "network" in caps
        assert "shell" in caps
        assert "environment" in caps


# -----------------------------------------------------------------------
# prepare_framework_coverage
# -----------------------------------------------------------------------


class TestFrameworkCoverage:
    """Tests for prepare_framework_coverage()."""

    def test_empty(self) -> None:
        assert prepare_framework_coverage([]) == []

    def test_single_framework(self, safe_skill: ParsedSkill) -> None:
        cov = prepare_framework_coverage([safe_skill])
        assert len(cov) == 1
        assert cov[0]["framework"] == "mcp_server"
        assert cov[0]["count"] == 1

    def test_multi_sorted_by_count(
        self, multi_framework_skills: list[ParsedSkill],
    ) -> None:
        cov = prepare_framework_coverage(multi_framework_skills)
        assert cov[0]["count"] >= cov[-1]["count"]
        assert cov[0]["framework"] == "claude"
        assert cov[0]["count"] == 2


# -----------------------------------------------------------------------
# encode_dashboard_json
# -----------------------------------------------------------------------


class TestEncodeDashboardJson:
    """Tests for encode_dashboard_json()."""

    def test_empty_is_valid_json(self) -> None:
        raw = encode_dashboard_json([], [])
        data = json.loads(raw)
        assert "summary" in data

    def test_contains_all_sections(self) -> None:
        raw = encode_dashboard_json([], [])
        data = json.loads(raw)
        for key in ("summary", "findings", "capabilities", "framework_coverage"):
            assert key in data

    def test_compact_format(self) -> None:
        raw = encode_dashboard_json([], [])
        assert " " not in raw.split('"scan_timestamp"')[0]


# -----------------------------------------------------------------------
# SUPPORTED_FRAMEWORKS constant
# -----------------------------------------------------------------------


class TestSupportedFrameworks:
    """Verify the SUPPORTED_FRAMEWORKS tuple matches the 22 parsers."""

    def test_count(self) -> None:
        assert len(SUPPORTED_FRAMEWORKS) == 22

    def test_no_duplicates(self) -> None:
        assert len(SUPPORTED_FRAMEWORKS) == len(set(SUPPORTED_FRAMEWORKS))
