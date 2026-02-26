"""Property-based tests for capability lattice algebraic laws.

Verifies that AccessLevel forms a valid bounded lattice under join (max)
and meet (min), and that Capability subsumption is a valid partial order.
Uses Hypothesis to exhaustively test all element combinations.

Lattice: L_cap = ({NONE, READ, WRITE, ADMIN}, <=)
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from skillfortify.core.capabilities import AccessLevel, Capability, CapabilitySet


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

access_levels = st.sampled_from(list(AccessLevel))
resources = st.sampled_from(["filesystem", "network", "shell", "environment"])


# ---------------------------------------------------------------------------
# Lattice laws for AccessLevel.join (least upper bound)
# ---------------------------------------------------------------------------


class TestJoinLaws:
    """Algebraic laws for the join (LUB) operation on AccessLevel."""

    @given(a=access_levels, b=access_levels)
    def test_commutativity(self, a: AccessLevel, b: AccessLevel) -> None:
        """join(a, b) == join(b, a)."""
        assert AccessLevel.join(a, b) == AccessLevel.join(b, a)

    @given(a=access_levels, b=access_levels, c=access_levels)
    def test_associativity(
        self, a: AccessLevel, b: AccessLevel, c: AccessLevel
    ) -> None:
        """join(join(a, b), c) == join(a, join(b, c))."""
        lhs = AccessLevel.join(AccessLevel.join(a, b), c)
        rhs = AccessLevel.join(a, AccessLevel.join(b, c))
        assert lhs == rhs

    @given(a=access_levels)
    def test_idempotency(self, a: AccessLevel) -> None:
        """join(a, a) == a."""
        assert AccessLevel.join(a, a) == a

    @given(a=access_levels)
    def test_bottom_identity(self, a: AccessLevel) -> None:
        """join(a, NONE) == a -- NONE is the identity for join."""
        assert AccessLevel.join(a, AccessLevel.bottom()) == a

    @given(a=access_levels)
    def test_top_absorbing(self, a: AccessLevel) -> None:
        """join(a, ADMIN) == ADMIN -- ADMIN absorbs join."""
        assert AccessLevel.join(a, AccessLevel.top()) == AccessLevel.top()

    @given(a=access_levels, b=access_levels)
    def test_join_upper_bound(self, a: AccessLevel, b: AccessLevel) -> None:
        """join(a, b) >= a and join(a, b) >= b."""
        j = AccessLevel.join(a, b)
        assert j >= a
        assert j >= b


# ---------------------------------------------------------------------------
# Lattice laws for AccessLevel.meet (greatest lower bound)
# ---------------------------------------------------------------------------


class TestMeetLaws:
    """Algebraic laws for the meet (GLB) operation on AccessLevel."""

    @given(a=access_levels, b=access_levels)
    def test_commutativity(self, a: AccessLevel, b: AccessLevel) -> None:
        """meet(a, b) == meet(b, a)."""
        assert AccessLevel.meet(a, b) == AccessLevel.meet(b, a)

    @given(a=access_levels, b=access_levels, c=access_levels)
    def test_associativity(
        self, a: AccessLevel, b: AccessLevel, c: AccessLevel
    ) -> None:
        """meet(meet(a, b), c) == meet(a, meet(b, c))."""
        lhs = AccessLevel.meet(AccessLevel.meet(a, b), c)
        rhs = AccessLevel.meet(a, AccessLevel.meet(b, c))
        assert lhs == rhs

    @given(a=access_levels)
    def test_idempotency(self, a: AccessLevel) -> None:
        """meet(a, a) == a."""
        assert AccessLevel.meet(a, a) == a

    @given(a=access_levels)
    def test_top_identity(self, a: AccessLevel) -> None:
        """meet(a, ADMIN) == a -- ADMIN is the identity for meet."""
        assert AccessLevel.meet(a, AccessLevel.top()) == a

    @given(a=access_levels)
    def test_bottom_absorbing(self, a: AccessLevel) -> None:
        """meet(a, NONE) == NONE -- NONE absorbs meet."""
        assert AccessLevel.meet(a, AccessLevel.bottom()) == AccessLevel.bottom()

    @given(a=access_levels, b=access_levels)
    def test_meet_lower_bound(self, a: AccessLevel, b: AccessLevel) -> None:
        """meet(a, b) <= a and meet(a, b) <= b."""
        m = AccessLevel.meet(a, b)
        assert m <= a
        assert m <= b


# ---------------------------------------------------------------------------
# Absorption laws (join + meet interaction)
# ---------------------------------------------------------------------------


class TestAbsorptionLaws:
    """Absorption laws linking join and meet in a lattice."""

    @given(a=access_levels, b=access_levels)
    def test_join_absorbs_meet(
        self, a: AccessLevel, b: AccessLevel
    ) -> None:
        """join(a, meet(a, b)) == a."""
        assert AccessLevel.join(a, AccessLevel.meet(a, b)) == a

    @given(a=access_levels, b=access_levels)
    def test_meet_absorbs_join(
        self, a: AccessLevel, b: AccessLevel
    ) -> None:
        """meet(a, join(a, b)) == a."""
        assert AccessLevel.meet(a, AccessLevel.join(a, b)) == a


# ---------------------------------------------------------------------------
# Capability subsumption
# ---------------------------------------------------------------------------


class TestSubsumption:
    """Properties of the Capability.subsumes partial order."""

    @given(r=resources, a=access_levels)
    def test_reflexivity(self, r: str, a: AccessLevel) -> None:
        """A capability always subsumes itself."""
        c = Capability(r, a)
        assert c.subsumes(c)

    @given(r=resources, a=access_levels, b=access_levels, c_lvl=access_levels)
    def test_transitivity(
        self, r: str, a: AccessLevel, b: AccessLevel, c_lvl: AccessLevel
    ) -> None:
        """If C1 subsumes C2 and C2 subsumes C3, then C1 subsumes C3."""
        c1 = Capability(r, a)
        c2 = Capability(r, b)
        c3 = Capability(r, c_lvl)
        if c1.subsumes(c2) and c2.subsumes(c3):
            assert c1.subsumes(c3)

    @given(r=resources, a=access_levels, b=access_levels)
    def test_antisymmetry(
        self, r: str, a: AccessLevel, b: AccessLevel
    ) -> None:
        """If C1 subsumes C2 and C2 subsumes C1, then C1 == C2."""
        c1 = Capability(r, a)
        c2 = Capability(r, b)
        if c1.subsumes(c2) and c2.subsumes(c1):
            assert c1 == c2

    @given(
        r1=resources, a1=access_levels,
        r2=st.sampled_from(["clipboard", "browser", "database"]),
        a2=access_levels,
    )
    def test_different_resources_incomparable(
        self, r1: str, a1: AccessLevel, r2: str, a2: AccessLevel
    ) -> None:
        """Capabilities on different resources never subsume each other."""
        c1 = Capability(r1, a1)
        c2 = Capability(r2, a2)
        assert not c1.subsumes(c2)
        assert not c2.subsumes(c1)


# ---------------------------------------------------------------------------
# CapabilitySet subset properties
# ---------------------------------------------------------------------------


class TestCapabilitySetSubset:
    """Properties of CapabilitySet.is_subset_of."""

    def test_empty_set_is_subset_of_anything(self) -> None:
        """The empty capability set is a subset of any set."""
        empty = CapabilitySet()
        full = CapabilitySet.from_list([
            Capability("filesystem", AccessLevel.ADMIN),
            Capability("network", AccessLevel.ADMIN),
        ])
        assert empty.is_subset_of(full)
        assert empty.is_subset_of(CapabilitySet())

    @given(r=resources, a=access_levels)
    def test_singleton_subset_reflexivity(
        self, r: str, a: AccessLevel
    ) -> None:
        """A singleton set is always a subset of itself."""
        cs = CapabilitySet.from_list([Capability(r, a)])
        assert cs.is_subset_of(cs)

    @given(r=resources, low=access_levels, high=access_levels)
    def test_lower_level_subset_of_higher(
        self, r: str, low: AccessLevel, high: AccessLevel
    ) -> None:
        """A set with lower access is a subset of one with higher access."""
        if low <= high:
            low_set = CapabilitySet.from_list([Capability(r, low)])
            high_set = CapabilitySet.from_list([Capability(r, high)])
            assert low_set.is_subset_of(high_set)
