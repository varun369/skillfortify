"""Tests for ADG construction, cycle detection, and transitive dependency computation.

Validates SkillNode creation, AgentDependencyGraph construction, version querying,
circular dependency detection via DFS coloring, and BFS-based transitive
dependency computation.
"""

from __future__ import annotations

from skillfortify.core.dependency import (
    AgentDependencyGraph,
    SkillConflict,
    SkillDependency,
    SkillNode,
    VersionConstraint,
)


# ===========================================================================
# Helpers: Build common graph topologies for test reuse
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
# ADG Construction
# ===========================================================================


class TestADGConstruction:
    """Tests for SkillNode creation and AgentDependencyGraph construction."""

    def test_add_single_skill(self) -> None:
        """Adding a single skill creates one node in the graph."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("weather", "1.0.0"))
        assert g.node_count == 1
        assert g.skills == {"weather"}

    def test_add_multiple_versions(self) -> None:
        """Same skill name with different versions creates multiple nodes."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("weather", "1.0.0"))
        g.add_skill(_make_node("weather", "1.1.0"))
        g.add_skill(_make_node("weather", "2.0.0"))
        assert g.node_count == 3
        assert g.skills == {"weather"}

    def test_get_versions_sorted_descending(self) -> None:
        """get_versions returns versions sorted newest-first (descending)."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("lib", "0.1.0"))
        g.add_skill(_make_node("lib", "1.0.0"))
        g.add_skill(_make_node("lib", "0.9.5"))
        assert g.get_versions("lib") == ["1.0.0", "0.9.5", "0.1.0"]

    def test_get_versions_unknown_skill(self) -> None:
        """get_versions returns empty list for unknown skills."""
        g = AgentDependencyGraph()
        assert g.get_versions("nonexistent") == []

    def test_get_node_found(self) -> None:
        """get_node returns the node for a known (name, version)."""
        g = AgentDependencyGraph()
        node = _make_node("auth", "2.0.0", capabilities={"network:READ"})
        g.add_skill(node)
        result = g.get_node("auth", "2.0.0")
        assert result is node

    def test_get_node_not_found(self) -> None:
        """get_node returns None for unknown nodes."""
        g = AgentDependencyGraph()
        assert g.get_node("ghost", "1.0.0") is None

    def test_replace_existing_node(self) -> None:
        """Adding a node with the same (name, version) replaces the existing one."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("lib", "1.0.0", capabilities={"network:READ"}))
        g.add_skill(_make_node("lib", "1.0.0", capabilities={"shell:WRITE"}))
        node = g.get_node("lib", "1.0.0")
        assert node is not None
        assert node.capabilities == {"shell:WRITE"}
        assert g.node_count == 1

    def test_get_dependencies(self) -> None:
        """get_dependencies returns the dependency list for a skill-version."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("app", "1.0.0", deps=[("db", ">=2.0.0"), ("cache", ">=1.0.0")]))
        deps = g.get_dependencies("app", "1.0.0")
        assert len(deps) == 2
        assert deps[0].skill_name == "db"
        assert deps[1].skill_name == "cache"

    def test_get_conflicts(self) -> None:
        """get_conflicts returns the conflict list for a skill-version."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("X", "1.0.0", conflicts=[("Y", ">=2.0.0")]))
        conflicts = g.get_conflicts("X", "1.0.0")
        assert len(conflicts) == 1
        assert conflicts[0].skill_name == "Y"


# ===========================================================================
# Cycle Detection
# ===========================================================================


class TestCycleDetection:
    """Tests for circular dependency detection in the ADG."""

    def test_no_cycles_in_linear_chain(self) -> None:
        """A linear chain A -> B -> C has no cycles."""
        g = _build_simple_chain()
        cycles = g.detect_cycles()
        assert cycles == []

    def test_direct_cycle_detected(self) -> None:
        """A direct cycle A -> B -> A is detected."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0", deps=[("A", ">=1.0.0")]))
        cycles = g.detect_cycles()
        assert len(cycles) >= 1
        # Check that both A and B appear in some cycle
        flat = [name for cycle in cycles for name in cycle]
        assert "A" in flat
        assert "B" in flat

    def test_three_node_cycle(self) -> None:
        """A -> B -> C -> A forms a cycle."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0", deps=[("C", ">=1.0.0")]))
        g.add_skill(_make_node("C", "1.0.0", deps=[("A", ">=1.0.0")]))
        cycles = g.detect_cycles()
        assert len(cycles) >= 1

    def test_diamond_no_cycle(self) -> None:
        """A diamond A -> B, A -> C, B -> D, C -> D has no cycles."""
        g = _build_diamond()
        cycles = g.detect_cycles()
        assert cycles == []


# ===========================================================================
# Transitive Dependency Computation
# ===========================================================================


class TestTransitiveDependencies:
    """Tests for transitive_dependencies() BFS computation."""

    def test_linear_chain_transitive(self) -> None:
        """A -> B -> C: transitive deps of A include B and C."""
        g = _build_simple_chain()
        trans = g.transitive_dependencies("A", "1.0.0")
        assert ("B", "1.0.0") in trans
        assert ("C", "1.0.0") in trans

    def test_leaf_node_no_transitive(self) -> None:
        """Leaf node C has no transitive dependencies."""
        g = _build_simple_chain()
        trans = g.transitive_dependencies("C", "1.0.0")
        assert trans == set()

    def test_diamond_transitive(self) -> None:
        """Diamond: A's transitive deps include B, C, and D."""
        g = _build_diamond()
        trans = g.transitive_dependencies("A", "1.0.0")
        assert ("B", "1.0.0") in trans
        assert ("C", "1.0.0") in trans
        assert ("D", "1.0.0") in trans

    def test_unknown_node_returns_empty(self) -> None:
        """Transitive deps of unknown node is empty."""
        g = AgentDependencyGraph()
        trans = g.transitive_dependencies("ghost", "1.0.0")
        assert trans == set()

    def test_selects_highest_satisfying_version(self) -> None:
        """Transitive computation picks highest satisfying version."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
        g.add_skill(_make_node("B", "1.0.0"))
        g.add_skill(_make_node("B", "2.0.0"))
        g.add_skill(_make_node("B", "3.0.0"))
        trans = g.transitive_dependencies("A", "1.0.0")
        # Should pick B@3.0.0 (highest satisfying >=1.0.0)
        assert ("B", "3.0.0") in trans
        assert ("B", "1.0.0") not in trans
        assert ("B", "2.0.0") not in trans
