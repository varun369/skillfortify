"""Tests for trust data models: TrustSignals, TrustWeights, TrustLevel.

Validates input range checking for signals, weight constraint enforcement
(sum to 1, non-negative), and basic dataclass behaviour for the trust
algebra's core data structures.
"""

from __future__ import annotations

import pytest

from skillfortify.core.trust import (
    TrustLevel,
    TrustSignals,
    TrustWeights,
)


# ===========================================================================
# Category 1: TrustSignals validation (6 tests)
# ===========================================================================


class TestTrustSignalsValidation:
    """Tests for TrustSignals range validation."""

    def test_valid_signals_pass_validation(self) -> None:
        """Signals in [0, 1] pass validation without error."""
        signals = TrustSignals(
            provenance=0.5, behavioral=1.0, community=0.0, historical=0.7
        )
        signals.validate()  # Should not raise

    def test_negative_signal_raises(self) -> None:
        """A negative signal value must be rejected."""
        signals = TrustSignals(
            provenance=-0.1, behavioral=0.5, community=0.5, historical=0.5
        )
        with pytest.raises(ValueError, match="provenance.*must be in.*0.*1"):
            signals.validate()

    def test_signal_above_one_raises(self) -> None:
        """A signal value > 1.0 must be rejected."""
        signals = TrustSignals(
            provenance=0.5, behavioral=1.1, community=0.5, historical=0.5
        )
        with pytest.raises(ValueError, match="behavioral.*must be in.*0.*1"):
            signals.validate()

    def test_default_signals_are_zero(self) -> None:
        """Default-constructed signals should all be zero."""
        signals = TrustSignals()
        assert signals.provenance == 0.0
        assert signals.behavioral == 0.0
        assert signals.community == 0.0
        assert signals.historical == 0.0
        signals.validate()

    def test_all_ones_valid(self) -> None:
        """Maximum trust across all signals is valid."""
        signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        signals.validate()

    def test_as_dict_returns_correct_values(self) -> None:
        """as_dict should return all four signal values by name."""
        signals = TrustSignals(
            provenance=0.1, behavioral=0.2, community=0.3, historical=0.4
        )
        d = signals.as_dict()
        assert d == {
            "provenance": 0.1,
            "behavioral": 0.2,
            "community": 0.3,
            "historical": 0.4,
        }


# ===========================================================================
# Category 2: TrustWeights validation (4 tests)
# ===========================================================================


class TestTrustWeightsValidation:
    """Tests for TrustWeights sum and non-negativity constraints."""

    def test_default_weights_are_valid(self) -> None:
        """Default weights (0.3, 0.3, 0.2, 0.2) should pass validation."""
        weights = TrustWeights()
        weights.validate()

    def test_weights_not_summing_to_one_raises(self) -> None:
        """Weights that don't sum to 1.0 must be rejected."""
        weights = TrustWeights(
            provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
        )
        with pytest.raises(ValueError, match="sum to 1.0"):
            weights.validate()

    def test_negative_weight_raises(self) -> None:
        """A negative weight must be rejected (violates monotonicity)."""
        weights = TrustWeights(
            provenance=-0.1, behavioral=0.4, community=0.4, historical=0.3
        )
        with pytest.raises(ValueError, match="non-negative"):
            weights.validate()

    def test_custom_valid_weights(self) -> None:
        """Custom weights summing to 1.0 should pass validation."""
        weights = TrustWeights(
            provenance=0.1, behavioral=0.5, community=0.2, historical=0.2
        )
        weights.validate()


# ===========================================================================
# TrustLevel ordering (1 test)
# ===========================================================================


class TestTrustLevelOrdering:
    """Tests for TrustLevel enum ordering."""

    def test_level_ordering(self) -> None:
        """Trust levels have strict ordering: UNSIGNED < ... < FORMALLY_VERIFIED."""
        assert TrustLevel.UNSIGNED < TrustLevel.SIGNED
        assert TrustLevel.SIGNED < TrustLevel.COMMUNITY_VERIFIED
        assert TrustLevel.COMMUNITY_VERIFIED < TrustLevel.FORMALLY_VERIFIED


# ===========================================================================
# Component-wise comparison (1 test)
# ===========================================================================


class TestComponentWiseComparison:
    """Tests for TrustSignals.component_wise_ge."""

    def test_component_wise_ge(self) -> None:
        """component_wise_ge correctly compares signal vectors."""
        low = TrustSignals(
            provenance=0.1, behavioral=0.2, community=0.3, historical=0.4
        )
        high = TrustSignals(
            provenance=0.5, behavioral=0.6, community=0.7, historical=0.8
        )
        assert high.component_wise_ge(low)
        assert not low.component_wise_ge(high)
