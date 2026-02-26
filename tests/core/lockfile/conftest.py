"""Shared helpers for lockfile tests."""

from __future__ import annotations

from skillfortify.core.lockfile import Lockfile, LockedSkill


def make_locked_skill(
    name: str = "test-skill",
    version: str = "1.0.0",
    content: str = "skill content",
    fmt: str = "mcp",
    capabilities: list[str] | None = None,
    dependencies: dict[str, str] | None = None,
    trust_score: float | None = None,
    trust_level: str | None = None,
    source_path: str = "/tmp/skills/test-skill",
) -> LockedSkill:
    """Convenience factory for LockedSkill instances with computed integrity."""
    return LockedSkill(
        name=name,
        version=version,
        integrity=Lockfile.compute_integrity(content),
        format=fmt,
        capabilities=capabilities or [],
        dependencies=dependencies or {},
        trust_score=trust_score,
        trust_level=trust_level,
        source_path=source_path,
    )


def make_lockfile_with_skills(*skills: LockedSkill) -> Lockfile:
    """Build a Lockfile pre-populated with the given skills."""
    lf = Lockfile()
    for s in skills:
        lf.add_skill(s)
    return lf
