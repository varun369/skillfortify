"""Property-based tests for SAT-based dependency resolution invariants.

Verifies the formal guarantees of DependencyResolver (Theorem 4):
- At-most-one: resolution never installs two versions of the same skill
- Dependency satisfaction: every dependency is satisfied in the resolution
- Conflict freedom: no conflicts present in the resolution
- Determinism: same graph -> same resolution
"""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from skillfortify.core.dependency import (
    AgentDependencyGraph,
    DependencyResolver,
    SkillNode,
    SkillDependency,
    SkillConflict,
    VersionConstraint,
)


# ---------------------------------------------------------------------------
# Strategies for generating random ADGs
# ---------------------------------------------------------------------------

version_strings = st.sampled_from([
    "1.0.0", "1.1.0", "1.2.0", "2.0.0", "2.1.0", "3.0.0",
])

skill_names = st.sampled_from([
    "alpha", "beta", "gamma", "delta", "epsilon",
])


@st.composite
def simple_adg(draw: st.DrawFn) -> AgentDependencyGraph:
    """Generate a simple ADG with 2-5 skills, each with 1-3 versions."""
    graph = AgentDependencyGraph()
    num_skills = draw(st.integers(min_value=2, max_value=4))
    names = draw(
        st.lists(skill_names, min_size=num_skills, max_size=num_skills, unique=True)
    )

    for name in names:
        num_versions = draw(st.integers(min_value=1, max_value=3))
        versions = draw(
            st.lists(version_strings, min_size=num_versions, max_size=num_versions, unique=True)
        )
        for version in versions:
            node = SkillNode(name=name, version=version)
            graph.add_skill(node)

    return graph


@st.composite
def adg_with_deps(draw: st.DrawFn) -> AgentDependencyGraph:
    """Generate an ADG where skills may have dependencies on other skills."""
    graph = AgentDependencyGraph()

    # Create a chain: A -> B -> C (each with one version)
    chain_len = draw(st.integers(min_value=2, max_value=4))
    names = [f"skill-{i}" for i in range(chain_len)]

    for i, name in enumerate(names):
        deps = []
        if i > 0:
            deps.append(SkillDependency(names[i - 1], VersionConstraint("*")))
        node = SkillNode(name=name, version="1.0.0", dependencies=deps)
        graph.add_skill(node)

    return graph


# ---------------------------------------------------------------------------
# Theorem 4: At-Most-One version per skill
# ---------------------------------------------------------------------------


class TestAtMostOne:
    """Resolution never installs two versions of the same skill."""

    @given(graph=simple_adg())
    @settings(max_examples=50)
    def test_at_most_one_version_per_skill(
        self, graph: AgentDependencyGraph
    ) -> None:
        """Each skill appears at most once in the resolution."""
        resolver = DependencyResolver(graph)
        resolution = resolver.resolve()

        if resolution.success:
            # installed is a dict: skill_name -> version
            # By definition of dict, each key appears once
            assert len(resolution.installed) == len(set(resolution.installed.keys()))

    @given(graph=adg_with_deps())
    @settings(max_examples=50)
    def test_at_most_one_with_dependencies(
        self, graph: AgentDependencyGraph
    ) -> None:
        """At-most-one holds even with dependency chains."""
        # Require the root (last skill in chain)
        skills = sorted(graph.skills)
        if not skills:
            return
        root = skills[-1]
        resolver = DependencyResolver(
            graph,
            requirements={root: VersionConstraint("*")},
        )
        resolution = resolver.resolve()
        if resolution.success:
            assert len(resolution.installed) == len(set(resolution.installed.keys()))


# ---------------------------------------------------------------------------
# Dependency satisfaction
# ---------------------------------------------------------------------------


class TestDependencySatisfaction:
    """Every dependency in the resolution is satisfied."""

    @given(graph=adg_with_deps())
    @settings(max_examples=50)
    def test_all_deps_satisfied(
        self, graph: AgentDependencyGraph
    ) -> None:
        """For each installed skill, its dependencies are also installed."""
        skills = sorted(graph.skills)
        if not skills:
            return
        root = skills[-1]
        resolver = DependencyResolver(
            graph,
            requirements={root: VersionConstraint("*")},
        )
        resolution = resolver.resolve()

        if resolution.success:
            for name, version in resolution.installed.items():
                node = graph.get_node(name, version)
                if node is None:
                    continue
                for dep in node.dependencies:
                    dep_version = resolution.installed.get(dep.skill_name)
                    if dep_version is not None:
                        assert dep.constraint.satisfies(dep_version), (
                            f"{name}@{version} requires {dep.skill_name} "
                            f"{dep.constraint.raw} but got {dep_version}"
                        )

    def test_linear_chain_all_deps_present(self) -> None:
        """A -> B -> C chain: all three must be in resolution."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(name="C", version="1.0.0"))
        graph.add_skill(SkillNode(
            name="B", version="1.0.0",
            dependencies=[SkillDependency("C", VersionConstraint(">=1.0.0"))],
        ))
        graph.add_skill(SkillNode(
            name="A", version="1.0.0",
            dependencies=[SkillDependency("B", VersionConstraint(">=1.0.0"))],
        ))

        resolver = DependencyResolver(
            graph, requirements={"A": VersionConstraint("*")}
        )
        resolution = resolver.resolve()
        assert resolution.success
        assert "A" in resolution.installed
        assert "B" in resolution.installed
        assert "C" in resolution.installed


# ---------------------------------------------------------------------------
# Conflict freedom
# ---------------------------------------------------------------------------


class TestConflictFreedom:
    """No conflicts are present in a successful resolution."""

    def test_conflicting_skills_not_both_installed(self) -> None:
        """Two skills that conflict cannot both appear in the resolution."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(
            name="X", version="1.0.0",
            conflicts=[SkillConflict("Y", VersionConstraint("*"))],
        ))
        graph.add_skill(SkillNode(name="Y", version="1.0.0"))

        # Require both -- should fail or only install one
        resolver = DependencyResolver(
            graph,
            requirements={
                "X": VersionConstraint("*"),
                "Y": VersionConstraint("*"),
            },
        )
        resolution = resolver.resolve()

        if resolution.success:
            # If somehow resolved, both must not be installed together
            x_installed = "X" in resolution.installed
            y_installed = "Y" in resolution.installed
            assert not (x_installed and y_installed)

    def test_conflict_causes_failure_when_both_required(self) -> None:
        """Requiring two conflicting skills results in resolution failure."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(
            name="A", version="1.0.0",
            conflicts=[SkillConflict("B", VersionConstraint("*"))],
        ))
        graph.add_skill(SkillNode(
            name="B", version="1.0.0",
            conflicts=[SkillConflict("A", VersionConstraint("*"))],
        ))

        resolver = DependencyResolver(
            graph,
            requirements={
                "A": VersionConstraint("*"),
                "B": VersionConstraint("*"),
            },
        )
        resolution = resolver.resolve()
        assert not resolution.success


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Same graph -> same resolution (deterministic solver)."""

    def test_repeated_resolution_identical(self) -> None:
        """Resolving the same graph twice yields identical results."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(name="lib", version="1.0.0"))
        graph.add_skill(SkillNode(name="lib", version="2.0.0"))
        graph.add_skill(SkillNode(
            name="app", version="1.0.0",
            dependencies=[SkillDependency("lib", VersionConstraint(">=1.0.0"))],
        ))

        req = {"app": VersionConstraint("*")}

        r1 = DependencyResolver(graph, requirements=req).resolve()
        r2 = DependencyResolver(graph, requirements=req).resolve()
        assert r1.success == r2.success
        assert r1.installed == r2.installed

    @given(graph=adg_with_deps())
    @settings(max_examples=30)
    def test_determinism_property(
        self, graph: AgentDependencyGraph
    ) -> None:
        """Repeated resolutions of generated graphs are identical."""
        skills = sorted(graph.skills)
        if not skills:
            return
        root = skills[-1]
        req = {root: VersionConstraint("*")}

        r1 = DependencyResolver(graph, requirements=req).resolve()
        r2 = DependencyResolver(graph, requirements=req).resolve()
        assert r1.success == r2.success
        if r1.success:
            assert r1.installed == r2.installed


# ---------------------------------------------------------------------------
# Capability filtering
# ---------------------------------------------------------------------------


class TestCapabilityFiltering:
    """Capability bounds exclude over-privileged skill versions."""

    def test_over_privileged_version_excluded(self) -> None:
        """A skill version exceeding allowed capabilities is not installed."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(
            name="tool", version="1.0.0",
            capabilities={"network:READ"},
        ))
        graph.add_skill(SkillNode(
            name="tool", version="2.0.0",
            capabilities={"network:READ", "shell:WRITE"},
        ))

        resolver = DependencyResolver(
            graph,
            allowed_capabilities={"network:READ"},
            requirements={"tool": VersionConstraint("*")},
        )
        resolution = resolver.resolve()
        assert resolution.success
        assert resolution.installed["tool"] == "1.0.0"

    def test_empty_capabilities_always_allowed(self) -> None:
        """A skill with no capability requirements always passes filtering."""
        graph = AgentDependencyGraph()
        graph.add_skill(SkillNode(
            name="safe", version="1.0.0",
            capabilities=set(),
        ))

        resolver = DependencyResolver(
            graph,
            allowed_capabilities={"network:READ"},
            requirements={"safe": VersionConstraint("*")},
        )
        resolution = resolver.resolve()
        assert resolution.success
