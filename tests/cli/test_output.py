"""Tests for CLI output formatting helpers.

Verifies:
    - Severity style mapping.
    - Trust level style mapping.
    - Output functions produce non-empty output without errors.
"""

from __future__ import annotations



from skillfortify.cli.output import (
    print_analysis_detail,
    print_resolution_summary,
    print_sbom_summary,
    print_scan_results,
    print_trust_score,
    severity_style,
    trust_level_style,
)
from skillfortify.core.analyzer import AnalysisResult, Finding, Severity
from skillfortify.core.capabilities import AccessLevel, Capability, CapabilitySet
from skillfortify.core.trust import TrustLevel, TrustScore, TrustSignals


class TestSeverityStyles:
    """Tests for severity-to-style mapping."""

    def test_critical_is_bold_red(self) -> None:
        assert severity_style(Severity.CRITICAL) == "bold red"

    def test_high_is_yellow(self) -> None:
        assert severity_style(Severity.HIGH) == "yellow"

    def test_medium_is_cyan(self) -> None:
        assert severity_style(Severity.MEDIUM) == "cyan"

    def test_low_is_green(self) -> None:
        assert severity_style(Severity.LOW) == "green"


class TestTrustLevelStyles:
    """Tests for trust level-to-style mapping."""

    def test_unsigned_is_bold_red(self) -> None:
        assert trust_level_style(TrustLevel.UNSIGNED) == "bold red"

    def test_signed_is_yellow(self) -> None:
        assert trust_level_style(TrustLevel.SIGNED) == "yellow"

    def test_community_verified_is_cyan(self) -> None:
        assert trust_level_style(TrustLevel.COMMUNITY_VERIFIED) == "cyan"

    def test_formally_verified_is_bold_green(self) -> None:
        assert trust_level_style(TrustLevel.FORMALLY_VERIFIED) == "bold green"


class TestPrintScanResults:
    """Tests for print_scan_results output."""

    def test_empty_results_produces_output(self, capsys) -> None:
        """Empty results should produce a 'No skills found' message."""
        print_scan_results([])
        captured = capsys.readouterr()
        assert "No skills" in captured.out

    def test_safe_result_produces_output(self, capsys) -> None:
        """Safe result should produce table output."""
        result = AnalysisResult(skill_name="test", is_safe=True)
        print_scan_results([result])
        captured = capsys.readouterr()
        assert "test" in captured.out

    def test_unsafe_result_produces_output(self, capsys) -> None:
        """Unsafe result should produce table output with findings."""
        finding = Finding(
            skill_name="bad-skill",
            severity=Severity.HIGH,
            message="Dangerous pattern",
            attack_class="data_exfiltration",
            finding_type="pattern_match",
            evidence="curl evil.com",
        )
        result = AnalysisResult(
            skill_name="bad-skill", is_safe=False, findings=[finding]
        )
        print_scan_results([result])
        captured = capsys.readouterr()
        assert "bad-skill" in captured.out


class TestPrintAnalysisDetail:
    """Tests for print_analysis_detail output."""

    def test_safe_detail_output(self, capsys) -> None:
        """Safe skill detail should show 'No findings' message."""
        result = AnalysisResult(skill_name="clean", is_safe=True)
        print_analysis_detail(result)
        captured = capsys.readouterr()
        assert "clean" in captured.out

    def test_detail_with_capabilities(self, capsys) -> None:
        """Detail with inferred capabilities should show capability table."""
        caps = CapabilitySet()
        caps.add(Capability("network", AccessLevel.READ))
        result = AnalysisResult(
            skill_name="networker",
            is_safe=True,
            inferred_capabilities=caps,
        )
        print_analysis_detail(result)
        captured = capsys.readouterr()
        assert "network" in captured.out


class TestPrintTrustScore:
    """Tests for print_trust_score output."""

    def test_trust_score_output(self, capsys) -> None:
        """Trust score should display all signal values."""
        signals = TrustSignals(
            provenance=0.5, behavioral=1.0, community=0.5, historical=0.5
        )
        score = TrustScore(
            skill_name="test-skill",
            version="1.0.0",
            intrinsic_score=0.65,
            effective_score=0.65,
            level=TrustLevel.COMMUNITY_VERIFIED,
            signals=signals,
        )
        print_trust_score(score)
        captured = capsys.readouterr()
        assert "test-skill" in captured.out
        assert "COMMUNITY_VERIFIED" in captured.out


class TestPrintResolutionSummary:
    """Tests for print_resolution_summary output."""

    def test_success_summary(self, capsys) -> None:
        """Successful resolution should show installed skills."""
        print_resolution_summary(
            success=True,
            installed={"skill-a": "1.0.0", "skill-b": "2.1.0"},
            conflicts=[],
        )
        captured = capsys.readouterr()
        assert "successful" in captured.out.lower()

    def test_failure_summary(self, capsys) -> None:
        """Failed resolution should show conflicts."""
        print_resolution_summary(
            success=False,
            installed={},
            conflicts=["skill-a conflicts with skill-b"],
        )
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()


class TestPrintSbomSummary:
    """Tests for print_sbom_summary output."""

    def test_sbom_summary_output(self, capsys) -> None:
        """SBOM summary should display statistics."""
        summary = {
            "total": 5,
            "safe": 3,
            "unsafe": 2,
            "total_findings": 7,
            "formats": {"claude": 3, "mcp": 2},
            "trust_distribution": {"UNSIGNED": 2, "SIGNED": 3},
        }
        print_sbom_summary(summary)
        captured = capsys.readouterr()
        assert "5" in captured.out
        assert "3" in captured.out
