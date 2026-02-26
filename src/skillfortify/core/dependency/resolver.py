"""SAT-based dependency resolution engine for agent skill installations.

Encodes the resolution problem as a Boolean satisfiability (SAT) instance and
uses a CDCL solver (Glucose3 via python-sat) to find a valid installation plan.
The encoding follows the OPIUM approach (Tucker et al., ICSE 2007).

Theorem 4 (Resolution Soundness): The SAT encoding is satisfiable if and only
if a secure installation exists.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from skillfortify.core.dependency.constraints import VersionConstraint
from skillfortify.core.dependency.graph import AgentDependencyGraph

# SAT solver import -- python-sat is an optional dependency.
# When unavailable, DependencyResolver.resolve() raises ImportError.
try:
    from pysat.solvers import Solver as _PySATSolver
    from pysat.card import CardEnc, EncType  # noqa: F401 — reserved for future at-most-k encoding

    _PYSAT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYSAT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Resolution: The output of SAT-based dependency resolution
# ---------------------------------------------------------------------------


@dataclass
class Resolution:
    """Result of SAT-based dependency resolution.

    A successful resolution corresponds to a valid lockfile -- a concrete
    assignment of exactly one version per installed skill that satisfies all
    dependency, conflict, and capability constraints.

    Attributes:
        success: True if a satisfying assignment was found.
        installed: Mapping of skill_name -> resolved_version for the satisfying
            assignment. Empty if resolution failed.
        conflicts: Human-readable descriptions of why resolution failed.
            Empty if resolution succeeded.
    """

    success: bool
    installed: dict[str, str] = field(default_factory=dict)
    conflicts: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DependencyResolver: SAT-based resolution engine
# ---------------------------------------------------------------------------


class DependencyResolver:
    """SAT-based dependency resolver for agent skill installations.

    Encodes the resolution problem as a Boolean satisfiability (SAT) instance
    and uses a modern CDCL solver (Glucose3 via python-sat) to find a valid
    installation plan.

    **Theorem 4 (Resolution Soundness):** The SAT encoding is satisfiable if
    and only if a secure installation exists.

    Args:
        graph: The Agent Dependency Graph to resolve.
        allowed_capabilities: If provided, only skill-versions whose capability
            requirements are a subset of this set will be considered.
        requirements: If provided, a dict of skill_name -> VersionConstraint
            representing the root requirements (what the user explicitly asked
            to install). If None, all skills in the graph are candidates.
    """

    def __init__(
        self,
        graph: AgentDependencyGraph,
        allowed_capabilities: set[str] | None = None,
        requirements: dict[str, VersionConstraint] | None = None,
    ) -> None:
        self._graph = graph
        self._allowed_capabilities = allowed_capabilities
        self._requirements = requirements

    def resolve(self) -> Resolution:
        """Execute SAT-based dependency resolution.

        Returns:
            A ``Resolution`` object. If ``success`` is True, ``installed``
            contains the resolved skill-version mapping. If False,
            ``conflicts`` describes the reasons.

        Raises:
            ImportError: If python-sat is not installed.
        """
        if not _PYSAT_AVAILABLE:
            raise ImportError(
                "python-sat is required for SAT-based dependency resolution. "
                "Install it with: pip install 'skillfortify[sat]'"
            )

        clauses, var_map, inv_map = self._encode_sat()

        if not var_map:
            # Empty graph -- check if there are unsatisfied requirements
            if self._requirements:
                msgs = self._diagnose_failure()
                return Resolution(success=False, conflicts=msgs)
            return Resolution(success=True, installed={})

        solver = _PySATSolver(name="g3")
        try:
            for clause in clauses:
                solver.add_clause(clause)

            if solver.solve():
                model = solver.get_model()
                installed: dict[str, str] = {}
                for lit in model:
                    if lit > 0 and lit in inv_map:
                        name, version = inv_map[lit]
                        installed[name] = version
                return Resolution(success=True, installed=installed)
            else:
                # Resolution failed -- generate conflict descriptions
                conflict_msgs = self._diagnose_failure()
                return Resolution(success=False, conflicts=conflict_msgs)
        finally:
            solver.delete()

    def _encode_sat(
        self,
    ) -> tuple[
        list[list[int]], dict[tuple[str, str], int], dict[int, tuple[str, str]]
    ]:
        """Encode the dependency resolution problem as a SAT formula.

        Returns:
            A tuple of (clauses, var_map, inv_map) where:
            - clauses: List of CNF clauses (each a list of integer literals)
            - var_map: Mapping from (skill_name, version) to SAT variable
            - inv_map: Inverse mapping from SAT variable to (skill_name, version)
        """
        graph = self._graph
        clauses: list[list[int]] = []

        # Step 1: Assign boolean variables to each (skill, version) pair
        var_map: dict[tuple[str, str], int] = {}
        inv_map: dict[int, tuple[str, str]] = {}
        next_var = 1

        for (name, version) in graph._nodes:
            var_map[(name, version)] = next_var
            inv_map[next_var] = (name, version)
            next_var += 1

        if not var_map:
            return [], {}, {}

        # Step 2: At-most-one version per skill
        skills_versions: dict[str, list[int]] = defaultdict(list)
        for (name, version), var in var_map.items():
            skills_versions[name].append(var)

        for skill_name, vars_list in skills_versions.items():
            if len(vars_list) > 1:
                for i in range(len(vars_list)):
                    for j in range(i + 1, len(vars_list)):
                        clauses.append([-vars_list[i], -vars_list[j]])

        # Step 3: Root requirements
        if self._requirements:
            for req_name, req_constraint in self._requirements.items():
                satisfying_vars = []
                for version in graph.get_versions(req_name):
                    if req_constraint.satisfies(version):
                        var = var_map.get((req_name, version))
                        if var is not None:
                            satisfying_vars.append(var)
                if satisfying_vars:
                    clauses.append(satisfying_vars)
                else:
                    clauses.append([])

        # Step 4: Dependency constraints
        for (name, version), node in graph._nodes.items():
            sv_var = var_map[(name, version)]
            for dep in node.dependencies:
                satisfying = []
                for dep_ver in graph.get_versions(dep.skill_name):
                    if dep.constraint.satisfies(dep_ver):
                        dep_var = var_map.get((dep.skill_name, dep_ver))
                        if dep_var is not None:
                            satisfying.append(dep_var)

                if not satisfying:
                    clauses.append([-sv_var])
                else:
                    clauses.append([-sv_var] + satisfying)

        # Step 5: Conflict constraints
        for (name, version), node in graph._nodes.items():
            sv_var = var_map[(name, version)]
            for conflict in node.conflicts:
                for conf_ver in graph.get_versions(conflict.skill_name):
                    if conflict.constraint.satisfies(conf_ver):
                        conf_var = var_map.get((conflict.skill_name, conf_ver))
                        if conf_var is not None:
                            clauses.append([-sv_var, -conf_var])

        # Step 6: Capability bounds
        if self._allowed_capabilities is not None:
            for (name, version), node in graph._nodes.items():
                if not node.capabilities.issubset(self._allowed_capabilities):
                    sv_var = var_map[(name, version)]
                    clauses.append([-sv_var])

        return clauses, var_map, inv_map

    def _diagnose_failure(self) -> list[str]:
        """Generate human-readable conflict descriptions when resolution fails.

        Returns:
            List of conflict description strings.
        """
        msgs: list[str] = []
        graph = self._graph

        # Check unsatisfiable requirements
        if self._requirements:
            for req_name, req_constraint in self._requirements.items():
                versions = graph.get_versions(req_name)
                if not versions:
                    msgs.append(
                        f"Skill {req_name!r} is not available in the graph"
                    )
                else:
                    satisfying = [
                        v for v in versions if req_constraint.satisfies(v)
                    ]
                    if not satisfying:
                        msgs.append(
                            f"No version of {req_name!r} satisfies "
                            f"constraint {req_constraint.raw!r} "
                            f"(available: {', '.join(versions)})"
                        )

        # Check for dependency dead-ends
        for (name, version), node in graph._nodes.items():
            for dep in node.dependencies:
                dep_versions = graph.get_versions(dep.skill_name)
                satisfying = [
                    v for v in dep_versions if dep.constraint.satisfies(v)
                ]
                if not satisfying:
                    msgs.append(
                        f"{name}@{version} requires {dep.skill_name} "
                        f"{dep.constraint.raw!r} but no satisfying version exists"
                    )

        # Check for mutual conflicts with requirements
        if self._requirements:
            for req_name in self._requirements:
                for version in graph.get_versions(req_name):
                    node = graph.get_node(req_name, version)
                    if node:
                        for conflict in node.conflicts:
                            if conflict.skill_name in self._requirements:
                                msgs.append(
                                    f"{req_name}@{version} conflicts with "
                                    f"required skill {conflict.skill_name!r}"
                                )

        if not msgs:
            msgs.append(
                "Resolution failed: no satisfying assignment exists "
                "(constraint system is unsatisfiable)"
            )

        return msgs
