"""Capability and CapabilitySet models for agent skill security analysis.

This module implements the Dennis & Van Horn (1966) capability concept as
an immutable (resource, access) dataclass, and a keyed collection
(CapabilitySet) that enforces least-privilege semantics.

Capability Model Foundations
----------------------------
A capability is an unforgeable reference coupling a *resource designation*
with an *access right*. Miller (2006) extended this to the object-capability
(ocap) model, establishing that capability-safe languages can enforce the
*Principle of Least Authority* (POLA). The ``CapabilitySet.permits()``
method enforces POLA by checking that observed capabilities never exceed
declared capabilities.

Maffeis, Mitchell & Taly (2010) proved the *capability safety theorem*:
in a capability-safe language, untrusted code is confined to the authority
explicitly passed to it. Our ``CapabilitySet.is_subset_of()`` implements
the formal verification of this confinement property.

References
----------
.. [DV66] Dennis, J.B. & Van Horn, E.C. (1966). "Programming Semantics for
   Multiprogrammed Computations." Communications of the ACM, 9(3), 143-155.

.. [Mil06] Miller, M.S. (2006). "Robust Composition: Towards a Unified
   Approach to Access Control and Concurrency Control." PhD Thesis,
   Johns Hopkins University.

.. [MMT10] Maffeis, S., Mitchell, J.C. & Taly, A. (2010). "Object
   Capabilities and Isolation of Untrusted Web Applications."
   Proc. IEEE S&P, 125-140.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from skillfortify.core.capabilities.levels import AccessLevel


# ---------------------------------------------------------------------------
# Capability: The (resource, access) pair -- Dennis & Van Horn (1966)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Capability:
    """An immutable (resource, access) pair representing a single capability.

    This directly implements the Dennis & Van Horn (1966) capability concept:
    a protected, unforgeable reference that couples a resource designation
    with an access right. The ``frozen=True`` constraint ensures immutability,
    preventing TOCTOU attacks where a capability is modified between
    verification and use.

    Attributes:
        resource: The resource type this capability grants access to.
            Should be one of the values in ``CAPABILITY_UNIVERSE``.
        access: The access level granted on the resource.

    Examples:
        >>> fs_read = Capability(resource="filesystem", access=AccessLevel.READ)
        >>> net_write = Capability(resource="network", access=AccessLevel.WRITE)
        >>> fs_read.subsumes(Capability("filesystem", AccessLevel.NONE))
        True
    """

    resource: str
    access: AccessLevel

    def subsumes(self, other: Capability) -> bool:
        """Check if this capability subsumes (covers) another capability.

        C1 = (r1, a1) subsumes C2 = (r2, a2) iff r1 == r2 and a1 >= a2.
        Capabilities on different resources are incomparable.

        Args:
            other: The capability to check against.

        Returns:
            True if this capability covers the other capability.
        """
        return self.resource == other.resource and self.access >= other.access

    def __repr__(self) -> str:
        return f"Capability(resource={self.resource!r}, access=AccessLevel.{self.access.name})"


# ---------------------------------------------------------------------------
# CapabilitySet: Collection of capabilities keyed by resource
# ---------------------------------------------------------------------------


class CapabilitySet:
    """A set of capabilities keyed by resource, enforcing least-privilege.

    Stores at most one ``Capability`` per resource, always keeping the
    *highest* access level observed (the lattice join). This models the
    principle that a skill's effective capability on a resource is the
    maximum of all individual grants for that resource.

    Primary verification operations:
    1. **permits(required)**: Checks if a required capability is covered.
    2. **is_subset_of(other)**: Formal POLA check.
    3. **violations_against(declared)**: Lists capabilities exceeding bounds.

    Examples:
        >>> declared = CapabilitySet.from_list([
        ...     Capability("filesystem", AccessLevel.WRITE),
        ...     Capability("network", AccessLevel.READ),
        ... ])
        >>> declared.permits(Capability("filesystem", AccessLevel.READ))
        True
        >>> declared.permits(Capability("shell", AccessLevel.WRITE))
        False
    """

    def __init__(self) -> None:
        self._caps: dict[str, Capability] = {}

    @classmethod
    def from_list(cls, caps: list[Capability]) -> CapabilitySet:
        """Create a CapabilitySet from a list of capabilities.

        If multiple capabilities reference the same resource, the highest
        access level is kept (lattice join semantics).

        Args:
            caps: List of capabilities.

        Returns:
            A new CapabilitySet with deduplicated capabilities.
        """
        cs = cls()
        for cap in caps:
            cs.add(cap)
        return cs

    def add(self, cap: Capability) -> None:
        """Add a capability, keeping the highest access level per resource.

        Args:
            cap: The capability to add or merge.
        """
        existing = self._caps.get(cap.resource)
        if existing is None or cap.access > existing.access:
            self._caps[cap.resource] = cap

    def permits(self, required: Capability) -> bool:
        """Check if this capability set permits a required capability.

        Args:
            required: The capability being requested/observed.

        Returns:
            True if the required capability is covered by this set.
        """
        declared = self._caps.get(required.resource)
        if declared is None:
            return False
        return declared.subsumes(required)

    def is_subset_of(self, other: CapabilitySet) -> bool:
        """Check if every capability in this set is permitted by another.

        Formally: self <= other iff for all (r, a) in self,
        other.permits((r, a)).

        Args:
            other: The reference (declared) capability set.

        Returns:
            True if this set is a subset of the other set.
        """
        for cap in self._caps.values():
            if not other.permits(cap):
                return False
        return True

    def violations_against(self, declared: CapabilitySet) -> list[Capability]:
        """Return capabilities in this set that exceed the declared set.

        Args:
            declared: The reference (declared) capability set.

        Returns:
            List of violating capabilities. Empty means compliant.
        """
        violations: list[Capability] = []
        for cap in self._caps.values():
            if not declared.permits(cap):
                violations.append(cap)
        return violations

    def __len__(self) -> int:
        """Return the number of distinct resources in this capability set."""
        return len(self._caps)

    def __iter__(self) -> Iterator[Capability]:
        """Iterate over the capabilities in this set."""
        return iter(self._caps.values())

    def __contains__(self, item: object) -> bool:
        """Check if an exact capability is in this set (not subsumption)."""
        if not isinstance(item, Capability):
            return False
        stored = self._caps.get(item.resource)
        return stored is not None and stored == item

    def __repr__(self) -> str:
        caps_str = ", ".join(repr(c) for c in self._caps.values())
        return f"CapabilitySet([{caps_str}])"
