"""Agent Dependency Graph (ADG) data structure and graph algorithms.

Implements the formal ADG = (S, V, D, C, Cap) data structure: skill nodes,
cycle detection, transitive dependency computation (BFS), and vulnerability
propagation through the dependency graph.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from skillfortify.core.dependency.constraints import (
    SkillConflict,
    SkillDependency,
    _version_key,
)


# ---------------------------------------------------------------------------
# SkillNode: A vertex in the ADG
# ---------------------------------------------------------------------------


@dataclass
class SkillNode:
    """A node in the ADG representing a specific skill at a specific version.

    Carries dependency edges, conflict edges, and required capabilities expressed
    as "resource:LEVEL" strings (e.g., "filesystem:WRITE").
    """

    name: str
    version: str
    dependencies: list[SkillDependency] = field(default_factory=list)
    conflicts: list[SkillConflict] = field(default_factory=list)
    capabilities: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# AgentDependencyGraph: The ADG data structure
# ---------------------------------------------------------------------------


class AgentDependencyGraph:
    """The complete dependency graph for an agent skill installation.

    Formal definition: ADG = (S, V, D, C, Cap) where S is the set of skill
    names, V maps each skill to its available versions, D captures dependency
    relations, C captures conflict relations, and Cap captures per-version
    capability requirements.

    The graph supports:
    - Adding skill nodes (multiple versions per skill name)
    - Querying available versions, dependencies, and conflicts
    - Cycle detection via DFS coloring
    - Transitive dependency computation via BFS
    - Transitive vulnerability propagation

    Thread safety: This class is NOT thread-safe. External synchronization is
    required for concurrent access.
    """

    def __init__(self) -> None:
        self._nodes: dict[tuple[str, str], SkillNode] = {}

    @property
    def skills(self) -> set[str]:
        """Return the set S of all skill names in the graph."""
        return {name for name, _ in self._nodes}

    @property
    def node_count(self) -> int:
        """Return the total number of (skill, version) nodes."""
        return len(self._nodes)

    def add_skill(self, node: SkillNode) -> None:
        """Add a skill node to the graph.

        If a node with the same (name, version) already exists, it is replaced.

        Args:
            node: The ``SkillNode`` to add.
        """
        self._nodes[(node.name, node.version)] = node

    def get_node(self, name: str, version: str) -> SkillNode | None:
        """Retrieve a specific skill node by name and version.

        Args:
            name: Skill name.
            version: Version string.

        Returns:
            The ``SkillNode``, or None if not found.
        """
        return self._nodes.get((name, version))

    def get_versions(self, skill_name: str) -> list[str]:
        """Return all available versions of a skill, sorted descending (newest first).

        Implements V(s) from the formal definition.

        Args:
            skill_name: The skill name to look up.

        Returns:
            List of version strings sorted newest-first. Empty if skill unknown.
        """
        versions = [
            ver for (name, ver) in self._nodes if name == skill_name
        ]
        versions.sort(key=_version_key, reverse=True)
        return versions

    def get_dependencies(self, name: str, version: str) -> list[SkillDependency]:
        """Return the dependency list for a specific skill-version.

        Implements D(s, v) from the formal definition.

        Args:
            name: Skill name.
            version: Version string.

        Returns:
            List of ``SkillDependency`` edges. Empty if node not found.
        """
        node = self._nodes.get((name, version))
        return list(node.dependencies) if node else []

    def get_conflicts(self, name: str, version: str) -> list[SkillConflict]:
        """Return the conflict list for a specific skill-version.

        Implements C(s, v) from the formal definition.

        Args:
            name: Skill name.
            version: Version string.

        Returns:
            List of ``SkillConflict`` edges. Empty if node not found.
        """
        node = self._nodes.get((name, version))
        return list(node.conflicts) if node else []

    def detect_cycles(self) -> list[list[str]]:
        """Detect circular dependencies using iterative DFS.

        Circular dependencies in the skill graph indicate potential infinite
        loops during resolution or loading. For agent skills, cycles are a
        security concern because they can create unbounded recursion during
        capability evaluation.

        Returns:
            A list of cycles, where each cycle is a list of skill names forming
            the cycle path (e.g., ["A", "B", "C", "A"]). Empty if no cycles.
        """
        # Build adjacency list: skill_name -> set of dependency skill names
        # We collapse versions to skill-name-level to detect name-level cycles.
        adj: dict[str, set[str]] = defaultdict(set)
        all_skills: set[str] = set()

        for (name, version), node in self._nodes.items():
            all_skills.add(name)
            for dep in node.dependencies:
                adj[name].add(dep.skill_name)
                all_skills.add(dep.skill_name)

        # Standard cycle detection via DFS coloring
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {s: WHITE for s in all_skills}
        parent: dict[str, str | None] = {s: None for s in all_skills}
        cycles: list[list[str]] = []

        def _dfs(u: str) -> None:
            color[u] = GRAY
            for v in adj.get(u, set()):
                if color.get(v, WHITE) == GRAY:
                    # Back edge found: extract cycle
                    cycle = [v, u]
                    cur = parent.get(u)
                    while cur is not None and cur != v:
                        cycle.append(cur)
                        cur = parent.get(cur)
                    cycle.append(v)
                    cycle.reverse()
                    cycles.append(cycle)
                elif color.get(v, WHITE) == WHITE:
                    parent[v] = u
                    _dfs(v)
            color[u] = BLACK

        for s in all_skills:
            if color[s] == WHITE:
                _dfs(s)

        return cycles

    def transitive_dependencies(
        self, name: str, version: str
    ) -> set[tuple[str, str]]:
        """Compute the transitive closure of dependencies for a skill-version.

        Uses BFS over the dependency edges, resolving each dependency constraint
        against available versions. For each dependency, the *highest* satisfying
        version is selected (optimistic resolution).

        Args:
            name: Root skill name.
            version: Root skill version.

        Returns:
            Set of (skill_name, version) tuples in the transitive dependency
            closure. Does NOT include the root itself.
        """
        visited: set[tuple[str, str]] = set()
        queue: deque[tuple[str, str]] = deque()
        queue.append((name, version))

        while queue:
            cur_name, cur_ver = queue.popleft()
            node = self._nodes.get((cur_name, cur_ver))
            if node is None:
                continue

            for dep in node.dependencies:
                # Find highest satisfying version
                candidates = self.get_versions(dep.skill_name)
                for cand in candidates:
                    if dep.constraint.satisfies(cand):
                        pair = (dep.skill_name, cand)
                        if pair not in visited:
                            visited.add(pair)
                            queue.append(pair)
                        break  # take highest satisfying version

        # Remove root if present
        visited.discard((name, version))
        return visited

    def propagate_vulnerabilities(
        self, vulnerable: set[tuple[str, str]]
    ) -> dict[tuple[str, str], list[tuple[str, str]]]:
        """Propagate known vulnerabilities through the dependency graph.

        If skill A depends on skill B and B is vulnerable, then A is
        *transitively affected*. This computes the reverse transitive closure:
        for each vulnerable (name, version), find all nodes that depend on it
        (directly or transitively).

        Args:
            vulnerable: Set of known-vulnerable (skill_name, version) pairs.

        Returns:
            Dictionary mapping each *affected* (skill_name, version) to the list
            of vulnerable (skill_name, version) pairs in its dependency chain
            that make it affected.
        """
        # Build reverse dependency map
        reverse_deps: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)

        for (name, version), node in self._nodes.items():
            for dep in node.dependencies:
                candidates = self.get_versions(dep.skill_name)
                for cand in candidates:
                    if dep.constraint.satisfies(cand):
                        reverse_deps[(dep.skill_name, cand)].add((name, version))

        # BFS from each vulnerable node upward through reverse deps
        affected: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)

        for vuln in vulnerable:
            visited: set[tuple[str, str]] = set()
            queue: deque[tuple[str, str]] = deque()
            queue.append(vuln)

            while queue:
                current = queue.popleft()
                for dependent in reverse_deps.get(current, set()):
                    if dependent not in visited and dependent not in vulnerable:
                        visited.add(dependent)
                        affected[dependent].add(vuln)
                        queue.append(dependent)

        # Convert sets to sorted lists for deterministic output
        return {k: sorted(v) for k, v in affected.items()}
