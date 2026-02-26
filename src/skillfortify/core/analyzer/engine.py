"""Three-phase static analysis engine for agent skill security.

This module implements the ``StaticAnalyzer`` class which orchestrates the
three analysis phases:

1. **Capability Inference** -- abstract interpretation of skill content to
   infer required capabilities (network, shell, filesystem, environment).
2. **Dangerous Pattern Detection** -- matching skill content against known
   threat patterns from ClawHavoc, MalTool, and "Agent Skills in the Wild".
3. **Capability Violation Check** -- comparing inferred capabilities against
   declared capabilities to enforce the Principle of Least Authority (POLA).

References
----------
.. [DV66] Dennis & Van Horn (1966). Capability model foundations.
.. [Mil06] Miller (2006). Object-capability model and POLA.
"""

from __future__ import annotations

from skillfortify.core.capabilities import AccessLevel, Capability, CapabilitySet
from skillfortify.core.analyzer.models import AnalysisResult, Finding, Severity
from skillfortify.core.analyzer.patterns import (
    _BASE64_PATTERN,
    _DANGEROUS_CODE_PATTERNS,
    _DANGEROUS_SHELL_PATTERNS,
    _FILE_READ_PATTERNS,
    _FILE_WRITE_PATTERNS,
    _POST_PATTERNS,
    _is_safe_url,
    _is_sensitive_env_var,
)
from skillfortify.parsers.base import ParsedSkill


class StaticAnalyzer:
    """Three-phase static analyzer for agent skill security.

    The analyzer takes a ``ParsedSkill`` and returns an ``AnalysisResult``
    containing all security findings. Analysis proceeds in three sequential
    phases: capability inference, dangerous pattern detection, and capability
    violation checking.

    The analyzer is stateless -- each ``analyze()`` call is independent.
    This enables safe concurrent analysis of multiple skills.

    Usage::

        analyzer = StaticAnalyzer()
        result = analyzer.analyze(parsed_skill)
        if not result.is_safe:
            for finding in result.findings:
                print(f"[{finding.severity.name}] {finding.message}")
    """

    def analyze(self, skill: ParsedSkill) -> AnalysisResult:
        """Analyze a parsed skill and return all security findings.

        Three phases run sequentially:
          1. Capability inference from static patterns.
          2. Dangerous pattern matching against known threats.
          3. Capability violation check (inferred vs declared).

        Args:
            skill: The parsed skill to analyze.

        Returns:
            An ``AnalysisResult`` with all findings, safety verdict, and
            inferred capabilities.
        """
        findings: list[Finding] = []

        # Phase 1: Capability inference
        inferred = self._infer_capabilities(skill)

        # Phase 2: Dangerous pattern detection
        findings.extend(self._detect_dangerous_patterns(skill))

        # Phase 3: Capability violation check
        if skill.declared_capabilities:
            findings.extend(self._check_capability_violations(skill, inferred))

        is_safe = len(findings) == 0

        return AnalysisResult(
            skill_name=skill.name,
            is_safe=is_safe,
            findings=findings,
            inferred_capabilities=inferred,
        )

    # -- Phase 1: Capability Inference (Abstract Interpretation) --

    def _infer_capabilities(self, skill: ParsedSkill) -> CapabilitySet:
        """Infer the capability set a skill actually needs from its content.

        This is a conservative over-approximation (sound abstract interpretation):
        if a pattern suggests a capability, we include it. False positives are
        acceptable; false negatives are not.

        Returns:
            A ``CapabilitySet`` representing inferred capabilities.
        """
        caps = CapabilitySet()

        # URLs present -> network capability
        if skill.urls:
            # Default to READ; upgrade to WRITE if POST-like patterns found
            network_level = AccessLevel.READ
            # Check shell commands for POST/PUT/PATCH/DELETE patterns
            combined_shell = " ".join(skill.shell_commands)
            for pat in _POST_PATTERNS:
                if pat.search(combined_shell):
                    network_level = AccessLevel.WRITE
                    break
            caps.add(Capability("network", network_level))

        # Shell commands present -> shell:WRITE
        if skill.shell_commands:
            caps.add(Capability("shell", AccessLevel.WRITE))

        # Environment variable references -> environment:READ
        if skill.env_vars_referenced:
            caps.add(Capability("environment", AccessLevel.READ))

        # File operation patterns in instructions -> filesystem capability
        combined_text = f"{skill.instructions} {skill.description}"
        has_file_write = any(
            pat.search(combined_text) for pat in _FILE_WRITE_PATTERNS
        )
        has_file_read = any(
            pat.search(combined_text) for pat in _FILE_READ_PATTERNS
        )

        if has_file_write:
            caps.add(Capability("filesystem", AccessLevel.WRITE))
        elif has_file_read:
            caps.add(Capability("filesystem", AccessLevel.READ))

        return caps

    # -- Phase 2: Dangerous Pattern Detection --

    def _detect_dangerous_patterns(self, skill: ParsedSkill) -> list[Finding]:
        """Detect known-dangerous patterns in the skill's content.

        Checks shell commands, code blocks, URLs, and environment variable
        references against a catalog of threat patterns.

        Returns:
            List of findings from pattern matching.
        """
        findings: list[Finding] = []

        # 2a: Shell command patterns
        for cmd in skill.shell_commands:
            for pattern, severity, attack_class, message in _DANGEROUS_SHELL_PATTERNS:
                if pattern.search(cmd):
                    findings.append(Finding(
                        skill_name=skill.name,
                        severity=severity,
                        message=message,
                        attack_class=attack_class,
                        finding_type="pattern_match",
                        evidence=cmd,
                    ))

        # 2b: Code block patterns
        for block in skill.code_blocks:
            for pattern, severity, attack_class, message in _DANGEROUS_CODE_PATTERNS:
                if pattern.search(block):
                    findings.append(Finding(
                        skill_name=skill.name,
                        severity=severity,
                        message=message,
                        attack_class=attack_class,
                        finding_type="pattern_match",
                        evidence=block,
                    ))

        # 2c: External URLs (not in allow-list)
        for url in skill.urls:
            if not _is_safe_url(url):
                findings.append(Finding(
                    skill_name=skill.name,
                    severity=Severity.HIGH,
                    message=f"External URL detected: {url}",
                    attack_class="data_exfiltration",
                    finding_type="pattern_match",
                    evidence=url,
                ))

        # 2d: Sensitive environment variable access
        for env_var in skill.env_vars_referenced:
            if _is_sensitive_env_var(env_var):
                findings.append(Finding(
                    skill_name=skill.name,
                    severity=Severity.HIGH,
                    message=f"Sensitive environment variable accessed: {env_var}",
                    attack_class="data_exfiltration",
                    finding_type="pattern_match",
                    evidence=env_var,
                ))

        # 2e: Information flow: base64 encoding + network access
        # This combination suggests data exfiltration via encoding
        has_base64 = any(
            _BASE64_PATTERN.search(cmd) for cmd in skill.shell_commands
        ) or any(
            _BASE64_PATTERN.search(block) for block in skill.code_blocks
        )
        has_external_urls = any(not _is_safe_url(url) for url in skill.urls)

        if has_base64 and has_external_urls:
            findings.append(Finding(
                skill_name=skill.name,
                severity=Severity.CRITICAL,
                message=(
                    "Information flow concern: base64 encoding combined with "
                    "external network access suggests data exfiltration"
                ),
                attack_class="data_exfiltration",
                finding_type="info_flow",
                evidence="base64 + external URL",
            ))

        return findings

    # -- Phase 3: Capability Violation Check --

    def _check_capability_violations(
        self, skill: ParsedSkill, inferred: CapabilitySet
    ) -> list[Finding]:
        """Compare inferred capabilities against declared capabilities.

        Each inferred capability that is NOT permitted by the declared set
        is a violation -- the skill needs more authority than it claims.

        Args:
            skill: The parsed skill (for declared_capabilities).
            inferred: The inferred capability set from Phase 1.

        Returns:
            List of capability violation findings.
        """
        # Parse declared capabilities from "resource:LEVEL" strings
        declared = CapabilitySet()
        for cap_str in skill.declared_capabilities:
            parts = cap_str.split(":", 1)
            if len(parts) == 2:
                resource = parts[0].strip().lower()
                level_str = parts[1].strip().upper()
                try:
                    level = AccessLevel[level_str]
                except KeyError:
                    continue
                declared.add(Capability(resource, level))

        # Find violations: inferred capabilities not covered by declared
        violations = inferred.violations_against(declared)

        findings: list[Finding] = []
        for violation in violations:
            findings.append(Finding(
                skill_name=skill.name,
                severity=Severity.HIGH,
                message=(
                    f"Capability violation: skill requires "
                    f"{violation.resource}:{violation.access.name} "
                    f"but only declares up to "
                    f"{_declared_level_str(declared, violation.resource)}"
                ),
                attack_class="privilege_escalation",
                finding_type="capability_violation",
                evidence=f"inferred={violation.resource}:{violation.access.name}",
            ))

        return findings


def _declared_level_str(declared: CapabilitySet, resource: str) -> str:
    """Get a human-readable string for the declared level of a resource."""
    for cap in declared:
        if cap.resource == resource:
            return f"{cap.resource}:{cap.access.name}"
    return f"{resource}:NONE (undeclared)"
