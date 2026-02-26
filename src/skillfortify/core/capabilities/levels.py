"""Access levels and capability universe for the formal capability lattice.

This module defines the four-element access level lattice
L_cap = ({NONE, READ, WRITE, ADMIN}, sqsubseteq) and the set of known
resource types (CAPABILITY_UNIVERSE) in the agent skill ecosystem.

Lattice Structure
-----------------
The access level lattice is a four-element chain (total order):

    NONE  sqsubseteq  READ  sqsubseteq  WRITE  sqsubseteq  ADMIN

Since this is a total order, the lattice operations reduce to:
- **join(a, b) = max(a, b)**: least upper bound
- **meet(a, b) = min(a, b)**: greatest lower bound
- **bottom = NONE**: least element (no access)
- **top = ADMIN**: greatest element (full access)

Resource Types
--------------
``CAPABILITY_UNIVERSE`` enumerates the eight known resource types derived
from empirical analysis of 42,447 skills [ASW26]_ and the MalTool
benchmark of 6,487 malicious tools [MT26]_.

References
----------
.. [DV66] Dennis, J.B. & Van Horn, E.C. (1966). "Programming Semantics for
   Multiprogrammed Computations." Communications of the ACM, 9(3), 143-155.

.. [Mil06] Miller, M.S. (2006). "Robust Composition: Towards a Unified
   Approach to Access Control and Concurrency Control." PhD Thesis,
   Johns Hopkins University.

.. [ASW26] "Agent Skills in the Wild" (arXiv:2601.10338, Jan 2026).

.. [MT26] "MalTool: Benchmarking Malicious Tool Attacks Against LLM Agents"
   (arXiv:2602.12194, Feb 12, 2026).
"""

from __future__ import annotations

from enum import IntEnum


# ---------------------------------------------------------------------------
# CAPABILITY_UNIVERSE: The set of known resource types
# ---------------------------------------------------------------------------

CAPABILITY_UNIVERSE: frozenset[str] = frozenset({
    "filesystem",
    "network",
    "environment",
    "shell",
    "skill_invoke",
    "clipboard",
    "browser",
    "database",
})
"""Known resource types in the agent skill ecosystem.

Derived from empirical analysis of real-world agent skill registries:
- **filesystem**: Local file read/write operations.
- **network**: HTTP requests, socket connections, DNS lookups.
- **environment**: Environment variable access (often contains secrets).
- **shell**: System command execution (highest-risk category).
- **skill_invoke**: Ability to invoke other skills (transitive authority).
- **clipboard**: System clipboard access (potential data exfiltration).
- **browser**: Browser automation and web scraping capabilities.
- **database**: Direct database connections and queries.
"""


# ---------------------------------------------------------------------------
# AccessLevel: The four-element linear order
# ---------------------------------------------------------------------------


class AccessLevel(IntEnum):
    """Four-element access level lattice: NONE < READ < WRITE < ADMIN.

    This forms a total order (chain), so the lattice operations join and meet
    reduce to max and min respectively. The integer encoding (0-3) enables
    direct comparison via standard relational operators.

    The access levels model the standard capability escalation path:
    - **NONE** (0): No access to the resource. The bottom element.
    - **READ** (1): Read-only access. Can observe but not modify.
    - **WRITE** (2): Read and write access. Can modify the resource.
    - **ADMIN** (3): Full administrative access. The top element. Includes
      the ability to grant/revoke access for other principals.

    Lattice operations (class methods):
    - ``join(a, b)``: Least upper bound = max(a, b).
    - ``meet(a, b)``: Greatest lower bound = min(a, b).
    - ``bottom()``: Returns NONE.
    - ``top()``: Returns ADMIN.
    """

    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3

    @classmethod
    def join(cls, a: AccessLevel, b: AccessLevel) -> AccessLevel:
        """Compute the least upper bound (join) of two access levels.

        On a total order, join is simply the maximum. This operation is:
        - Commutative: join(a, b) == join(b, a)
        - Associative: join(join(a, b), c) == join(a, join(b, c))
        - Idempotent: join(a, a) == a
        - Identity element: join(a, NONE) == a

        Args:
            a: First access level.
            b: Second access level.

        Returns:
            The higher of the two access levels.
        """
        return cls(max(a.value, b.value))

    @classmethod
    def meet(cls, a: AccessLevel, b: AccessLevel) -> AccessLevel:
        """Compute the greatest lower bound (meet) of two access levels.

        On a total order, meet is simply the minimum. This operation is:
        - Commutative: meet(a, b) == meet(b, a)
        - Associative: meet(meet(a, b), c) == meet(a, meet(b, c))
        - Idempotent: meet(a, a) == a
        - Identity element: meet(a, ADMIN) == a

        Args:
            a: First access level.
            b: Second access level.

        Returns:
            The lower of the two access levels.
        """
        return cls(min(a.value, b.value))

    @classmethod
    def bottom(cls) -> AccessLevel:
        """Return the bottom element (NONE) -- the least element.

        bottom is the identity element for join: join(a, bottom) == a.
        bottom is the absorbing element for meet: meet(a, bottom) == bottom.
        """
        return cls.NONE

    @classmethod
    def top(cls) -> AccessLevel:
        """Return the top element (ADMIN) -- the greatest element.

        top is the identity element for meet: meet(a, top) == a.
        top is the absorbing element for join: join(a, top) == top.
        """
        return cls.ADMIN
