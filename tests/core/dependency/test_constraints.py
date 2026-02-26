"""Tests for VersionConstraint parsing and satisfaction.

Validates that the constraint engine correctly evaluates exact match (==),
range (>=, <=, >, <), not-equal (!=), caret (^), tilde (~), wildcard (*),
and compound comma-separated constraints against semantic version strings.
"""

from __future__ import annotations

import pytest

from skillfortify.core.dependency import (
    VersionConstraint,
    _parse_version_tuple,
)


class TestVersionConstraint:
    """Tests for VersionConstraint parsing and the ``satisfies()`` method."""

    def test_exact_match_satisfies(self) -> None:
        """Exact match ==1.0.0 satisfies only 1.0.0."""
        vc = VersionConstraint("==1.0.0")
        assert vc.satisfies("1.0.0") is True
        assert vc.satisfies("1.0.1") is False
        assert vc.satisfies("0.9.9") is False

    def test_gte_constraint(self) -> None:
        """>=1.0.0 satisfies 1.0.0 and above."""
        vc = VersionConstraint(">=1.0.0")
        assert vc.satisfies("1.0.0") is True
        assert vc.satisfies("1.0.1") is True
        assert vc.satisfies("2.0.0") is True
        assert vc.satisfies("0.9.9") is False

    def test_lte_constraint(self) -> None:
        """<=2.0.0 satisfies 2.0.0 and below."""
        vc = VersionConstraint("<=2.0.0")
        assert vc.satisfies("2.0.0") is True
        assert vc.satisfies("1.99.99") is True
        assert vc.satisfies("2.0.1") is False

    def test_gt_constraint(self) -> None:
        """>1.0.0 is exclusive: 1.0.0 does NOT satisfy."""
        vc = VersionConstraint(">1.0.0")
        assert vc.satisfies("1.0.0") is False
        assert vc.satisfies("1.0.1") is True

    def test_lt_constraint(self) -> None:
        """<2.0.0 is exclusive: 2.0.0 does NOT satisfy."""
        vc = VersionConstraint("<2.0.0")
        assert vc.satisfies("2.0.0") is False
        assert vc.satisfies("1.99.99") is True

    def test_not_equal_constraint(self) -> None:
        """!=1.0.0 satisfies everything except 1.0.0."""
        vc = VersionConstraint("!=1.0.0")
        assert vc.satisfies("1.0.0") is False
        assert vc.satisfies("1.0.1") is True
        assert vc.satisfies("0.9.9") is True

    def test_wildcard_satisfies_anything(self) -> None:
        """Wildcard * satisfies any valid version."""
        vc = VersionConstraint("*")
        assert vc.satisfies("0.0.1") is True
        assert vc.satisfies("99.99.99") is True

    def test_compound_range_constraint(self) -> None:
        """Compound constraint >=1.0.0,<2.0.0 (inclusive lower, exclusive upper)."""
        vc = VersionConstraint(">=1.0.0,<2.0.0")
        assert vc.satisfies("1.0.0") is True
        assert vc.satisfies("1.5.3") is True
        assert vc.satisfies("1.99.99") is True
        assert vc.satisfies("2.0.0") is False
        assert vc.satisfies("0.9.9") is False

    def test_tilde_constraint(self) -> None:
        """Tilde ~1.2.0 allows patch-level changes only (same major.minor)."""
        vc = VersionConstraint("~1.2.0")
        assert vc.satisfies("1.2.0") is True
        assert vc.satisfies("1.2.5") is True
        assert vc.satisfies("1.3.0") is False
        assert vc.satisfies("2.0.0") is False

    def test_caret_constraint(self) -> None:
        """Caret ^1.2.3 allows minor+patch changes (same major)."""
        vc = VersionConstraint("^1.2.3")
        assert vc.satisfies("1.2.3") is True
        assert vc.satisfies("1.9.0") is True
        assert vc.satisfies("1.2.2") is False  # below minimum
        assert vc.satisfies("2.0.0") is False  # different major

    def test_caret_zero_major(self) -> None:
        """Caret ^0.2.3 with major=0 locks to same major.minor."""
        vc = VersionConstraint("^0.2.3")
        assert vc.satisfies("0.2.3") is True
        assert vc.satisfies("0.2.9") is True
        assert vc.satisfies("0.3.0") is False
        assert vc.satisfies("1.0.0") is False

    def test_invalid_version_raises(self) -> None:
        """Parsing an invalid version string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid semantic version"):
            _parse_version_tuple("not-a-version")

    def test_invalid_constraint_atom_raises(self) -> None:
        """An invalid constraint atom raises ValueError."""
        vc = VersionConstraint("~=1.0.0")  # ~= not supported
        with pytest.raises(ValueError, match="Invalid constraint atom"):
            vc.satisfies("1.0.0")
