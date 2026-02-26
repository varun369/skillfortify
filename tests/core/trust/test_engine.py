"""Tests for the TrustEngine: intrinsic computation, level mapping, edge cases.

Validates:
- Weighted linear combination of trust signals.
- SLSA-inspired score-to-level mapping.
- Engine construction edge cases (invalid weights, negative decay rate).
- Score dataclass invariants.
"""

from __future__ import annotations

import math
from datetime import datetime

import pytest

from skillfortify.core.trust import (
    TrustEngine,
    TrustLevel,
    TrustSignals,
    TrustWeights,
)


# ===========================================================================
# Category 3: Intrinsic score computation (6 tests)
# ===========================================================================


class TestIntrinsicScoreComputation:
    """Tests for weighted linear combination of trust signals."""

    def test_all_zero_signals_give_zero_score(self) -> None:
        """Zero signals produce zero intrinsic score."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.0, behavioral=0.0, community=0.0, historical=0.0
        )
        assert engine.compute_intrinsic(signals) == 0.0

    def test_all_one_signals_give_one_score(self) -> None:
        """Maximum signals with weights summing to 1.0 produce score 1.0."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        assert engine.compute_intrinsic(signals) == pytest.approx(1.0)

    def test_weighted_combination_default_weights(self) -> None:
        """Verify the weighted linear combination with default weights."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.8, behavioral=0.6, community=0.4, historical=1.0
        )
        # T = 0.3*0.8 + 0.3*0.6 + 0.2*0.4 + 0.2*1.0
        # T = 0.24 + 0.18 + 0.08 + 0.20 = 0.70
        expected = 0.3 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4 + 0.2 * 1.0
        assert engine.compute_intrinsic(signals) == pytest.approx(expected)

    def test_custom_weights_change_score(self) -> None:
        """Custom weights produce different scores than defaults."""
        # Heavy behavioral weighting
        weights = TrustWeights(
            provenance=0.1, behavioral=0.6, community=0.2, historical=0.1
        )
        engine = TrustEngine(weights=weights)
        signals = TrustSignals(
            provenance=1.0, behavioral=0.5, community=0.0, historical=0.0
        )
        # T = 0.1*1.0 + 0.6*0.5 + 0.2*0.0 + 0.1*0.0 = 0.40
        expected = 0.1 * 1.0 + 0.6 * 0.5 + 0.2 * 0.0 + 0.1 * 0.0
        assert engine.compute_intrinsic(signals) == pytest.approx(expected)

    def test_single_signal_contribution(self) -> None:
        """Only one signal is non-zero: score = weight * signal."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.0, behavioral=0.0, community=0.0, historical=0.0
        )
        # T = 0.3*1.0 + 0.3*0.0 + 0.2*0.0 + 0.2*0.0 = 0.3
        assert engine.compute_intrinsic(signals) == pytest.approx(0.3)

    def test_invalid_signals_raises(self) -> None:
        """Passing invalid signals to compute_intrinsic raises ValueError."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.5, behavioral=0.0, community=0.0, historical=0.0
        )
        with pytest.raises(ValueError):
            engine.compute_intrinsic(signals)


# ===========================================================================
# Category 4: Trust level mapping (7 tests)
# ===========================================================================


class TestTrustLevelMapping:
    """Tests for score-to-level mapping (SLSA-inspired)."""

    def test_zero_score_is_unsigned(self) -> None:
        """Score 0.0 maps to UNSIGNED."""
        engine = TrustEngine()
        assert engine.score_to_level(0.0) == TrustLevel.UNSIGNED

    def test_below_025_is_unsigned(self) -> None:
        """Score just below 0.25 maps to UNSIGNED."""
        engine = TrustEngine()
        assert engine.score_to_level(0.24) == TrustLevel.UNSIGNED

    def test_exact_025_is_signed(self) -> None:
        """Score exactly 0.25 maps to SIGNED."""
        engine = TrustEngine()
        assert engine.score_to_level(0.25) == TrustLevel.SIGNED

    def test_050_is_community_verified(self) -> None:
        """Score exactly 0.50 maps to COMMUNITY_VERIFIED."""
        engine = TrustEngine()
        assert engine.score_to_level(0.50) == TrustLevel.COMMUNITY_VERIFIED

    def test_075_is_formally_verified(self) -> None:
        """Score exactly 0.75 maps to FORMALLY_VERIFIED."""
        engine = TrustEngine()
        assert engine.score_to_level(0.75) == TrustLevel.FORMALLY_VERIFIED

    def test_one_is_formally_verified(self) -> None:
        """Score 1.0 maps to FORMALLY_VERIFIED."""
        engine = TrustEngine()
        assert engine.score_to_level(1.0) == TrustLevel.FORMALLY_VERIFIED


# ===========================================================================
# Category 9: Edge cases (5 tests)
# ===========================================================================


class TestEdgeCases:
    """Tests for boundary conditions and edge cases."""

    def test_completely_untrusted_skill(self) -> None:
        """A skill with all zero signals has zero trust and UNSIGNED level."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.0, behavioral=0.0, community=0.0, historical=0.0
        )
        score = engine.compute_score("malicious-skill", "0.0.1", signals)
        assert score.intrinsic_score == 0.0
        assert score.effective_score == 0.0
        assert score.level == TrustLevel.UNSIGNED

    def test_fully_trusted_skill(self) -> None:
        """A skill with all max signals has trust 1.0 and FORMALLY_VERIFIED."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        score = engine.compute_score("trusted-skill", "2.0.0", signals)
        assert score.intrinsic_score == pytest.approx(1.0)
        assert score.effective_score == pytest.approx(1.0)
        assert score.level == TrustLevel.FORMALLY_VERIFIED

    def test_score_carries_signals(self) -> None:
        """The computed TrustScore retains the original signals."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.3, behavioral=0.7, community=0.5, historical=0.9
        )
        score = engine.compute_score("skill", "1.0.0", signals)
        assert score.signals is signals

    def test_negative_decay_rate_raises(self) -> None:
        """A negative decay rate is rejected at construction."""
        with pytest.raises(ValueError, match="non-negative"):
            TrustEngine(decay_rate=-0.01)

    def test_invalid_weights_rejected_at_construction(self) -> None:
        """Invalid weights are rejected when the engine is constructed."""
        bad_weights = TrustWeights(
            provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
        )
        with pytest.raises(ValueError):
            TrustEngine(weights=bad_weights)

    def test_decay_with_naive_datetime(self) -> None:
        """Naive datetimes (no timezone) are treated as UTC."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        score = engine.compute_score("skill", "1.0.0", signals)

        last_update = datetime(2026, 1, 1)  # naive
        current = datetime(2026, 1, 11)  # 10 days later, naive
        decayed = engine.apply_decay(score, last_update, current)

        expected = math.exp(-0.01 * 10)
        assert decayed.effective_score == pytest.approx(expected, abs=0.01)
