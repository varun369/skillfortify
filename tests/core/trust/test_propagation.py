"""Tests for trust propagation through dependency chains.

Validates:
- Multiplicative trust composition through dependencies.
- Conservative (min-over-deps) semantics.
- End-to-end chain propagation from leaf to root.
"""

from __future__ import annotations

import pytest

from skillfortify.core.trust import (
    TrustEngine,
    TrustLevel,
    TrustSignals,
)


# ===========================================================================
# Category 5: Trust propagation through dependencies (6 tests)
# ===========================================================================


class TestTrustPropagation:
    """Tests for multiplicative trust composition through dependency chains."""

    def test_no_dependencies_effective_equals_intrinsic(self) -> None:
        """Without dependencies, effective_score == intrinsic_score."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )
        score = engine.compute_score("skill-a", "1.0.0", signals)
        assert score.effective_score == pytest.approx(score.intrinsic_score)

    def test_single_dependency_reduces_trust(self) -> None:
        """A dependency with trust < 1.0 reduces the effective trust."""
        engine = TrustEngine()

        dep_signals = TrustSignals(
            provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
        )
        dep_score = engine.compute_score("dep-a", "1.0.0", dep_signals)
        assert dep_score.effective_score == pytest.approx(0.5)

        main_signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        main_score = engine.compute_score(
            "main", "1.0.0", main_signals, [dep_score]
        )

        # effective = 1.0 * min(0.5) = 0.5
        assert main_score.intrinsic_score == pytest.approx(1.0)
        assert main_score.effective_score == pytest.approx(0.5)

    def test_weakest_link_determines_effective(self) -> None:
        """With multiple dependencies, the weakest determines effective trust."""
        engine = TrustEngine()

        dep_high = engine.compute_score(
            "dep-high",
            "1.0.0",
            TrustSignals(
                provenance=0.9, behavioral=0.9, community=0.9, historical=0.9
            ),
        )
        dep_low = engine.compute_score(
            "dep-low",
            "1.0.0",
            TrustSignals(
                provenance=0.2, behavioral=0.2, community=0.2, historical=0.2
            ),
        )

        main_signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        main_score = engine.compute_score(
            "main", "1.0.0", main_signals, [dep_high, dep_low]
        )

        assert main_score.effective_score == pytest.approx(
            1.0 * dep_low.effective_score
        )

    def test_zero_dependency_zeros_effective(self) -> None:
        """A zero-trust dependency completely eliminates effective trust."""
        engine = TrustEngine()

        dep_zero = engine.compute_score(
            "dep-zero",
            "1.0.0",
            TrustSignals(
                provenance=0.0, behavioral=0.0, community=0.0, historical=0.0
            ),
        )

        main_signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        main_score = engine.compute_score(
            "main", "1.0.0", main_signals, [dep_zero]
        )

        assert main_score.intrinsic_score == pytest.approx(1.0)
        assert main_score.effective_score == pytest.approx(0.0)

    def test_effective_score_never_exceeds_intrinsic(self) -> None:
        """Effective score is always <= intrinsic (dependencies only reduce)."""
        engine = TrustEngine()

        dep = engine.compute_score(
            "dep",
            "1.0.0",
            TrustSignals(
                provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
            ),
        )

        main_signals = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )
        main_score = engine.compute_score(
            "main", "1.0.0", main_signals, [dep]
        )

        assert main_score.effective_score <= main_score.intrinsic_score

    def test_level_reflects_effective_not_intrinsic(self) -> None:
        """Trust level is derived from effective_score, not intrinsic_score."""
        engine = TrustEngine()

        dep = engine.compute_score(
            "dep",
            "1.0.0",
            TrustSignals(
                provenance=0.2, behavioral=0.2, community=0.2, historical=0.2
            ),
        )
        main_signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )
        main_score = engine.compute_score(
            "main", "1.0.0", main_signals, [dep]
        )

        assert main_score.level == engine.score_to_level(
            main_score.effective_score
        )
        assert main_score.level < TrustLevel.FORMALLY_VERIFIED


# ===========================================================================
# Category 8: Chain propagation (4 tests)
# ===========================================================================


class TestChainPropagation:
    """Tests for end-to-end trust propagation through dependency chains."""

    def test_single_element_chain(self) -> None:
        """A chain with one element has no dependencies."""
        engine = TrustEngine()
        signals = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )
        scores = engine.propagate_through_chain(
            [("lib-a", "1.0.0", signals)]
        )
        assert len(scores) == 1
        assert scores[0].effective_score == pytest.approx(
            scores[0].intrinsic_score
        )

    def test_two_element_chain(self) -> None:
        """Root's effective trust depends on the leaf in a two-element chain."""
        engine = TrustEngine()
        leaf_signals = TrustSignals(
            provenance=0.5, behavioral=0.5, community=0.5, historical=0.5
        )
        root_signals = TrustSignals(
            provenance=1.0, behavioral=1.0, community=1.0, historical=1.0
        )

        scores = engine.propagate_through_chain(
            [
                ("leaf", "1.0.0", leaf_signals),
                ("root", "1.0.0", root_signals),
            ]
        )

        assert len(scores) == 2
        assert scores[0].effective_score == pytest.approx(0.5)
        assert scores[1].effective_score == pytest.approx(0.5)

    def test_three_element_chain_cascading(self) -> None:
        """Trust cascades: each link in the chain reduces effective trust."""
        engine = TrustEngine()

        signals_08 = TrustSignals(
            provenance=0.8, behavioral=0.8, community=0.8, historical=0.8
        )

        scores = engine.propagate_through_chain(
            [
                ("leaf", "1.0.0", signals_08),
                ("mid", "1.0.0", signals_08),
                ("root", "1.0.0", signals_08),
            ]
        )

        assert len(scores) == 3
        assert scores[0].effective_score == pytest.approx(0.8)
        assert scores[1].effective_score == pytest.approx(0.8 * 0.8)
        assert scores[2].effective_score == pytest.approx(0.8 * 0.8 * 0.8)

    def test_empty_chain_raises(self) -> None:
        """An empty chain should raise ValueError."""
        engine = TrustEngine()
        with pytest.raises(ValueError, match="must not be empty"):
            engine.propagate_through_chain([])
