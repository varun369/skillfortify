"""Data models for the static analyzer: Severity, Finding, AnalysisResult.

These are the core data types produced and consumed by the analysis pipeline.
They are intentionally decoupled from the analysis engine so that downstream
modules (SBOM generator, CLI formatters, trust engine) can import them without
pulling in the pattern catalogs or analysis logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from skillfortify.core.capabilities import CapabilitySet


# ---------------------------------------------------------------------------
# Severity: Ordered threat severity levels
# ---------------------------------------------------------------------------


class Severity(IntEnum):
    """Four-level severity scale for analysis findings.

    The integer encoding enables direct comparison: LOW < MEDIUM < HIGH < CRITICAL.
    This aligns with CVSS v4.0 qualitative severity ratings.
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ---------------------------------------------------------------------------
# Finding: A single security observation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single security finding produced by the static analyzer.

    Each finding represents one detected issue -- a dangerous pattern match,
    a capability violation, or an information flow concern. Findings are
    immutable (frozen) to prevent post-analysis tampering.

    Attributes:
        skill_name: Name of the skill that produced this finding.
        severity: Threat severity (LOW through CRITICAL).
        message: Human-readable description of the finding.
        attack_class: The attack taxonomy class (e.g., "privilege_escalation",
            "data_exfiltration"). String values align with ``AttackClass`` enum
            values in the threat model.
        finding_type: Classification of how the finding was detected:
            "pattern_match" -- matched a known dangerous pattern.
            "capability_violation" -- inferred capability exceeds declared.
            "info_flow" -- cross-channel information flow concern.
        evidence: The specific text/pattern that triggered the finding.
    """

    skill_name: str
    severity: Severity
    message: str
    attack_class: str
    finding_type: str
    evidence: str


# ---------------------------------------------------------------------------
# AnalysisResult: Complete output of a static analysis run
# ---------------------------------------------------------------------------


@dataclass
class AnalysisResult:
    """The complete result of analyzing a single skill.

    Attributes:
        skill_name: Name of the analyzed skill.
        is_safe: True if no findings were produced. False otherwise.
        findings: List of all findings (may be empty).
        inferred_capabilities: The capability set inferred by Phase 1
            (abstract interpretation). None if inference was not performed.
    """

    skill_name: str
    is_safe: bool
    findings: list[Finding] = field(default_factory=list)
    inferred_capabilities: CapabilitySet | None = None

    @property
    def max_severity(self) -> Severity | None:
        """Return the highest severity among all findings, or None if safe."""
        if not self.findings:
            return None
        return max(f.severity for f in self.findings)
