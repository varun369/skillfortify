"""Lockfile factory --- constructing lockfiles from resolution results.

The ``from_resolution`` function constructs a ``Lockfile`` directly from a
``Resolution`` result produced by SAT-based dependency resolution. This is
the primary entry point in the normal workflow::

    resolver = DependencyResolver(graph, allowed_capabilities, requirements)
    resolution = resolver.resolve()
    lockfile = Lockfile.from_resolution(resolution, graph, trust_scores, parsed_skills)
    lockfile.write(Path("skill-lock.json"))

References
----------
.. [OPIUM07] Tucker, C. et al. (2007). "OPIUM: Optimal Package Install/
   Uninstall Manager." ICSE '07, 178-188. SAT-based resolution.
"""

from __future__ import annotations

from typing import Any

from skillfortify.core.lockfile.models import (
    LockedSkill,
    _score_to_level_str,
)


def _from_resolution(
    cls: type,
    resolution: Any,
    graph: Any | None = None,
    trust_scores: dict[str, float] | None = None,
    parsed_skills: dict[str, Any] | None = None,
) -> Any:
    """Create a lockfile from a dependency Resolution result.

    This is the primary factory method. Takes the output of
    ``DependencyResolver.resolve()`` and creates a complete lockfile.

    Args:
        resolution: A ``Resolution(success=True, installed={...})``
            from ``skillfortify.core.dependency``.
        graph: Optional ``AgentDependencyGraph`` for dependency and
            capability lookup.
        trust_scores: Optional dict of ``skill_name -> trust_score``
            (float in [0, 1]).
        parsed_skills: Optional dict of ``skill_name -> ParsedSkill``
            for integrity hash computation, format, and source path.

    Returns:
        A new ``Lockfile`` populated from the resolution result.

    Raises:
        ValueError: If the resolution was not successful.
    """
    if not resolution.success:
        raise ValueError(
            "Cannot create lockfile from failed resolution. "
            f"Conflicts: {resolution.conflicts}"
        )

    lf = cls()

    for skill_name, version in resolution.installed.items():
        # Defaults
        integrity = ""
        fmt = ""
        capabilities: list[str] = []
        dependencies: dict[str, str] = {}
        trust_score: float | None = None
        trust_level: str | None = None
        source_path = ""

        # Enrich from dependency graph
        if graph is not None:
            node = graph.get_node(skill_name, version)
            if node is not None:
                capabilities = sorted(node.capabilities)
                # Extract resolved dependency versions from resolution
                for dep in node.dependencies:
                    dep_version = resolution.installed.get(dep.skill_name)
                    if dep_version is not None:
                        dependencies[dep.skill_name] = dep_version

        # Enrich from parsed skills
        if parsed_skills is not None and skill_name in parsed_skills:
            ps = parsed_skills[skill_name]
            fmt = getattr(ps, "format", "")
            source_path = str(getattr(ps, "source_path", ""))
            raw_content = getattr(ps, "raw_content", "")
            if raw_content:
                integrity = cls.compute_integrity(raw_content)

        # Enrich from trust scores
        if trust_scores is not None and skill_name in trust_scores:
            trust_score = trust_scores[skill_name]
            trust_level = _score_to_level_str(trust_score)

        skill = LockedSkill(
            name=skill_name,
            version=version,
            integrity=integrity,
            format=fmt,
            capabilities=capabilities,
            dependencies=dependencies,
            trust_score=trust_score,
            trust_level=trust_level,
            source_path=source_path,
        )
        lf.add_skill(skill)

    return lf
