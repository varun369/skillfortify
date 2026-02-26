"""Formal Capability Lattice for Agent Skill Supply Chain Security.

This package implements the capability lattice L_cap = ({NONE, READ, WRITE,
ADMIN}, sqsubseteq) that forms the abstract domain for SkillShield's static
analysis of agent skill permissions.

Submodules
----------
- ``levels``: AccessLevel IntEnum, CAPABILITY_UNIVERSE frozenset.
- ``models``: Capability dataclass, CapabilitySet collection.

All public names are re-exported here for backward compatibility::

    from skillfortify.core.capabilities import AccessLevel, Capability, CapabilitySet
    from skillfortify.core.capabilities import CAPABILITY_UNIVERSE
"""

from skillfortify.core.capabilities.levels import CAPABILITY_UNIVERSE, AccessLevel
from skillfortify.core.capabilities.models import Capability, CapabilitySet

__all__ = [
    "AccessLevel",
    "CAPABILITY_UNIVERSE",
    "Capability",
    "CapabilitySet",
]
