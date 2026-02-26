"""Agent Dependency Graph (ADG) and SAT-Based Dependency Resolution.

This package implements the formal dependency graph data structure and a
SAT-based resolution engine for agent skill supply chains. All public names
are re-exported here for backward compatibility -- existing imports of the form
``from skillfortify.core.dependency import X`` continue to work unchanged.

Formal Definition
-----------------
An Agent Dependency Graph is a 5-tuple ADG = (S, V, D, C, Cap) where:

- **S** = set of skill names (strings)
- **V**: S -> 2^N = available versions per skill
- **D**: S x N -> 2^(S x Constraint) = dependency relation
- **C**: S x N -> 2^(S x Constraint) = conflict relation
- **Cap**: S x N -> 2^C = capability requirements
"""

# Re-export all public names for backward compatibility.
# Existing code using ``from skillfortify.core.dependency import X`` will continue
# to work without modification.

from skillfortify.core.dependency.constraints import (
    VersionConstraint,
    SkillDependency,
    SkillConflict,
    _parse_version_tuple,
    _version_key,
)
from skillfortify.core.dependency.graph import (
    SkillNode,
    AgentDependencyGraph,
)
from skillfortify.core.dependency.resolver import (
    Resolution,
    DependencyResolver,
)

__all__ = [
    "VersionConstraint",
    "SkillDependency",
    "SkillConflict",
    "SkillNode",
    "AgentDependencyGraph",
    "Resolution",
    "DependencyResolver",
    "_parse_version_tuple",
    "_version_key",
]
