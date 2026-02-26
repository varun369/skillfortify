"""Tests for AccessLevel lattice and CAPABILITY_UNIVERSE.

Validates the four-element access level lattice L_cap = ({NONE, READ, WRITE,
ADMIN}, sqsubseteq) and its formal properties: commutativity, associativity,
idempotency, absorption, and identity/absorbing elements.

Property-based tests via Hypothesis ensure the lattice axioms hold for ALL
input combinations.

References:
    Dennis, J.B. & Van Horn, E.C. (1966). "Programming Semantics for
        Multiprogrammed Computations." Communications of the ACM, 9(3).
    Miller, M.S. (2006). "Robust Composition." PhD Thesis, Johns Hopkins.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from skillfortify.core.capabilities import CAPABILITY_UNIVERSE, AccessLevel


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

access_levels = st.sampled_from(list(AccessLevel))


# ---------------------------------------------------------------------------
# TestAccessLevel: The four-element linear order
# ---------------------------------------------------------------------------


class TestAccessLevel:
    """Validate the four-element access level lattice: NONE < READ < WRITE < ADMIN."""

    def test_ordering(self) -> None:
        """NONE < READ < WRITE < ADMIN forms a strict total order."""
        assert AccessLevel.NONE < AccessLevel.READ
        assert AccessLevel.READ < AccessLevel.WRITE
        assert AccessLevel.WRITE < AccessLevel.ADMIN

    def test_ordering_transitive(self) -> None:
        """Transitivity: NONE < ADMIN follows from the chain."""
        assert AccessLevel.NONE < AccessLevel.ADMIN

    def test_int_values(self) -> None:
        """Enum values are 0, 1, 2, 3 -- suitable for direct comparison."""
        assert AccessLevel.NONE.value == 0
        assert AccessLevel.READ.value == 1
        assert AccessLevel.WRITE.value == 2
        assert AccessLevel.ADMIN.value == 3

    def test_exactly_four_levels(self) -> None:
        assert len(AccessLevel) == 4

    def test_join_is_max(self) -> None:
        """join(a, b) = max(a, b) -- the least upper bound on a total order."""
        assert AccessLevel.join(AccessLevel.READ, AccessLevel.WRITE) == AccessLevel.WRITE
        assert AccessLevel.join(AccessLevel.NONE, AccessLevel.ADMIN) == AccessLevel.ADMIN
        assert AccessLevel.join(AccessLevel.READ, AccessLevel.READ) == AccessLevel.READ

    def test_meet_is_min(self) -> None:
        """meet(a, b) = min(a, b) -- the greatest lower bound on a total order."""
        assert AccessLevel.meet(AccessLevel.READ, AccessLevel.WRITE) == AccessLevel.READ
        assert AccessLevel.meet(AccessLevel.NONE, AccessLevel.ADMIN) == AccessLevel.NONE
        assert AccessLevel.meet(AccessLevel.WRITE, AccessLevel.WRITE) == AccessLevel.WRITE

    def test_bottom(self) -> None:
        """bottom() returns NONE, the least element."""
        assert AccessLevel.bottom() == AccessLevel.NONE

    def test_top(self) -> None:
        """top() returns ADMIN, the greatest element."""
        assert AccessLevel.top() == AccessLevel.ADMIN

    def test_bottom_is_identity_for_join(self) -> None:
        """join(a, bottom) = a for all a."""
        for level in AccessLevel:
            assert AccessLevel.join(level, AccessLevel.bottom()) == level

    def test_top_is_identity_for_meet(self) -> None:
        """meet(a, top) = a for all a."""
        for level in AccessLevel:
            assert AccessLevel.meet(level, AccessLevel.top()) == level

    def test_top_is_absorbing_for_join(self) -> None:
        """join(a, top) = top for all a."""
        for level in AccessLevel:
            assert AccessLevel.join(level, AccessLevel.top()) == AccessLevel.top()

    def test_bottom_is_absorbing_for_meet(self) -> None:
        """meet(a, bottom) = bottom for all a."""
        for level in AccessLevel:
            assert AccessLevel.meet(level, AccessLevel.bottom()) == AccessLevel.bottom()


# ---------------------------------------------------------------------------
# TestCapabilityLatticeProperties: Formal lattice axioms via Hypothesis
# ---------------------------------------------------------------------------


class TestCapabilityLatticeProperties:
    """Property-based tests verifying the formal lattice axioms.

    A lattice (L, <=) requires join and meet to be commutative, associative,
    and idempotent, with absorption laws and identity elements.
    """

    @given(a=access_levels, b=access_levels)
    @settings(max_examples=50)
    def test_join_commutative(self, a: AccessLevel, b: AccessLevel) -> None:
        """join(a, b) == join(b, a)."""
        assert AccessLevel.join(a, b) == AccessLevel.join(b, a)

    @given(a=access_levels, b=access_levels, c=access_levels)
    @settings(max_examples=50)
    def test_join_associative(self, a: AccessLevel, b: AccessLevel, c: AccessLevel) -> None:
        """join(join(a, b), c) == join(a, join(b, c))."""
        assert AccessLevel.join(AccessLevel.join(a, b), c) == AccessLevel.join(
            a, AccessLevel.join(b, c)
        )

    @given(a=access_levels)
    @settings(max_examples=20)
    def test_join_idempotent(self, a: AccessLevel) -> None:
        """join(a, a) == a."""
        assert AccessLevel.join(a, a) == a

    @given(a=access_levels)
    @settings(max_examples=20)
    def test_join_with_bottom(self, a: AccessLevel) -> None:
        """join(a, bottom) == a."""
        assert AccessLevel.join(a, AccessLevel.bottom()) == a

    @given(a=access_levels, b=access_levels)
    @settings(max_examples=50)
    def test_meet_commutative(self, a: AccessLevel, b: AccessLevel) -> None:
        """meet(a, b) == meet(b, a)."""
        assert AccessLevel.meet(a, b) == AccessLevel.meet(b, a)

    @given(a=access_levels, b=access_levels, c=access_levels)
    @settings(max_examples=50)
    def test_meet_associative(self, a: AccessLevel, b: AccessLevel, c: AccessLevel) -> None:
        """meet(meet(a, b), c) == meet(a, meet(b, c))."""
        assert AccessLevel.meet(AccessLevel.meet(a, b), c) == AccessLevel.meet(
            a, AccessLevel.meet(b, c)
        )

    @given(a=access_levels)
    @settings(max_examples=20)
    def test_meet_idempotent(self, a: AccessLevel) -> None:
        """meet(a, a) == a."""
        assert AccessLevel.meet(a, a) == a

    @given(a=access_levels)
    @settings(max_examples=20)
    def test_meet_with_top(self, a: AccessLevel) -> None:
        """meet(a, top) == a."""
        assert AccessLevel.meet(a, AccessLevel.top()) == a

    @given(a=access_levels, b=access_levels)
    @settings(max_examples=50)
    def test_absorption_join_meet(self, a: AccessLevel, b: AccessLevel) -> None:
        """a join (a meet b) == a."""
        assert AccessLevel.join(a, AccessLevel.meet(a, b)) == a

    @given(a=access_levels, b=access_levels)
    @settings(max_examples=50)
    def test_absorption_meet_join(self, a: AccessLevel, b: AccessLevel) -> None:
        """a meet (a join b) == a."""
        assert AccessLevel.meet(a, AccessLevel.join(a, b)) == a

    @given(a=access_levels, b=access_levels)
    @settings(max_examples=50)
    def test_join_consistent_with_order(self, a: AccessLevel, b: AccessLevel) -> None:
        """a <= b iff join(a, b) == b."""
        if a <= b:
            assert AccessLevel.join(a, b) == b
        else:
            assert AccessLevel.join(a, b) == a


# ---------------------------------------------------------------------------
# TestCapabilityUniverse: Known resource types
# ---------------------------------------------------------------------------


class TestCapabilityUniverse:
    """Validate CAPABILITY_UNIVERSE -- the set of known resource types."""

    def test_is_frozenset(self) -> None:
        assert isinstance(CAPABILITY_UNIVERSE, frozenset)

    def test_contains_expected_resources(self) -> None:
        expected = {
            "filesystem",
            "network",
            "environment",
            "shell",
            "skill_invoke",
            "clipboard",
            "browser",
            "database",
        }
        assert CAPABILITY_UNIVERSE == expected

    def test_exactly_eight_resources(self) -> None:
        assert len(CAPABILITY_UNIVERSE) == 8

    def test_all_lowercase(self) -> None:
        """Resource names must be lowercase for consistent keying."""
        for resource in CAPABILITY_UNIVERSE:
            assert resource == resource.lower()
