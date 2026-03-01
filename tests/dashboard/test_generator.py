"""Tests for DashboardGenerator.render() and DashboardGenerator.write().

Covers: empty results, None arguments, single skill, multiple skills,
all severities, HTML structure validation, embedded data integrity,
file output, and absence of external CDN dependencies.

Fixtures are provided by ``conftest.py`` in this package.
"""

from __future__ import annotations

from pathlib import Path


from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.dashboard import DashboardGenerator
from skillfortify.parsers.base import ParsedSkill

from tests.dashboard.conftest import extract_json_payload


# -----------------------------------------------------------------------
# Rendering with empty / None inputs
# -----------------------------------------------------------------------


class TestRenderEmptyResults:
    """Render when there are no results at all."""

    def test_empty_lists_produce_valid_html(self) -> None:
        html = DashboardGenerator().render([], [])
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_none_arguments_produce_valid_html(self) -> None:
        html = DashboardGenerator().render(None, None)
        assert "<!DOCTYPE html>" in html

    def test_empty_results_embed_zero_counts(self) -> None:
        data = extract_json_payload(DashboardGenerator().render([], []))
        assert data["summary"]["total_skills"] == 0
        assert data["summary"]["safe_count"] == 0
        assert data["summary"]["unsafe_count"] == 0

    def test_empty_results_no_findings(self) -> None:
        data = extract_json_payload(DashboardGenerator().render([], []))
        assert data["findings"] == []

    def test_empty_results_no_capabilities(self) -> None:
        data = extract_json_payload(DashboardGenerator().render([], []))
        assert data["capabilities"] == []


# -----------------------------------------------------------------------
# Rendering with a single safe skill
# -----------------------------------------------------------------------


class TestRenderSingleSkill:
    """Render a single skill that passes analysis."""

    def test_safe_skill_counts(
        self, safe_result: AnalysisResult, safe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([safe_result], [safe_skill])
        )
        assert data["summary"]["total_skills"] == 1
        assert data["summary"]["safe_count"] == 1
        assert data["summary"]["unsafe_count"] == 0

    def test_safe_skill_no_findings(
        self, safe_result: AnalysisResult, safe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([safe_result], [safe_skill])
        )
        assert data["findings"] == []

    def test_safe_skill_capabilities_present(
        self, safe_result: AnalysisResult, safe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([safe_result], [safe_skill])
        )
        assert len(data["capabilities"]) == 1
        cap = data["capabilities"][0]
        assert cap["skill_name"] == "weather-api"
        assert cap["capabilities"]["network"] == "READ"

    def test_framework_coverage_single(
        self, safe_result: AnalysisResult, safe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([safe_result], [safe_skill])
        )
        assert len(data["framework_coverage"]) == 1
        assert data["framework_coverage"][0]["framework"] == "mcp_server"


# -----------------------------------------------------------------------
# Rendering with multiple / mixed skills
# -----------------------------------------------------------------------


class TestRenderMultipleSkills:
    """Render a mix of safe and unsafe skills."""

    def test_mixed_safe_unsafe_counts(
        self,
        safe_result: AnalysisResult,
        unsafe_result: AnalysisResult,
        safe_skill: ParsedSkill,
        unsafe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render(
                [safe_result, unsafe_result],
                [safe_skill, unsafe_skill],
            )
        )
        assert data["summary"]["total_skills"] == 2
        assert data["summary"]["safe_count"] == 1
        assert data["summary"]["unsafe_count"] == 1

    def test_findings_from_unsafe_skill(
        self,
        safe_result: AnalysisResult,
        unsafe_result: AnalysisResult,
        safe_skill: ParsedSkill,
        unsafe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render(
                [safe_result, unsafe_result],
                [safe_skill, unsafe_skill],
            )
        )
        assert len(data["findings"]) == 2
        severities = {f["severity"] for f in data["findings"]}
        assert "CRITICAL" in severities
        assert "HIGH" in severities

    def test_framework_coverage_multi(
        self, multi_framework_skills: list[ParsedSkill],
    ) -> None:
        results = [
            AnalysisResult(skill_name=s.name, is_safe=True)
            for s in multi_framework_skills
        ]
        data = extract_json_payload(
            DashboardGenerator().render(results, multi_framework_skills)
        )
        fw_names = {fc["framework"] for fc in data["framework_coverage"]}
        assert fw_names == {"claude", "mcp_server", "langchain"}
        assert data["framework_coverage"][0]["framework"] == "claude"
        assert data["framework_coverage"][0]["count"] == 2


class TestRenderAllSeverities:
    """All four severity levels appear in the report."""

    def test_all_severities_counted(
        self, all_severity_results: list[AnalysisResult],
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render(all_severity_results, [])
        )
        assert data["summary"]["critical_count"] == 1
        assert data["summary"]["high_count"] == 1
        assert data["summary"]["medium_count"] == 1
        assert data["summary"]["low_count"] == 1


# -----------------------------------------------------------------------
# HTML structure validation
# -----------------------------------------------------------------------


class TestHTMLStructure:
    """Validate structural elements of the generated HTML."""

    def test_starts_with_doctype(self) -> None:
        html = DashboardGenerator().render([], [])
        assert html.startswith("<!DOCTYPE html>")

    def test_contains_title_tag(self) -> None:
        assert "<title>" in DashboardGenerator().render([], [])

    def test_contains_style_tag(self) -> None:
        assert "<style>" in DashboardGenerator().render([], [])

    def test_contains_script_tag(self) -> None:
        assert "<script>" in DashboardGenerator().render([], [])

    def test_no_external_cdn(self) -> None:
        html = DashboardGenerator().render([], [])
        for term in ("cdn", "googleapis", "unpkg", "cdnjs", "jsdelivr"):
            assert term not in html.lower()

    def test_filter_controls_present(self) -> None:
        html = DashboardGenerator().render([], [])
        assert 'id="filter-severity"' in html
        assert 'id="filter-framework"' in html

    def test_collapsible_sections(self) -> None:
        html = DashboardGenerator().render([], [])
        assert "section-header" in html
        assert "section-body" in html

    def test_capabilities_table(self) -> None:
        html = DashboardGenerator().render([], [])
        assert 'id="cap-body"' in html

    def test_risk_bar(self) -> None:
        assert 'id="risk-bar"' in DashboardGenerator().render([], [])

    def test_print_css(self) -> None:
        assert "@media print" in DashboardGenerator().render([], [])

    def test_responsive_css(self) -> None:
        assert "@media(max-width:640px)" in DashboardGenerator().render([], [])


# -----------------------------------------------------------------------
# Data embedding
# -----------------------------------------------------------------------


class TestDataEmbedding:
    """JSON payload is correctly embedded and parseable."""

    def test_payload_has_all_sections(
        self, safe_result: AnalysisResult, safe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([safe_result], [safe_skill])
        )
        for key in ("summary", "findings", "capabilities", "framework_coverage"):
            assert key in data

    def test_timestamp_present(self) -> None:
        data = extract_json_payload(DashboardGenerator().render([], []))
        ts = data["summary"]["scan_timestamp"]
        assert ts and "T" in ts

    def test_evidence_truncation(self) -> None:
        finding = Finding(
            skill_name="test", severity=Severity.HIGH, message="test",
            attack_class="test", finding_type="pattern_match",
            evidence="x" * 200,
        )
        result = AnalysisResult(
            skill_name="test", is_safe=False, findings=[finding],
        )
        data = extract_json_payload(DashboardGenerator().render([result], []))
        assert len(data["findings"][0]["evidence"]) <= 120

    def test_finding_format_lookup(
        self, unsafe_result: AnalysisResult, unsafe_skill: ParsedSkill,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([unsafe_result], [unsafe_skill])
        )
        for f in data["findings"]:
            assert f["format"] == "claude"

    def test_missing_skill_defaults_unknown(
        self, unsafe_result: AnalysisResult,
    ) -> None:
        data = extract_json_payload(
            DashboardGenerator().render([unsafe_result], [])
        )
        for f in data["findings"]:
            assert f["format"] == "unknown"


# -----------------------------------------------------------------------
# File writing
# -----------------------------------------------------------------------


class TestWriteToFile:
    """Tests for the file-writing convenience method."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "report.html"
        returned = DashboardGenerator().write(out, results=[], skills=[])
        assert out.exists()
        assert returned == out.resolve()

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        out = tmp_path / "sub" / "dir" / "report.html"
        DashboardGenerator().write(out, results=[], skills=[])
        assert out.exists()

    def test_written_file_is_valid_html(self, tmp_path: Path) -> None:
        out = tmp_path / "report.html"
        DashboardGenerator().write(out, results=[], skills=[])
        content = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content
