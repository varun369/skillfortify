"""Tests for edge cases and boundary conditions in the dependency module.

Validates empty graphs, single-skill scenarios, missing dependencies, unsatisfiable
constraints, dataclass defaults, and other unusual graph configurations.
"""

from __future__ import annotations

from skillfortify.core.dependency import (
    AgentDependencyGraph,
    DependencyResolver,
    Resolution,
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


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Tests for boundary conditions and unusual graph configurations."""

    def test_empty_graph_resolution(self) -> None:
        """Resolving an empty graph succeeds with empty installation."""
        g = AgentDependencyGraph()
        resolver = DependencyResolver(g)
        result = resolver.resolve()
        assert result.success is True
        assert result.installed == {}

    def test_single_skill_no_deps(self) -> None:
        """A single skill with no deps resolves trivially."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("solo", "1.0.0"))
        resolver = DependencyResolver(g, requirements={"solo": VersionConstraint("*")})
        result = resolver.resolve()
        assert result.success is True
        assert result.installed["solo"] == "1.0.0"

    def test_missing_required_skill(self) -> None:
        """Requiring a skill not in the graph fails."""
        g = AgentDependencyGraph()
        resolver = DependencyResolver(
            g, requirements={"missing": VersionConstraint(">=1.0.0")}
        )
        result = resolver.resolve()
        assert result.success is False
        assert any("missing" in msg for msg in result.conflicts)

    def test_unsatisfiable_version_constraint(self) -> None:
        """Requiring a version that doesn't exist fails."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("lib", "1.0.0"))
        resolver = DependencyResolver(
            g, requirements={"lib": VersionConstraint(">=5.0.0")}
        )
        result = resolver.resolve()
        assert result.success is False
        assert any("lib" in msg for msg in result.conflicts)

    def test_resolution_result_dataclass(self) -> None:
        """Resolution dataclass defaults are correct."""
        r = Resolution(success=True)
        assert r.installed == {}
        assert r.conflicts == []

    def test_no_requirements_no_forced_installs(self) -> None:
        """Without requirements, the solver is free to install nothing."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0"))
        g.add_skill(_make_node("B", "1.0.0"))
        resolver = DependencyResolver(g)
        result = resolver.resolve()
        assert result.success is True
        # Solver may or may not install anything -- both are valid

    def test_skill_node_default_fields(self) -> None:
        """SkillNode default fields are empty lists/sets."""
        node = SkillNode(name="test", version="1.0.0")
        assert node.dependencies == []
        assert node.conflicts == []
        assert node.capabilities == set()

    def test_version_constraint_repr(self) -> None:
        """VersionConstraint has a useful repr."""
        vc = VersionConstraint(">=1.0.0")
        assert ">=1.0.0" in repr(vc)

    def test_dependency_with_missing_dep_in_graph(self) -> None:
        """A depends on B but B is not in the graph: A cannot be installed."""
        g = AgentDependencyGraph()
        g.add_skill(_make_node("A", "1.0.0", deps=[("B", ">=1.0.0")]))
        # B is NOT added
        resolver = DependencyResolver(g, requirements={"A": VersionConstraint(">=1.0.0")})
        result = resolver.resolve()
        assert result.success is False
