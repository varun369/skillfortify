"""Version constraints, dependency edges, and conflict edges for the ADG.

This module provides the foundational data types for declaring version
requirements and inter-skill relationships in the Agent Dependency Graph.

Constraint semantics follow PEP 440 / SemVer conventions with support for
exact match (``==``), range (``>=``, ``<=``, ``>``, ``<``), not-equal
(``!=``), caret (``^``), tilde (``~``), wildcard (``*``), and compound
comma-separated constraints.

References
----------
.. [SemVer] Preston-Werner, T. (2013). "Semantic Versioning 2.0.0."
   https://semver.org/
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Version comparison utilities
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z\-.]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z\-.]+))?$"
)


def _parse_version_tuple(version: str) -> tuple[int, int, int]:
    """Parse a semantic version string into a comparable (major, minor, patch) tuple.

    Pre-release and build metadata are stripped for ordering purposes, following
    SemVer 2.0.0 precedence rules (section 11): build metadata does not affect
    precedence and pre-release versions have lower precedence than the associated
    normal version.

    Args:
        version: Semantic version string (e.g., "1.2.3", "0.1.0-alpha").

    Returns:
        A (major, minor, patch) integer tuple.

    Raises:
        ValueError: If the string does not match semantic version format.
    """
    m = _SEMVER_RE.match(version.strip())
    if not m:
        raise ValueError(f"Invalid semantic version: {version!r}")
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def _version_key(version: str) -> tuple[int, int, int]:
    """Sort key for version strings -- highest version first (descending)."""
    return _parse_version_tuple(version)


# ---------------------------------------------------------------------------
# VersionConstraint: Declarative version requirement
# ---------------------------------------------------------------------------

# Regex to tokenize a single constraint atom like ">=1.2.3" or "==0.1.0"
_CONSTRAINT_ATOM_RE = re.compile(
    r"^\s*(?P<op>==|!=|>=|<=|>|<|\^|~)\s*"
    r"(?P<ver>(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z\-.]+)?(?:\+[0-9A-Za-z\-.]+)?)\s*$"
)


@dataclass(frozen=True)
class VersionConstraint:
    """A version constraint specification, analogous to npm/pip constraint syntax.

    Supports:
    - Exact match: ``==1.0.0``
    - Not-equal: ``!=1.0.0``
    - Minimum (inclusive): ``>=1.0.0``
    - Maximum (inclusive): ``<=2.0.0``
    - Minimum (exclusive): ``>1.0.0``
    - Maximum (exclusive): ``<2.0.0``
    - Wildcard (any version): ``*``
    - Compound (comma-separated, all must hold): ``>=1.0.0,<2.0.0``

    The constraint semantics follow PEP 440 / SemVer conventions.

    Attributes:
        raw: The raw constraint string as authored (e.g., ">=1.0.0,<2.0.0").
    """

    raw: str

    def satisfies(self, version: str) -> bool:
        """Check whether a version string satisfies this constraint.

        For compound constraints (comma-separated), ALL atoms must be satisfied
        (conjunction semantics).

        Args:
            version: A semantic version string (e.g., "1.2.3").

        Returns:
            True if the version satisfies every atom in this constraint.

        Raises:
            ValueError: If *version* is not a valid semantic version.
        """
        stripped = self.raw.strip()
        if stripped == "*":
            return True

        ver_tuple = _parse_version_tuple(version)

        # Split compound constraints on comma
        atoms = [a.strip() for a in stripped.split(",") if a.strip()]
        for atom in atoms:
            if not self._atom_satisfies(atom, ver_tuple):
                return False
        return True

    @staticmethod
    def _atom_satisfies(atom: str, ver_tuple: tuple[int, int, int]) -> bool:
        """Evaluate a single constraint atom against a parsed version tuple."""
        m = _CONSTRAINT_ATOM_RE.match(atom)
        if not m:
            raise ValueError(f"Invalid constraint atom: {atom!r}")

        op = m.group("op")
        target = _parse_version_tuple(m.group("ver"))

        if op == "==":
            return ver_tuple == target
        elif op == "!=":
            return ver_tuple != target
        elif op == ">=":
            return ver_tuple >= target
        elif op == "<=":
            return ver_tuple <= target
        elif op == ">":
            return ver_tuple > target
        elif op == "<":
            return ver_tuple < target
        elif op == "^":
            # Caret: compatible with (same major, >= target). If major is 0,
            # same major.minor and >= target.
            if target[0] == 0:
                return (
                    ver_tuple[0] == target[0]
                    and ver_tuple[1] == target[1]
                    and ver_tuple >= target
                )
            return ver_tuple[0] == target[0] and ver_tuple >= target
        elif op == "~":
            # Tilde: same major.minor, patch >= target patch.
            return (
                ver_tuple[0] == target[0]
                and ver_tuple[1] == target[1]
                and ver_tuple >= target
            )
        else:  # pragma: no cover
            raise ValueError(f"Unknown operator: {op!r}")

    def __repr__(self) -> str:
        return f"VersionConstraint({self.raw!r})"


# ---------------------------------------------------------------------------
# SkillDependency & SkillConflict: Edge types in the ADG
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillDependency:
    """A directed dependency edge from one skill-version to another skill.

    Represents: "installing skill X at version V *requires* that skill
    ``skill_name`` is also installed at some version satisfying ``constraint``."

    In the SAT encoding, this becomes an implication clause:
        x_{X,V} -> OR_{w satisfies constraint} x_{skill_name, w}

    Attributes:
        skill_name: The name of the required dependency skill.
        constraint: Version constraint that the dependency must satisfy.
    """

    skill_name: str
    constraint: VersionConstraint


@dataclass(frozen=True)
class SkillConflict:
    """A conflict declaration between two skills.

    Represents: "skill X at version V is *incompatible* with any version of
    ``skill_name`` that satisfies ``constraint``."

    In the SAT encoding, this becomes mutual exclusion clauses:
        ~x_{X,V} OR ~x_{skill_name, w}  for each w satisfying constraint

    Attributes:
        skill_name: The name of the conflicting skill.
        constraint: Version constraint identifying conflicting versions.
    """

    skill_name: str
    constraint: VersionConstraint
