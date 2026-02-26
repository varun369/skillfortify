"""Property-based tests for trust algebra formal properties.

Verifies the formal guarantees of the trust computation engine:
- Theorem 5 (Trust Monotonicity): increasing any signal never decreases score
- Boundedness: trust score always in [0, 1]
- Propagation conservatism: effective_score <= intrinsic_score
- Decay monotonicity: longer time -> lower or equal score
- Weight normalization: default weights sum to 1.0
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, assume
from hypothesis import strategies as st

from skillfortify.core.trust import (
    TrustEngine,
    TrustSignals,
    TrustWeights,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

unit_floats = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
small_positive = st.floats(min_value=0.001, max_value=1.0, allow_nan=False)


def signals_strategy() -> st.SearchStrategy[TrustSignals]:
    """Strategy that generates valid TrustSignals."""
    return st.builds(
        TrustSignals,
        provenance=unit_floats,
        behavioral=unit_floats,
        community=unit_floats,
        historical=unit_floats,
    )


# ---------------------------------------------------------------------------
# Theorem 5: Trust Monotonicity
# ---------------------------------------------------------------------------


class TestTrustMonotonicity:
    """Theorem 5: Increasing any signal never decreases the trust score."""

    @given(signals=signals_strategy(), delta=small_positive)
    def test_increasing_provenance_never_decreases_score(
        self, signals: TrustSignals, delta: float
    ) -> None:
        """Raising provenance signal yields >= trust score."""
        assume(signals.provenance + delta <= 1.0)
        engine = TrustEngine()

        score_before = engine.compute_intrinsic(signals)
        boosted = TrustSignals(
            provenance=signals.provenance + delta,
            behavioral=signals.behavioral,
            community=signals.community,
            historical=signals.historical,
        )
        score_after = engine.compute_intrinsic(boosted)
        assert score_after >= score_before - 1e-9

    @given(signals=signals_strategy(), delta=small_positive)
    def test_increasing_behavioral_never_decreases_score(
        self, signals: TrustSignals, delta: float
    ) -> None:
        """Raising behavioral signal yields >= trust score."""
        assume(signals.behavioral + delta <= 1.0)
        engine = TrustEngine()

        score_before = engine.compute_intrinsic(signals)
        boosted = TrustSignals(
            provenance=signals.provenance,
            behavioral=signals.behavioral + delta,
            community=signals.community,
            historical=signals.historical,
        )
        score_after = engine.compute_intrinsic(boosted)
        assert score_after >= score_before - 1e-9

    @given(signals=signals_strategy(), delta=small_positive)
    def test_increasing_community_never_decreases_score(
        self, signals: TrustSignals, delta: float
    ) -> None:
        """Raising community signal yields >= trust score."""
        assume(signals.community + delta <= 1.0)
        engine = TrustEngine()

        score_before = engine.compute_intrinsic(signals)
        boosted = TrustSignals(
            provenance=signals.provenance,
            behavioral=signals.behavioral,
            community=signals.community + delta,
            historical=signals.historical,
        )
        score_after = engine.compute_intrinsic(boosted)
        assert score_after >= score_before - 1e-9

    @given(signals=signals_strategy(), delta=small_positive)
    def test_increasing_historical_never_decreases_score(
        self, signals: TrustSignals, delta: float
    ) -> None:
        """Raising historical signal yields >= trust score."""
        assume(signals.historical + delta <= 1.0)
        engine = TrustEngine()

        score_before = engine.compute_intrinsic(signals)
        boosted = TrustSignals(
            provenance=signals.provenance,
            behavioral=signals.behavioral,
            community=signals.community,
            historical=signals.historical + delta,
        )
        score_after = engine.compute_intrinsic(boosted)
        assert score_after >= score_before - 1e-9

    @given(s1=signals_strategy(), s2=signals_strategy())
    def test_component_wise_ge_implies_score_ge(
        self, s1: TrustSignals, s2: TrustSignals
    ) -> None:
        """If s1 >= s2 component-wise, then T(s1) >= T(s2)."""
        if s1.component_wise_ge(s2):
            engine = TrustEngine()
            assert engine.compute_intrinsic(s1) >= engine.compute_intrinsic(s2) - 1e-9


# ---------------------------------------------------------------------------
# Boundedness
# ---------------------------------------------------------------------------


class TestBoundedness:
    """Trust scores are always in [0, 1]."""

    @given(signals=signals_strategy())
    def test_intrinsic_score_bounded(self, signals: TrustSignals) -> None:
        """Intrinsic score is in [0, 1]."""
        engine = TrustEngine()
        score = engine.compute_intrinsic(signals)
        assert 0.0 <= score <= 1.0

    @given(signals=signals_strategy())
    def test_full_score_bounded(self, signals: TrustSignals) -> None:
        """Full TrustScore effective_score is in [0, 1]."""
        engine = TrustEngine()
        ts = engine.compute_score("skill", "1.0.0", signals)
        assert 0.0 <= ts.intrinsic_score <= 1.0
        assert 0.0 <= ts.effective_score <= 1.0

    def test_all_zero_signals_yield_zero(self) -> None:
        """Signals all at 0.0 produce a score of 0.0."""
        signals = TrustSignals(0.0, 0.0, 0.0, 0.0)
        engine = TrustEngine()
        assert engine.compute_intrinsic(signals) == 0.0

    def test_all_one_signals_yield_one(self) -> None:
        """Signals all at 1.0 produce a score of 1.0."""
        signals = TrustSignals(1.0, 1.0, 1.0, 1.0)
        engine = TrustEngine()
        assert engine.compute_intrinsic(signals) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Propagation conservatism
# ---------------------------------------------------------------------------


class TestPropagationConservatism:
    """Effective score <= intrinsic score when dependencies exist."""

    @given(
        parent_signals=signals_strategy(),
        dep_signals=signals_strategy(),
    )
    def test_effective_le_intrinsic_with_deps(
        self, parent_signals: TrustSignals, dep_signals: TrustSignals
    ) -> None:
        """With any dependency, effective_score <= intrinsic_score."""
        engine = TrustEngine()
        dep_score = engine.compute_score("dep", "1.0.0", dep_signals)
        parent_score = engine.compute_score(
            "parent", "1.0.0", parent_signals,
            dependency_scores=[dep_score],
        )
        assert parent_score.effective_score <= parent_score.intrinsic_score + 1e-9

    @given(signals=signals_strategy())
    def test_no_deps_effective_equals_intrinsic(
        self, signals: TrustSignals
    ) -> None:
        """Without dependencies, effective_score == intrinsic_score."""
        engine = TrustEngine()
        score = engine.compute_score("skill", "1.0.0", signals)
        assert score.effective_score == pytest.approx(score.intrinsic_score)


# ---------------------------------------------------------------------------
# Decay monotonicity
# ---------------------------------------------------------------------------


class TestDecayMonotonicity:
    """Longer elapsed time -> lower or equal score."""

    @given(signals=signals_strategy(), days=st.integers(min_value=0, max_value=365))
    def test_decay_never_increases_score(
        self, signals: TrustSignals, days: int
    ) -> None:
        """Decayed score is <= original effective score."""
        engine = TrustEngine(decay_rate=0.01)
        score = engine.compute_score("skill", "1.0.0", signals)

        now = datetime.now(timezone.utc)
        last_update = now - timedelta(days=days)
        decayed = engine.apply_decay(score, last_update, now)
        assert decayed.effective_score <= score.effective_score + 1e-9

    @given(
        signals=signals_strategy(),
        d1=st.integers(min_value=0, max_value=180),
        d2=st.integers(min_value=0, max_value=180),
    )
    def test_more_days_means_more_decay(
        self, signals: TrustSignals, d1: int, d2: int
    ) -> None:
        """If d1 <= d2, then decayed(d1) >= decayed(d2)."""
        assume(d1 <= d2)
        engine = TrustEngine(decay_rate=0.01)
        score = engine.compute_score("skill", "1.0.0", signals)

        now = datetime.now(timezone.utc)
        decayed_1 = engine.apply_decay(
            score, now - timedelta(days=d1), now
        )
        decayed_2 = engine.apply_decay(
            score, now - timedelta(days=d2), now
        )
        assert decayed_1.effective_score >= decayed_2.effective_score - 1e-9


# ---------------------------------------------------------------------------
# Weight normalization
# ---------------------------------------------------------------------------


class TestWeightNormalization:
    """Trust weights must satisfy formal constraints."""

    def test_default_weights_sum_to_one(self) -> None:
        """Default TrustWeights sum to exactly 1.0."""
        w = TrustWeights()
        total = w.provenance + w.behavioral + w.community + w.historical
        assert total == pytest.approx(1.0)

    def test_negative_weight_rejected(self) -> None:
        """Negative weights are rejected to preserve monotonicity."""
        w = TrustWeights(provenance=-0.1, behavioral=0.4,
                         community=0.4, historical=0.3)
        with pytest.raises(ValueError):
            w.validate()

    def test_non_unit_sum_rejected(self) -> None:
        """Weights not summing to 1.0 are rejected."""
        w = TrustWeights(provenance=0.5, behavioral=0.5,
                         community=0.5, historical=0.5)
        with pytest.raises(ValueError):
            w.validate()
