"""Tests for Capability dataclass and CapabilitySet collection.

Validates the Dennis & Van Horn (1966) capability pairing (resource, access)
and the keyed collection that enforces least-privilege semantics. Tests cover
subsumption, set membership, permits/subset/violations operations, and
iteration semantics.

References:
    Dennis, J.B. & Van Horn, E.C. (1966). "Programming Semantics for
        Multiprogrammed Computations." Communications of the ACM, 9(3).
    Maffeis, S., Mitchell, J.C. & Taly, A. (2010). "Object Capabilities
        and Isolation of Untrusted Web Applications." Proc. IEEE S&P.
"""

from __future__ import annotations

import pytest

from skillfortify.core.capabilities import (
    AccessLevel,
    Capability,
    CapabilitySet,
)


# ---------------------------------------------------------------------------
# TestCapability: The (resource, access) pair
# ---------------------------------------------------------------------------


class TestCapability:
    """Validate the Capability dataclass -- the (resource, access) pairing."""

    def test_create_capability(self) -> None:
        cap = Capability(resource="filesystem", access=AccessLevel.READ)
        assert cap.resource == "filesystem"
        assert cap.access == AccessLevel.READ

    def test_capability_is_frozen(self) -> None:
        """Capabilities are immutable to prevent TOCTOU attacks."""
        cap = Capability(resource="network", access=AccessLevel.WRITE)
        with pytest.raises(AttributeError):
            cap.resource = "filesystem"  # type: ignore[misc]

    def test_capability_is_hashable(self) -> None:
        """Required for use in sets and as dict keys."""
        cap = Capability(resource="filesystem", access=AccessLevel.READ)
        s = {cap}
        assert cap in s

    def test_subsumes_higher_access_covers_lower(self) -> None:
        """WRITE subsumes READ on the same resource."""
        write_fs = Capability(resource="filesystem", access=AccessLevel.WRITE)
        read_fs = Capability(resource="filesystem", access=AccessLevel.READ)
        assert write_fs.subsumes(read_fs)

    def test_subsumes_same_access(self) -> None:
        """A capability subsumes itself (reflexive)."""
        read_fs = Capability(resource="filesystem", access=AccessLevel.READ)
        assert read_fs.subsumes(read_fs)

    def test_subsumes_lower_does_not_cover_higher(self) -> None:
        """READ does NOT subsume WRITE."""
        read_fs = Capability(resource="filesystem", access=AccessLevel.READ)
        write_fs = Capability(resource="filesystem", access=AccessLevel.WRITE)
        assert not read_fs.subsumes(write_fs)

    def test_subsumes_same_resource_required(self) -> None:
        """fs:WRITE does NOT subsume net:READ -- different resources are incomparable."""
        fs_write = Capability(resource="filesystem", access=AccessLevel.WRITE)
        net_read = Capability(resource="network", access=AccessLevel.READ)
        assert not fs_write.subsumes(net_read)

    def test_subsumes_admin_covers_everything_on_same_resource(self) -> None:
        """ADMIN subsumes all lower levels on the same resource."""
        admin_fs = Capability(resource="filesystem", access=AccessLevel.ADMIN)
        for level in AccessLevel:
            lower = Capability(resource="filesystem", access=level)
            assert admin_fs.subsumes(lower)

    def test_subsumes_none_covers_only_none(self) -> None:
        """NONE only subsumes NONE."""
        none_fs = Capability(resource="filesystem", access=AccessLevel.NONE)
        assert none_fs.subsumes(Capability(resource="filesystem", access=AccessLevel.NONE))
        assert not none_fs.subsumes(Capability(resource="filesystem", access=AccessLevel.READ))

    def test_equality(self) -> None:
        c1 = Capability(resource="network", access=AccessLevel.WRITE)
        c2 = Capability(resource="network", access=AccessLevel.WRITE)
        assert c1 == c2

    def test_inequality_different_resource(self) -> None:
        c1 = Capability(resource="network", access=AccessLevel.WRITE)
        c2 = Capability(resource="filesystem", access=AccessLevel.WRITE)
        assert c1 != c2

    def test_inequality_different_access(self) -> None:
        c1 = Capability(resource="network", access=AccessLevel.READ)
        c2 = Capability(resource="network", access=AccessLevel.WRITE)
        assert c1 != c2

    def test_repr_is_readable(self) -> None:
        cap = Capability(resource="shell", access=AccessLevel.ADMIN)
        r = repr(cap)
        assert "shell" in r
        assert "ADMIN" in r


# ---------------------------------------------------------------------------
# TestCapabilitySet: Collection operations
# ---------------------------------------------------------------------------


class TestCapabilitySet:
    """Validate CapabilitySet -- a keyed collection enforcing least-privilege."""

    def test_empty_set(self) -> None:
        cs = CapabilitySet()
        assert len(cs) == 0

    def test_add_capability(self) -> None:
        cs = CapabilitySet()
        cs.add(Capability(resource="filesystem", access=AccessLevel.READ))
        assert len(cs) == 1

    def test_add_upserts_to_highest(self) -> None:
        """Adding a higher access level for the same resource replaces the lower."""
        cs = CapabilitySet()
        cs.add(Capability(resource="filesystem", access=AccessLevel.READ))
        cs.add(Capability(resource="filesystem", access=AccessLevel.WRITE))
        assert len(cs) == 1
        cap = next(iter(cs))
        assert cap.access == AccessLevel.WRITE

    def test_add_does_not_downgrade(self) -> None:
        """Adding a lower access level does not replace an existing higher one."""
        cs = CapabilitySet()
        cs.add(Capability(resource="filesystem", access=AccessLevel.WRITE))
        cs.add(Capability(resource="filesystem", access=AccessLevel.READ))
        cap = next(iter(cs))
        assert cap.access == AccessLevel.WRITE

    def test_from_list(self) -> None:
        caps = [
            Capability(resource="filesystem", access=AccessLevel.READ),
            Capability(resource="network", access=AccessLevel.WRITE),
        ]
        cs = CapabilitySet.from_list(caps)
        assert len(cs) == 2

    def test_from_list_deduplicates(self) -> None:
        """from_list with duplicates keeps the highest access per resource."""
        caps = [
            Capability(resource="filesystem", access=AccessLevel.READ),
            Capability(resource="filesystem", access=AccessLevel.ADMIN),
            Capability(resource="network", access=AccessLevel.WRITE),
        ]
        cs = CapabilitySet.from_list(caps)
        assert len(cs) == 2

    def test_permits_when_declared_covers_required(self) -> None:
        """Declared WRITE permits required READ."""
        declared = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.WRITE),
        ])
        required = Capability(resource="filesystem", access=AccessLevel.READ)
        assert declared.permits(required)

    def test_permits_exact_match(self) -> None:
        declared = CapabilitySet.from_list([
            Capability(resource="network", access=AccessLevel.READ),
        ])
        required = Capability(resource="network", access=AccessLevel.READ)
        assert declared.permits(required)

    def test_denies_excess(self) -> None:
        """Declared READ denies required WRITE."""
        declared = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        required = Capability(resource="filesystem", access=AccessLevel.WRITE)
        assert not declared.permits(required)

    def test_denies_unknown_resource(self) -> None:
        """A skill requesting access to an undeclared resource is denied."""
        declared = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.ADMIN),
        ])
        required = Capability(resource="network", access=AccessLevel.READ)
        assert not declared.permits(required)

    def test_is_subset_of(self) -> None:
        """A set with lower/equal access is a subset of a broader set."""
        smaller = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        bigger = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.WRITE),
            Capability(resource="network", access=AccessLevel.READ),
        ])
        assert smaller.is_subset_of(bigger)

    def test_not_subset_when_exceeds(self) -> None:
        """A set requiring higher access is NOT a subset."""
        requesting = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.ADMIN),
        ])
        allowed = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        assert not requesting.is_subset_of(allowed)

    def test_not_subset_when_extra_resource(self) -> None:
        """A set with capabilities for an undeclared resource is NOT a subset."""
        requesting = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
            Capability(resource="shell", access=AccessLevel.WRITE),
        ])
        allowed = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.ADMIN),
        ])
        assert not requesting.is_subset_of(allowed)

    def test_empty_is_subset_of_anything(self) -> None:
        """The empty set is a subset of every CapabilitySet."""
        empty = CapabilitySet()
        non_empty = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        assert empty.is_subset_of(non_empty)
        assert empty.is_subset_of(CapabilitySet())

    def test_violations_against_returns_excess(self) -> None:
        """violations_against lists capabilities that exceed the declared set."""
        observed = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
            Capability(resource="shell", access=AccessLevel.WRITE),
            Capability(resource="network", access=AccessLevel.ADMIN),
        ])
        declared = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.WRITE),
            Capability(resource="network", access=AccessLevel.READ),
        ])
        violations = observed.violations_against(declared)
        assert len(violations) == 2
        violation_resources = {v.resource for v in violations}
        assert "shell" in violation_resources
        assert "network" in violation_resources

    def test_violations_empty_when_compliant(self) -> None:
        """No violations when observed is a subset of declared."""
        observed = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        declared = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.ADMIN),
        ])
        violations = observed.violations_against(declared)
        assert len(violations) == 0

    def test_contains(self) -> None:
        cs = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        assert Capability(resource="filesystem", access=AccessLevel.READ) in cs

    def test_not_contains(self) -> None:
        cs = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
        ])
        assert Capability(resource="network", access=AccessLevel.READ) not in cs

    def test_iter(self) -> None:
        caps = [
            Capability(resource="filesystem", access=AccessLevel.READ),
            Capability(resource="network", access=AccessLevel.WRITE),
        ]
        cs = CapabilitySet.from_list(caps)
        iterated = list(cs)
        assert len(iterated) == 2

    def test_len(self) -> None:
        cs = CapabilitySet.from_list([
            Capability(resource="filesystem", access=AccessLevel.READ),
            Capability(resource="network", access=AccessLevel.WRITE),
            Capability(resource="shell", access=AccessLevel.ADMIN),
        ])
        assert len(cs) == 3
