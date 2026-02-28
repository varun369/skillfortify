"""Suspicious pattern detection for remote registry entries.

Centralised pattern definitions shared by MCP, PyPI, and npm scanners.
Each pattern maps to a Finding that the scanners can emit when a match
is detected in registry metadata, README content, or package scripts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Compiled regex patterns for suspicious indicators
# ---------------------------------------------------------------------------

# Data exfiltration indicators in code or descriptions
EXFIL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(requests\.post|httpx\.post|fetch\()\s*\(?\s*['\"]https?://", re.I),
    re.compile(r"(webhook|exfil|phone[_\-]?home|beacon)", re.I),
    re.compile(r"base64\.(b64encode|encode)", re.I),
    re.compile(r"socket\.connect", re.I),
]

# Privilege escalation / dangerous system access
PRIV_ESC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(sudo|chmod\s+[0-7]{3,4}|chown)\b", re.I),
    re.compile(r"(os\.system|subprocess\.(run|call|Popen))", re.I),
    re.compile(r"exec\s*\(|eval\s*\(", re.I),
    re.compile(r"__import__\s*\(", re.I),
]

# Credential / secret harvesting
CRED_HARVEST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)", re.I),
    re.compile(r"os\.environ\[", re.I),
    re.compile(r"\.(aws|gcp|azure).*credential", re.I),
    re.compile(r"keyring\.|keychain", re.I),
]

# Typosquatting indicators (common name mutations)
TYPOSQUAT_INDICATORS: list[str] = [
    "offical", "0fficial", "orginal", "modlecontext", "mcpp-",
    "servr", "sever-", "claud-", "cladue", "openaai",
]

# npm preinstall / postinstall abuse
NPM_SCRIPT_DANGERS: list[re.Pattern[str]] = [
    re.compile(r"(preinstall|postinstall|preuninstall)\s*:", re.I),
    re.compile(r"curl\s+.*\|\s*(sh|bash)", re.I),
    re.compile(r"wget\s+.*&&\s*(sh|bash|chmod)", re.I),
    re.compile(r"node\s+-e\s+['\"]", re.I),
]

# Missing authentication indicators for MCP servers
MCP_NO_AUTH_INDICATORS: list[str] = [
    "no authentication",
    "authentication not required",
    "open access",
    "unauthenticated",
]

# Overly broad permission indicators
BROAD_PERMISSION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(full[_\s]?access|admin|root|superuser|all[_\s]?permissions)", re.I),
    re.compile(r"\*\.\*|/\*\*/\*", re.I),
    re.compile(r"(read|write|execute)\s*(,\s*(read|write|execute)){2,}", re.I),
]


# ---------------------------------------------------------------------------
# Pattern match result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PatternMatch:
    """Result of a pattern match against registry entry content.

    Attributes:
        category: Attack taxonomy category (e.g. "data_exfiltration").
        description: Human-readable description of the matched pattern.
        evidence: The text snippet that triggered the match.
        is_critical: Whether this match warrants CRITICAL severity.
    """

    category: str
    description: str
    evidence: str
    is_critical: bool = False


def check_suspicious_content(text: str) -> list[PatternMatch]:
    """Run all pattern checks against the given text.

    Args:
        text: Content to scan (README, description, source, etc.).

    Returns:
        List of PatternMatch objects for every match found.
    """
    matches: list[PatternMatch] = []

    for pat in EXFIL_PATTERNS:
        m = pat.search(text)
        if m:
            matches.append(PatternMatch(
                category="data_exfiltration",
                description="Potential data exfiltration pattern detected",
                evidence=m.group(0)[:120],
                is_critical=True,
            ))

    for pat in PRIV_ESC_PATTERNS:
        m = pat.search(text)
        if m:
            matches.append(PatternMatch(
                category="privilege_escalation",
                description="Dangerous system access pattern detected",
                evidence=m.group(0)[:120],
                is_critical=True,
            ))

    for pat in CRED_HARVEST_PATTERNS:
        m = pat.search(text)
        if m:
            matches.append(PatternMatch(
                category="credential_harvesting",
                description="Credential or secret access pattern detected",
                evidence=m.group(0)[:120],
            ))

    for pat in BROAD_PERMISSION_PATTERNS:
        m = pat.search(text)
        if m:
            matches.append(PatternMatch(
                category="excessive_permissions",
                description="Overly broad permission request detected",
                evidence=m.group(0)[:120],
            ))

    return matches


def check_typosquatting(name: str) -> list[PatternMatch]:
    """Check a package name for typosquatting indicators.

    Args:
        name: Package or skill name to check.

    Returns:
        List of PatternMatch objects if suspicious, empty otherwise.
    """
    matches: list[PatternMatch] = []
    lower_name = name.lower()
    for indicator in TYPOSQUAT_INDICATORS:
        if indicator in lower_name:
            matches.append(PatternMatch(
                category="typosquatting",
                description=f"Name contains typosquatting indicator: {indicator}",
                evidence=name,
                is_critical=True,
            ))
    return matches


def check_npm_scripts(scripts: dict[str, str]) -> list[PatternMatch]:
    """Check npm package.json scripts for suspicious lifecycle hooks.

    Args:
        scripts: The ``scripts`` dict from package.json.

    Returns:
        List of PatternMatch objects for dangerous script patterns.
    """
    matches: list[PatternMatch] = []
    text = " ".join(f"{k}: {v}" for k, v in scripts.items())
    for pat in NPM_SCRIPT_DANGERS:
        m = pat.search(text)
        if m:
            matches.append(PatternMatch(
                category="malicious_lifecycle_script",
                description="Suspicious npm lifecycle script detected",
                evidence=m.group(0)[:120],
                is_critical=True,
            ))
    return matches


# ---------------------------------------------------------------------------
# Shared Finding converters (used by all three scanners)
# ---------------------------------------------------------------------------


def matches_to_findings(skill_name: str, text: str) -> list:
    """Scan text for suspicious patterns and return Finding objects.

    Avoids circular imports by importing Finding/Severity lazily.

    Args:
        skill_name: Name for Finding attribution.
        text: Content to scan.

    Returns:
        List of Finding objects.
    """
    from skillfortify.core.analyzer.models import Finding, Severity

    return [
        Finding(
            skill_name=skill_name,
            severity=Severity.CRITICAL if m.is_critical else Severity.HIGH,
            message=m.description,
            attack_class=m.category,
            finding_type="pattern_match",
            evidence=m.evidence,
        )
        for m in check_suspicious_content(text)
    ]


def typosquat_to_findings(name: str) -> list:
    """Check name for typosquatting and return Finding objects.

    Args:
        name: Package or skill name to check.

    Returns:
        List of Finding objects.
    """
    from skillfortify.core.analyzer.models import Finding, Severity

    return [
        Finding(
            skill_name=name,
            severity=Severity.CRITICAL,
            message=m.description,
            attack_class=m.category,
            finding_type="pattern_match",
            evidence=m.evidence,
        )
        for m in check_typosquatting(name)
    ]
