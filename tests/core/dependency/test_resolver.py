"""Tests for SAT encoding correctness, dependency resolution, conflict handling,
capability-bounded resolution, and edge cases.

Validates that the SAT-based dependency resolver (Theorem 4: Resolution Soundness)
correctly encodes constraints and finds satisfying assignments or reports failures.
"""

from __future__ import annotations

import pytest

from skillfortify.core.dependency import (
    AgentDependencyGraph,
    DependencyResolver,
    SkillConflict,
    SkillDependency,
    SkillNode,
    VersionConstraint,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_node(
    name: str,
    version: str,
    deps: list[tuple[str, str]] | None = None,
    conflicts: list[tuple[str, str]] | None = None,
    capabilities: set[str] | None = None,
) -> SkillNode:
    """Convenience factory for SkillNode instances."""
    return SkillNode(
        name=name,
        version=version,
        dependencies=[
            SkillDependency(skill_name=d[0], constraint=VersionConstraint(d[1]))
            for d in (deps or [])
        ],
        conflicts=[
            SkillConflict(skill_name=c[0], constraint=VersionConstraint(c[1]))
            for c in (conflicts or [])
        ],
        capabilities=capabilities or set(),
    )


def _build_simple_chain() -> AgentDependencyGraph:
    """Build A@1.0.0 -> B@1.0.0 -> C@1.0.0 (linear dependency chain)."""
    g = AgentDependencyGraph()
    g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
    g.add_skill(_make_node("B", "1.0.0", deps=[("C", ">=1.0.0")]))
    g.add_skill(_make_node("C", "1.0.0"))
    return g


def _build_diamond() -> AgentDependencyGraph:
    """Build a diamond dependency: A -> B, A -> C, B -> D, C -> D."""
    g = AgentDependencyGraph()
    g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0"), ("C", ">=1.0.0")]))
    g.add_skill(_make_node("B", "1.0.0", deps=[("D", ">=1.0.0")]))
    g.add_skill(_make_node("C", "1.0.0", deps=[("D", ">=1.0.0")]))
    g.add_skill(_make_node("D", "1.0.0"))
    return g


# ===========================================================================
# SAT Encoding Correctness
# ===========================================================================


class TestSATEncoding:
    """Tests that the SAT encoding captures the correct constraints."""

    def test_single_skill_encoding(self) -> None:
        """A single skill with no deps/conflicts yields satisfiable encoding."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0"))
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint(">=1.0.0")})
        clauses, var_map, inv_map = resolver._encode_sat()
        # Should have a requirement clause: [var_A_1.0.0]
        assert len(var_map) == 1
        assert (clauses is not None)

    def test_at_most_one_version_clauses(self) -> None:
        """Two versions of same skill produce pairwise exclusion clauses."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0"))
        g.add_skill(_make_node("A", "2.0.0"))
        resolver = DependencyResolver(g)
        clauses, var_map, inv_map = resolver._encode_sat()

        v1 = var_map[("A", "1.0.0")]
        v2 = var_map[("A", "2.0.0")]
        # There must be a clause [-v1, -v2] (at-most-one)
        assert [-v1, -v2] in clauses or [-v2, -v1] in clauses

    def test_dependency_implication_clause(self) -> None:
        """A dependency creates an implication clause in the encoding."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))
        resolver = DependencyResolver(g)
        clauses, var_map, _ = resolver._encode_sat()

        va = var_map[("A", "1.0.0")]
        vb = var_map[("B", "1.0.0")]
        # Should contain implication: [-va, vb]
        assert [-va, vb] in clauses

    def test_conflict_exclusion_clause(self) -> None:
        """A conflict creates a mutual exclusion clause."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", conflicts=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))
        resolver = DependencyResolver(g)
        clauses, var_map, _ = resolver._encode_sat()

        va = var_map[("A", "1.0.0")]
        vb = var_map[("B", "1.0.0")]
        # Should contain exclusion: [-va, -vb]
        assert [-va, -vb] in clauses

    def test_unsatisfiable_dependency_excludes_node(self) -> None:
        """If a dependency cannot be satisfied, the parent is excluded."""
        g = AgentDependencyGraph()
        # A depends on B>=2.0.0 but only B@1.0.0 exists
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=2.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))
        resolver = DependencyResolver(g)
        clauses, var_map, _ = resolver._encode_sat()

        va = var_map[("A", "1.0.0")]
        # A must be excluded: unit clause [-va]
        assert [-va] in clauses

    def test_capability_exclusion_clause(self) -> None:
        """Capability-bounded resolution excludes disallowed skill-versions."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", capabilities={"shell:WRITE"}))
        g.add_skill(_make_node("B", "1.0.0", capabilities={"network:READ"}))
        resolver = DependencyResolver(
            g, allowed_capabilities={"network:READ"}  # shell:WRITE not allowed
        )
        clauses, var_map, _ = resolver._encode_sat()

        va = var_map[("A", "1.0.0")]
        vb = var_map[("B", "1.0.0")]
        # A should be excluded (shell:WRITE not in allowed)
        assert [-va] in clauses
        # B should NOT be excluded
        assert [-vb] not in clauses


# ===========================================================================
# Resolution with Simple Dependencies
# ===========================================================================


class TestSimpleResolution:
    """Tests for SAT-based resolution with straightforward dependencies."""

    def test_resolve_single_skill(self) -> None:
        """Resolving a single skill with no dependencies succeeds."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0"))
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint(">=1.0.0")})
        result = resolver.resolve()
        assert result.success is True
        assert result.installed == {"A": "1.0.0"}

    def test_resolve_linear_chain(self) -> None:
        """A -> B -> C chain resolves with all three installed."""
        g = _build_simple_chain()
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint(">=1.0.0")})
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["A"] == "1.0.0"
        assert result.installed["B"] == "1.0.0"
        assert result.installed["C"] == "1.0.0"

    def test_resolve_picks_satisfying_version(self) -> None:
        """Resolver picks a version that satisfies the dependency constraint."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=2.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))
        g.add_skill(_make_node("B", "2.0.0"))
        g.add_skill(_make_node("B", "3.0.0"))
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint("==1.0.0")})
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["A"] == "1.0.0"
        # B must be >= 2.0.0
        assert result.installed["B"] in ("2.0.0", "3.0.0")

    def test_resolve_diamond_dependency(self) -> None:
        """Diamond dependency A -> B, A -> C, B -> D, C -> D resolves correctly."""
        g = _build_diamond()
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint(">=1.0.0")})
        result = resolver.resolve()
        assert result.success is True
        assert "A" in result.installed
        assert "B" in result.installed
        assert "C" in result.installed
        assert "D" in result.installed

    def test_resolve_multiple_root_requirements(self) -> None:
        """Multiple independent root requirements are resolved together."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("X", "1.0.0"))
        g.add_skill(_make_node("Y", "2.0.0"))
        resolver = DependencyResolver(
            g,
            requirements={
                "X": VersionConstraint(">=1.0.0"),
                "Y": VersionConstraint(">=2.0.0"),
            },
        )
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["X"] == "1.0.0"
        assert result.installed["Y"] == "2.0.0"

    def test_resolve_prefers_only_satisfying(self) -> None:
        """If only one version satisfies, that version is installed."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0"))
        g.add_skill(_make_node("A", "2.0.0"))
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint("==2.0.0")})
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["A"] == "2.0.0"


# ===========================================================================
# Resolution with Conflicts
# ===========================================================================


class TestConflictResolution:
    """Tests for resolution when skills declare conflicts."""

    def test_direct_conflict_no_requirement(self) -> None:
        """Two conflicting skills without requirements can both be excluded."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", conflicts=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))
        # No requirements: solver can leave both uninstalled
        resolver = DependencyResolver(g)
        result = resolver.resolve()
        assert result.success is True
        # Shouldn't install both
        if "A" in result.installed and "B" in result.installed:
            pytest.fail("Both conflicting skills were installed")

    def test_conflict_prevents_co_installation(self) -> None:
        """Requiring two mutually conflicting skills fails."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", conflicts=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0", conflicts=[("A", ">=1.0.0")]))
        resolver = DependencyResolver(
            g,
            requirements={
                "A": VersionConstraint(">=1.0.0"),
                "B": VersionConstraint(">=1.0.0"),
            },
        )
        result = resolver.resolve()
        assert result.success is False
        assert len(result.conflicts) > 0

    def test_conflict_with_version_range(self) -> None:
        """Conflict only applies to matching versions; non-matching is ok."""
        g = AgentDependencyGraph()
        # A conflicts with B >=2.0.0 only
        g.add_skill(_make_node("A", "1.0.0", conflicts=[("B", ">=2.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))  # not conflicting
        g.add_skill(_make_node("B", "2.0.0"))  # conflicting
        resolver = DependencyResolver(
            g,
            requirements={
                "A": VersionConstraint(">=1.0.0"),
                "B": VersionConstraint(">=1.0.0"),
            },
        )
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["A"] == "1.0.0"
        assert result.installed["B"] == "1.0.0"  # must pick non-conflicting version

    def test_transitive_conflict(self) -> None:
        """A requires B, B conflicts with C, so requiring A+C may fail."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0", conflicts=[("C", ">=1.0.0")]))
        g.add_skill(_make_node("C", "1.0.0"))
        resolver = DependencyResolver(
            g,
            requirements={
                "A": VersionConstraint(">=1.0.0"),
                "C": VersionConstraint(">=1.0.0"),
            },
        )
        result = resolver.resolve()
        # B@1.0.0 conflicts with C@1.0.0, and A requires B, so this is UNSAT
        assert result.success is False


# ===========================================================================
# Capability-Bounded Resolution
# ===========================================================================


class TestCapabilityBoundedResolution:
    """Tests for resolution with capability constraints (POLA at install time)."""

    def test_allowed_capabilities_permits_installation(self) -> None:
        """Skill within allowed capabilities can be installed."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("safe", "1.0.0", capabilities={"network:READ"}))
        resolver = DependencyResolver(
            g,
            allowed_capabilities={"network:READ", "filesystem:READ"},
            requirements={"safe": VersionConstraint(">=1.0.0")},
        )
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["safe"] == "1.0.0"

    def test_disallowed_capabilities_blocks_installation(self) -> None:
        """Skill requiring disallowed capabilities cannot be installed."""
        g = AgentDependencyGraph()
        g.add_skill(
            _make_node("dangerous", "1.0.0", capabilities={"shell:WRITE", "network:READ"})
        )
        resolver = DependencyResolver(
            g,
            allowed_capabilities={"network:READ"},  # shell:WRITE not allowed
            requirements={"dangerous": VersionConstraint(">=1.0.0")},
        )
        result = resolver.resolve()
        assert result.success is False

    def test_capability_filtering_picks_safe_version(self) -> None:
        """When one version is safe and another is not, resolver picks the safe one."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("tool", "1.0.0", capabilities={"network:READ"}))
        g.add_skill(_make_node("tool", "2.0.0", capabilities={"shell:WRITE"}))
        resolver = DependencyResolver(
            g,
            allowed_capabilities={"network:READ"},
            requirements={"tool": VersionConstraint(">=1.0.0")},
        )
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["tool"] == "1.0.0"

    def test_no_capability_filter_allows_all(self) -> None:
        """Without capability filter, all skill-versions are candidates."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("tool", "1.0.0", capabilities={"shell:ADMIN"}))
        resolver = DependencyResolver(
            g,
            requirements={"tool": VersionConstraint(">=1.0.0")},
        )
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["tool"] == "1.0.0"
