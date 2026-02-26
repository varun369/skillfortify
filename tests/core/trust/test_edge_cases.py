"""Tests for trust engine edge cases.

Verifies:
    - All signals = 0.0 yields score = 0.0, level = UNSIGNED.
    - All signals = 1.0 yields score = 1.0, level = FORMALLY_VERIFIED.
    - Single signal = 1.0, rest = 0.0 yields correct weighted result.
    - 365-day decay yields very low but non-negative score.
    - Very small decay rate (lambda=0.0001) yields minimal decay.
    - Negative time delta (future update) yields no decay.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from skillfortify.core.trust.engine import TrustEngine
from skillfortify.core.trust.models import (
    TrustLevel,
    TrustSignals,
)


class TestAllSignalsZero:
    """Trust computation when all signals are 0.0."""

    def test_all_zero_intrinsic_is_zero(self) -> None:
        """All-zero signals yield intrinsic score of 0.0."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.0, behavioral=0.0, community=0.0, historical=0.0,
        )
        intrinsic = engine.compute_intrinsic(signals)
        assert intrinsic == 0.0

    def test_all_zero_score_level_unsigned(self) -> None:
        """All-zero signals yield trust level UNSIGNED."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.0, behavioral=0.0, community=0.0, historical=0.0,
        )
        score = engine.compute_score("zero-skill", "0.0.0", signals)
        assert score.effective_score == 0.0
        assert score.level == TrustLevel.UNSIGNED


class TestAllSignalsOne:
    """Trust computation when all signals are 1.0."""

    def test_all_one_intrinsic_is_one(self) -> None:
        """All-one signals yield intrinsic score of 1.0."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0,
        )
        intrinsic = engine.compute_intrinsic(signals)
        assert intrinsic == pytest.approx(1.0)

    def test_all_one_score_level_formally_verified(self) -> None:
        """All-one signals yield trust level FORMALLY_VERIFIED."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0,
        )
        score = engine.compute_score("perfect-skill", "1.0.0", signals)
        assert score.effective_score == pytest.approx(1.0)
        assert score.level == TrustLevel.FORMALLY_VERIFIED


class TestSingleSignalActive:
    """Trust computation with only one signal at 1.0, rest at 0.0."""

    def test_provenance_only(self) -> None:
        """Only provenance=1.0 yields score equal to provenance weight."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=1.0, behavioral=0.0, community=0.0, historical=0.0,
        )
        intrinsic = engine.compute_intrinsic(signals)
        # Default provenance weight is 0.3
        assert intrinsic == pytest.approx(0.3)

    def test_behavioral_only(self) -> None:
        """Only behavioral=1.0 yields score equal to behavioral weight."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.0, behavioral=1.0, community=0.0, historical=0.0,
        )
        intrinsic = engine.compute_intrinsic(signals)
        assert intrinsic == pytest.approx(0.3)

    def test_community_only(self) -> None:
        """Only community=1.0 yields score equal to community weight."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.0, behavioral=0.0, community=1.0, historical=0.0,
        )
        intrinsic = engine.compute_intrinsic(signals)
        assert intrinsic == pytest.approx(0.2)


class TestDecayEdgeCases:
    """Trust decay boundary conditions."""

    def test_365_day_decay_nonnegative(self) -> None:
        """365-day decay should produce a very low but non-negative score."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0,
        )
        base_score = engine.compute_score("old-skill", "1.0.0", signals)

        now = datetime(2026, 2, 26, tzinfo=timezone.utc)
        one_year_ago = now - timedelta(days=365)
        decayed = engine.apply_decay(base_score, one_year_ago, now)

        # exp(-0.01 * 365) ~ 0.0255. Still positive.
        assert decayed.effective_score >= 0.0
        assert decayed.effective_score < 0.05
        expected = base_score.effective_score * math.exp(-0.01 * 365)
        assert decayed.effective_score == pytest.approx(expected, abs=1e-6)

    def test_very_small_decay_rate(self) -> None:
        """Very small lambda=0.0001 causes minimal decay over 30 days."""
        engine = TrustEngine(decay_rate=0.0001)
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0,
        )
        base_score = engine.compute_score("stable-skill", "1.0.0", signals)

        now = datetime(2026, 2, 26, tzinfo=timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        decayed = engine.apply_decay(base_score, thirty_days_ago, now)

        # exp(-0.0001 * 30) ~ 0.997. Almost no decay.
        assert decayed.effective_score > 0.99
        assert decayed.effective_score <= 1.0

    def test_future_update_no_decay(self) -> None:
        """If last_update is in the future, no decay is applied."""
        engine = TrustEngine(decay_rate=0.01)
        signals = TrustSignals(
            provenance=0.8, behavioral=0.9, community=0.7, historical=0.6,
        )
        base_score = engine.compute_score("future-skill", "2.0.0", signals)

        now = datetime(2026, 2, 26, tzinfo=timezone.utc)
        future = now + timedelta(days=10)
        decayed = engine.apply_decay(base_score, future, now)

        # No decay: effective score unchanged.
        assert decayed.effective_score == pytest.approx(
            base_score.effective_score, abs=1e-9,
        )
