"""Trust score computation engine.

Implements the core trust algebra: intrinsic score computation via weighted
linear combination, full score computation with dependency propagation, and
SLSA-inspired level mapping.

Trust Score Model:
    T(s, v) = w_p * T_p + w_b * T_b + w_c * T_c + w_h * T_h

Trust Propagation:
    T_effective(s) = T_intrinsic(s) * min(T_effective(dep) for dep in deps(s))

References:
    RFC 2704 (KeyNote Trust Management): Assertion monotonicity.
    SLSA Framework (Google, 2023): Graduated trust levels.
"""

from __future__ import annotations

from datetime import datetime

from .models import (
    LEVEL_COMMUNITY_THRESHOLD,
    LEVEL_FORMAL_THRESHOLD,
    LEVEL_SIGNED_THRESHOLD,
    TrustLevel,
    TrustScore,
    TrustSignals,
    TrustWeights,
)
from . import propagation as _propagation


class TrustEngine:
    """Trust score computation, propagation, and decay engine.

    The engine implements the full trust algebra:
    1. **Intrinsic score computation** via weighted linear combination.
    2. **Dependency propagation** via multiplicative composition with
       conservative (min-over-deps) semantics.
    3. **Temporal decay** via exponential decay for unmaintained skills.
    4. **Level mapping** from numeric scores to SLSA-inspired levels.
    5. **Evidence updates** with Theorem 5 (monotonicity) guarantee.

    The engine is stateless: each method call is independent, enabling
    safe concurrent use from multiple threads or analysis pipelines.

    Theorem 5 (Trust Monotonicity):
        Adding positive evidence (increasing any signal value) NEVER reduces
        the trust score. This holds because:
        1. All weights are non-negative (validated at construction).
        2. The intrinsic score is a linear combination with non-negative
           coefficients.
        3. Propagation uses multiplication by values in [0, 1], which
           preserves the ordering.
        4. Decay is monotonically decreasing in time, not in signals.

    References:
        RFC 2704 (KeyNote Trust Management): Assertion monotonicity.
        SLSA Framework (Google, 2023): Graduated trust levels.

    Args:
        weights: Custom weights for signal combination. If None, uses
            default weights (0.3, 0.3, 0.2, 0.2).
        decay_rate: Exponential decay rate lambda (per day). Default 0.01.
            At this rate, trust halves every ~69 days without updates.
    """

    def __init__(
        self,
        weights: TrustWeights | None = None,
        decay_rate: float = 0.01,
    ) -> None:
        self._weights = weights or TrustWeights()
        self._weights.validate()
        if decay_rate < 0.0:
            raise ValueError(
                f"Decay rate must be non-negative, got {decay_rate}"
            )
        self._decay_rate = decay_rate

    @property
    def weights(self) -> TrustWeights:
        """Return the configured trust weights."""
        return self._weights

    @property
    def decay_rate(self) -> float:
        """Return the configured decay rate (lambda, per day)."""
        return self._decay_rate

    # -- Intrinsic score computation --

    def compute_intrinsic(self, signals: TrustSignals) -> float:
        """Compute intrinsic trust score from weighted signals.

        T(s, v) = w_p * T_p + w_b * T_b + w_c * T_c + w_h * T_h

        The result is guaranteed to be in [0, 1] when signals are valid
        (all in [0, 1]) and weights are valid (non-negative, sum to 1).

        Args:
            signals: The raw trust signals. Must pass validation.

        Returns:
            The intrinsic trust score in [0, 1].

        Raises:
            ValueError: If signals are invalid.
        """
        signals.validate()
        w = self._weights
        score = (
            w.provenance * signals.provenance
            + w.behavioral * signals.behavioral
            + w.community * signals.community
            + w.historical * signals.historical
        )
        # Clamp to [0, 1] to guard against floating-point drift
        return max(0.0, min(1.0, score))

    # -- Full score computation with dependency propagation --

    def compute_score(
        self,
        skill_name: str,
        version: str,
        signals: TrustSignals,
        dependency_scores: list[TrustScore] | None = None,
    ) -> TrustScore:
        """Compute full trust score with optional dependency propagation.

        If ``dependency_scores`` is provided, the effective score is:

            T_effective = T_intrinsic * min(dep.effective_score for dep in deps)

        If no dependencies exist, effective_score = intrinsic_score.

        Args:
            skill_name: Name of the skill.
            version: Version string.
            signals: Raw trust signals for this skill.
            dependency_scores: Trust scores of direct dependencies.

        Returns:
            A ``TrustScore`` with both intrinsic and effective scores.

        Raises:
            ValueError: If signals are invalid.
        """
        intrinsic = self.compute_intrinsic(signals)
        effective = intrinsic

        if dependency_scores:
            min_dep_trust = min(
                d.effective_score for d in dependency_scores
            )
            effective = intrinsic * min_dep_trust

        # Clamp to [0, 1]
        effective = max(0.0, min(1.0, effective))
        level = self.score_to_level(effective)

        return TrustScore(
            skill_name=skill_name,
            version=version,
            intrinsic_score=intrinsic,
            effective_score=effective,
            level=level,
            signals=signals,
        )

    # -- Level mapping --

    def score_to_level(self, score: float) -> TrustLevel:
        """Map a numeric trust score to a SLSA-inspired trust level.

        Level boundaries:
            - L0 (UNSIGNED):           score < 0.25
            - L1 (SIGNED):             0.25 <= score < 0.50
            - L2 (COMMUNITY_VERIFIED): 0.50 <= score < 0.75
            - L3 (FORMALLY_VERIFIED):  score >= 0.75

        Args:
            score: Numeric trust score in [0, 1].

        Returns:
            The corresponding ``TrustLevel``.
        """
        if score >= LEVEL_FORMAL_THRESHOLD:
            return TrustLevel.FORMALLY_VERIFIED
        if score >= LEVEL_COMMUNITY_THRESHOLD:
            return TrustLevel.COMMUNITY_VERIFIED
        if score >= LEVEL_SIGNED_THRESHOLD:
            return TrustLevel.SIGNED
        return TrustLevel.UNSIGNED

    # -- Chain propagation (delegated to propagation module) --

    def propagate_through_chain(
        self,
        chain: list[tuple[str, str, TrustSignals]],
    ) -> list[TrustScore]:
        """Compute trust scores for a dependency chain from leaf to root.

        See :func:`skillfortify.core.trust.propagation.propagate_through_chain`
        for full documentation.
        """
        return _propagation.propagate_through_chain(self, chain)

    # -- Temporal decay (delegated to propagation module) --

    def apply_decay(
        self,
        score: TrustScore,
        last_update: datetime,
        current_time: datetime | None = None,
    ) -> TrustScore:
        """Apply exponential decay for time since last update.

        See :func:`skillfortify.core.trust.propagation.apply_decay`
        for full documentation.
        """
        return _propagation.apply_decay(
            self, score, last_update, current_time
        )

    # -- Evidence update (delegated to propagation module) --

    def update_with_evidence(
        self,
        current: TrustSignals,
        positive_evidence: dict[str, float],
    ) -> TrustSignals:
        """Update trust signals with new positive evidence.

        See :func:`skillfortify.core.trust.propagation.update_with_evidence`
        for full documentation.
        """
        return _propagation.update_with_evidence(current, positive_evidence)
