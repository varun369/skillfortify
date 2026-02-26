"""Tests for trust decay and Theorem 5 (monotonicity).

Validates:
- Exponential temporal decay for unmaintained skills.
- Evidence updates with Theorem 5 (Trust Monotonicity) guarantee.
- Property-based (Hypothesis) exhaustive exploration of the signal space.

Theorem 5 (Trust Monotonicity):
    Adding positive evidence (increasing any signal) NEVER reduces the
    trust score.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from skillfortify.core.trust import (
    TrustEngine,
    TrustLevel,
    TrustSignals,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies for property-based testing
# ---------------------------------------------------------------------------

unit_floats = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)

trust_signals_strategy = st.builds(
    TrustSignals,
    provenance=unit_floats,
    behavioral=unit_floats,
    community=unit_floats,
    historical=unit_floats,
)

positive_deltas = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)


# ===========================================================================
# Category 6: Trust decay over time (6 tests)
# ===========================================================================


class TestTrustDecay:
    """Tests for exponential temporal decay of trust scores."""

    def test_no_elapsed_time_no_decay(self) -> None:
        """Zero elapsed time produces no decay."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )
        score = engine.compute_score("skill", "1.0.0", signals)

        now = datetime(2026, 2, 26, tzinfo=timezone.utc)
        decayed = engine.apply_decay(score, last_update=now, current_time=now)
        assert decayed.effective_score == pytest.approx(score.effective_score)

    def test_decay_after_69_days_halves_trust(self) -> None:
        """At lambda=0.01, trust halves after ~69.3 days (ln(2)/0.01)."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        score = engine.compute_score("skill", "1.0.0", signals)

        half_life_days = math.log(2) / 0.01  # ~69.3 days
        last_update = datetime(2026, 1, 1, tzinfo=timezone.utc)
        current = last_update + timedelta(days=half_life_days)
        decayed = engine.apply_decay(score, last_update, current)

        assert decayed.effective_score == pytest.approx(0.5, abs=0.01)

    def test_decay_after_230_days_drops_to_ten_percent(self) -> None:
        """After ~230 days (lambda=0.01), trust drops to ~10%."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        score = engine.compute_score("skill", "1.0.0", signals)

        last_update = datetime(2026, 1, 1, tzinfo=timezone.utc)
        current = last_update + timedelta(days=230)
        decayed = engine.apply_decay(score, last_update, current)

        expected = math.exp(-0.01 * 230)
        assert decayed.effective_score == pytest.approx(expected, abs=0.01)

    def test_future_update_no_decay(self) -> None:
        """If last_update is in the future, no decay is applied."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )
        score = engine.compute_score("skill", "1.0.0", signals)

        now = datetime(2026, 2, 26, tzinfo=timezone.utc)
        future = now + timedelta(days=10)
        decayed = engine.apply_decay(
            score, last_update=future, current_time=now
        )

        assert decayed.effective_score == pytest.approx(score.effective_score)

    def test_decay_changes_level(self) -> None:
        """Sufficient decay can downgrade the trust level."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        score = engine.compute_score("skill", "1.0.0", signals)
        assert score.level == TrustLevel.FORMALLY_VERIFIED

        last_update = datetime(2026, 1, 1, tzinfo=timezone.utc)
        current = last_update + timedelta(days=200)
        decayed = engine.apply_decay(score, last_update, current)
        assert decayed.level == TrustLevel.UNSIGNED

    def test_zero_decay_rate_no_decay(self) -> None:
        """A decay rate of 0.0 means trust never decays."""
        engine = TrustEngine(decay_rate=0.0)
        signals = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )
        score = engine.compute_score("skill", "1.0.0", signals)

        last_update = datetime(2020, 1, 1, tzinfo=timezone.utc)
        current = datetime(2026, 2, 26, tzinfo=timezone.utc)
        decayed = engine.apply_decay(score, last_update, current)

        assert decayed.effective_score == pytest.approx(score.effective_score)


# ===========================================================================
# Category 7: Evidence update and monotonicity -- Theorem 5 (8 tests)
# ===========================================================================


class TestEvidenceUpdateAndMonotonicity:
    """Tests for evidence updates and Theorem 5 (Trust Monotonicity)."""

    def test_positive_evidence_increases_provenance(self) -> None:
        """Adding provenance evidence increases the signal value."""
        engine = TrustEngine()
        current = TrustSignals(
            provenance=0.3, behavioral=0.5, community=0.5, historical=0.5
        )
        updated = engine.update_with_evidence(current, {"provenance": 0.2})
        assert updated.provenance == pytest.approx(0.5)

    def test_evidence_clamped_to_one(self) -> None:
        """Evidence that would exceed 1.0 is clamped."""
        engine = TrustEngine()
        current = TrustSignals(
            provenance=0.9, behavioral=0.5, community=0.5, historical=0.5
        )
        updated = engine.update_with_evidence(current, {"provenance": 0.5})
        assert updated.provenance == pytest.approx(1.0)

    def test_negative_evidence_raises(self) -> None:
        """Negative evidence delta is rejected (would violate Theorem 5)."""
        engine = TrustEngine()
        current = TrustSignals(
            provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
        )
        with pytest.raises(ValueError, match="non-negative"):
            engine.update_with_evidence(current, {"provenance": -0.1})

    def test_unknown_signal_name_raises(self) -> None:
        """Evidence for an unknown signal name is rejected."""
        engine = TrustEngine()
        current = TrustSignals(
            provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
        )
        with pytest.raises(ValueError, match="Unknown signal name"):
            engine.update_with_evidence(current, {"nonexistent": 0.1})

    def test_monotonicity_manual_all_signals(self) -> None:
        """Theorem 5: increasing any signal never decreases the trust score."""
        engine = TrustEngine()
        base = TrustSignals(
            provenance=0.3, behavioral=0.4, community=0.2, historical=0.5
        )
        base_score = engine.compute_intrinsic(base)

        for signal_name in (
            "provenance",
            "behavioral",
            "community",
            "historical",
        ):
            updated = engine.update_with_evidence(base, {signal_name: 0.1})
            updated_score = engine.compute_intrinsic(updated)
            assert updated_score >= base_score, (
                f"Theorem 5 violated: increasing {signal_name} reduced "
                f"score from {base_score} to {updated_score}"
            )

    def test_monotonicity_multiple_evidence_at_once(self) -> None:
        """Theorem 5: adding evidence to multiple signals simultaneously."""
        engine = TrustEngine()
        base = TrustSignals(
            provenance=0.2, behavioral=0.3, community=0.1, historical=0.4
        )
        base_score = engine.compute_intrinsic(base)

        updated = engine.update_with_evidence(
            base,
            {
                "provenance": 0.1,
                "behavioral": 0.2,
                "community": 0.3,
            },
        )
        updated_score = engine.compute_intrinsic(updated)
        assert updated_score >= base_score

    @given(signals=trust_signals_strategy, delta=positive_deltas)
    @settings(max_examples=100)
    def test_monotonicity_property_provenance(
        self, signals: TrustSignals, delta: float
    ) -> None:
        """Property-based Theorem 5: increasing provenance never reduces score."""
        engine = TrustEngine()
        base_score = engine.compute_intrinsic(signals)

        updated = TrustSignals(
            provenance=min(1.0, signals.provenance + delta),
            behavioral=signals.behavioral,
            community=signals.community,
            historical=signals.historical,
        )
        updated_score = engine.compute_intrinsic(updated)
        assert updated_score >= base_score - 1e-10

    @given(
        signals=trust_signals_strategy,
        dp=positive_deltas,
        db=positive_deltas,
        dc=positive_deltas,
        dh=positive_deltas,
    )
    @settings(max_examples=100)
    def test_monotonicity_property_all_signals(
        self,
        signals: TrustSignals,
        dp: float,
        db: float,
        dc: float,
        dh: float,
    ) -> None:
        """Property-based Theorem 5: increasing ALL signals never reduces score."""
        engine = TrustEngine()
        base_score = engine.compute_intrinsic(signals)

        updated = TrustSignals(
            provenance=min(1.0, signals.provenance + dp),
            behavioral=min(1.0, signals.behavioral + db),
            community=min(1.0, signals.community + dc),
            historical=min(1.0, signals.historical + dh),
        )
        updated_score = engine.compute_intrinsic(updated)
        assert updated_score >= base_score - 1e-10
