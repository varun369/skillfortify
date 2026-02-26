"""Lockfile data models — LockedSkill and LockfileMetadata.

Defines the core data structures used in the ``skill-lock.json`` lockfile
format. These are pure data holders (dataclasses) with no business logic,
making them safe to import without circular-dependency concerns.

.. [SLSA] Google (2023). "Supply chain Levels for Software Artifacts."
   Graduated trust levels adapted for agent skills.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Integrity hash format: "sha256:<64-hex-characters>"
# ---------------------------------------------------------------------------

_INTEGRITY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# LockedSkill: A single entry in the lockfile
# ---------------------------------------------------------------------------


@dataclass
class LockedSkill:
    """A single skill entry in the lockfile.

    Represents the fully resolved state of one skill --- its exact version,
    content integrity hash, declared capabilities, resolved dependencies,
    and trust metadata.

    Attributes:
        name: Skill name (e.g., "weather-api").
        version: Resolved semantic version (e.g., "1.2.3").
        integrity: Content hash in "sha256:<hex>" format. Used for tamper
            detection at install time.
        format: Skill format identifier ("claude", "mcp", "openclaw").
        capabilities: List of capability strings the skill requires at
            runtime (e.g., ["filesystem:READ", "network:WRITE"]).
        dependencies: Mapping of dependency name to resolved version.
        trust_score: Computed trust score in [0, 1], or None if not
            yet computed.
        trust_level: SLSA-inspired trust level string (e.g.,
            "COMMUNITY_VERIFIED"), or None if not yet computed.
        source_path: Filesystem path where the skill was found.
    """

    name: str
    version: str
    integrity: str  # "sha256:<hex>"
    format: str  # "claude", "mcp", "openclaw"
    capabilities: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    trust_score: float | None = None
    trust_level: str | None = None
    source_path: str = ""


# ---------------------------------------------------------------------------
# LockfileMetadata: Top-level metadata section
# ---------------------------------------------------------------------------


@dataclass
class LockfileMetadata:
    """Metadata section of the lockfile.

    Captures aggregate information about the lockfile contents and the
    resolution strategy used to produce it.

    Attributes:
        total_skills: Expected number of skill entries. Used during
            validation to detect incomplete writes.
        resolution_strategy: The resolution algorithm used ("sat" for
            SAT-based resolution, "manual" for hand-authored lockfiles).
        allowed_capabilities: The capability bounds applied during
            resolution, if any. None means no capability restriction.
    """

    total_skills: int = 0
    resolution_strategy: str = "sat"
    allowed_capabilities: list[str] | None = None


# ---------------------------------------------------------------------------
# Trust level helper
# ---------------------------------------------------------------------------

# These thresholds match skillfortify.core.trust.TrustEngine.score_to_level
_LEVEL_FORMALLY_VERIFIED_THRESHOLD: float = 0.75
_LEVEL_COMMUNITY_VERIFIED_THRESHOLD: float = 0.50
_LEVEL_SIGNED_THRESHOLD: float = 0.25


def _score_to_level_str(score: float) -> str:
    """Map a trust score to a trust level string.

    Uses the same thresholds as ``TrustEngine.score_to_level`` but returns
    a string rather than requiring the ``TrustLevel`` enum import, keeping
    the lockfile module self-contained.

    Args:
        score: Trust score in [0, 1].

    Returns:
        Trust level string: "FORMALLY_VERIFIED", "COMMUNITY_VERIFIED",
        "SIGNED", or "UNSIGNED".
    """
    if score >= _LEVEL_FORMALLY_VERIFIED_THRESHOLD:
        return "FORMALLY_VERIFIED"
    if score >= _LEVEL_COMMUNITY_VERIFIED_THRESHOLD:
        return "COMMUNITY_VERIFIED"
    if score >= _LEVEL_SIGNED_THRESHOLD:
        return "SIGNED"
    return "UNSIGNED"
