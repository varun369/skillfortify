"""Trust data models: levels, signals, weights, and scores.

Defines the core data structures for the trust algebra:

- ``TrustLevel`` -- SLSA-inspired graduated trust levels (L0-L3).
- ``TrustSignals`` -- Four orthogonal raw trust inputs in [0, 1].
- ``TrustWeights`` -- Configurable weights for signal combination.
- ``TrustScore`` -- Computed trust output with intrinsic and effective scores.

References:
    SLSA Framework (Google, 2023): https://slsa.dev
    RFC 2704 (KeyNote Trust Management): Assertion monotonicity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


# ---------------------------------------------------------------------------
# TrustLevel: SLSA-inspired graduated trust levels
# ---------------------------------------------------------------------------


class TrustLevel(IntEnum):
    """SLSA-inspired graduated trust levels for agent skills.

    Maps numeric trust scores to four discrete levels that correspond to
    increasing levels of verification and provenance assurance. The integer
    encoding enables direct comparison: UNSIGNED < SIGNED < COMMUNITY_VERIFIED
    < FORMALLY_VERIFIED.

    The level boundaries are chosen to align with practical verification
    milestones:

    - **UNSIGNED** (L0): No verification whatsoever. The skill has not been
      signed, analyzed, or reviewed. T < 0.25.
    - **SIGNED** (L1): Basic provenance established. The author has signed
      the skill package, but no behavioral or community verification exists.
      0.25 <= T < 0.50.
    - **COMMUNITY_VERIFIED** (L2): Multiple positive signals. The skill has
      been reviewed by the community, has usage history, and passes basic
      behavioral checks. 0.50 <= T < 0.75.
    - **FORMALLY_VERIFIED** (L3): Highest assurance. Formal static analysis
      has passed, strong provenance chain, active community trust, and clean
      historical record. T >= 0.75.

    References:
        SLSA Framework (Google, 2023): https://slsa.dev
        RFC 2704 (KeyNote Trust Management): Assertion monotonicity.
    """

    UNSIGNED = 0
    SIGNED = 1
    COMMUNITY_VERIFIED = 2
    FORMALLY_VERIFIED = 3


# ---------------------------------------------------------------------------
# Trust level boundary constants
# ---------------------------------------------------------------------------

LEVEL_SIGNED_THRESHOLD: float = 0.25
LEVEL_COMMUNITY_THRESHOLD: float = 0.50
LEVEL_FORMAL_THRESHOLD: float = 0.75


# ---------------------------------------------------------------------------
# TrustSignals: Raw trust inputs
# ---------------------------------------------------------------------------


@dataclass
class TrustSignals:
    """Raw trust signals for a skill.

    Each signal is a value in the closed interval [0, 1], where 0 indicates
    no trust (worst case) and 1 indicates full trust (best case) along that
    dimension. The four signals are designed to be orthogonal:

    Attributes:
        provenance: Author verification and signing status. 0 = unsigned,
            anonymous author. 1 = signed by a verified organization with
            reproducible builds.
        behavioral: Static analysis results. 0 = critical findings detected.
            1 = clean analysis, no findings.
        community: Community trust signals. 0 = no usage, no reviews,
            brand new. 1 = widely used, no reported issues, mature.
        historical: Past vulnerability record. 0 = history of CVEs or
            security incidents. 1 = clean historical record.
    """

    provenance: float = 0.0
    behavioral: float = 0.0
    community: float = 0.0
    historical: float = 0.0

    def validate(self) -> None:
        """Raise ValueError if any signal is outside the [0, 1] range.

        All trust signals must be in the closed interval [0, 1]. Values
        outside this range are physically meaningless (trust cannot be
        negative or exceed certainty).

        Raises:
            ValueError: If any signal is < 0 or > 1.
        """
        for name in ("provenance", "behavioral", "community", "historical"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Signal '{name}' must be numeric, got {type(value).__name__}"
                )
            if value < 0.0 or value > 1.0:
                raise ValueError(
                    f"Signal '{name}' must be in [0, 1], got {value}"
                )

    def as_dict(self) -> dict[str, float]:
        """Return signals as a dictionary for iteration.

        Returns:
            Dictionary mapping signal names to their values.
        """
        return {
            "provenance": self.provenance,
            "behavioral": self.behavioral,
            "community": self.community,
            "historical": self.historical,
        }

    def component_wise_ge(self, other: TrustSignals) -> bool:
        """Check if this signal vector is >= other in every component.

        Used for verifying Theorem 5 (Trust Monotonicity): if signals_new
        >= signals_old component-wise, then T(signals_new) >= T(signals_old).

        Args:
            other: The signal vector to compare against.

        Returns:
            True if every signal in self is >= the corresponding signal
            in other.
        """
        return (
            self.provenance >= other.provenance
            and self.behavioral >= other.behavioral
            and self.community >= other.community
            and self.historical >= other.historical
        )


# ---------------------------------------------------------------------------
# TrustWeights: Configurable signal weights
# ---------------------------------------------------------------------------


WEIGHT_SUM_EPSILON: float = 1e-6


@dataclass
class TrustWeights:
    """Weights for trust signal combination.

    The weights determine the relative importance of each trust signal in
    the composite trust score. They must be non-negative and sum to 1.0
    (within floating-point tolerance).

    Default weights (0.3, 0.3, 0.2, 0.2) prioritize provenance and
    behavioral analysis equally (30% each), reflecting that these are the
    signals most directly under the skill author's and the tool's control.
    Community and historical signals each contribute 20%, as they accumulate
    over time and are less actionable for new skills.

    Attributes:
        provenance: Weight for the provenance trust signal.
        behavioral: Weight for the behavioral trust signal.
        community: Weight for the community trust signal.
        historical: Weight for the historical trust signal.
    """

    provenance: float = 0.3
    behavioral: float = 0.3
    community: float = 0.2
    historical: float = 0.2

    def validate(self) -> None:
        """Raise ValueError if weights are invalid.

        Validation rules:
        1. All weights must be non-negative.
        2. Weights must sum to 1.0 (within epsilon = 1e-6).

        Non-negative weights are essential for Theorem 5 (Trust
        Monotonicity): increasing a signal must never decrease the score,
        which requires all coefficients in the linear combination to be >= 0.

        Raises:
            ValueError: If any weight is negative or weights don't sum
                to ~1.0.
        """
        weight_names = ("provenance", "behavioral", "community", "historical")
        total = 0.0
        for name in weight_names:
            value = getattr(self, name)
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Weight '{name}' must be numeric, got {type(value).__name__}"
                )
            if value < 0.0:
                raise ValueError(
                    f"Weight '{name}' must be non-negative, got {value}"
                )
            total += value

        if abs(total - 1.0) > WEIGHT_SUM_EPSILON:
            raise ValueError(
                f"Weights must sum to 1.0 (within epsilon={WEIGHT_SUM_EPSILON}), "
                f"got sum={total}"
            )


# ---------------------------------------------------------------------------
# TrustScore: Computed trust output
# ---------------------------------------------------------------------------


@dataclass
class TrustScore:
    """Computed trust score for a specific skill version.

    The trust score encapsulates both the intrinsic score (computed from
    the skill's own signals) and the effective score (after propagation
    through the dependency chain). The effective score is always <= the
    intrinsic score, reflecting the conservative propagation semantics.

    Attributes:
        skill_name: Name of the skill.
        version: Version string of the skill.
        intrinsic_score: T(s,v) = weighted combination of signals. In [0, 1].
        effective_score: After propagation through dependencies. In [0, 1].
            Always <= intrinsic_score.
        level: SLSA-inspired trust level derived from effective_score.
        signals: The raw input signals used to compute the score.
    """

    skill_name: str
    version: str
    intrinsic_score: float
    effective_score: float
    level: TrustLevel
    signals: TrustSignals
