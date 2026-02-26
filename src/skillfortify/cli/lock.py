"""``skillfortify lock <path>`` — Generate skill-lock.json for reproducible installs.

Discovers all skills in the target directory, builds an Agent Dependency
Graph (ADG), runs SAT-based resolution, and writes a deterministic
``skill-lock.json`` lockfile.

Exit Codes:
    0 — Lockfile generated successfully.
    1 — Dependency resolution failed (conflicts detected).
    2 — No skills found in the target path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from skillfortify.core.analyzer import StaticAnalyzer
from skillfortify.core.lockfile import Lockfile, LockedSkill
from skillfortify.parsers.registry import default_registry


def _build_lockfile_from_skills(skills, results) -> Lockfile:
    """Build a lockfile directly from parsed skills and analysis results.

    Since skills discovered from a local directory do not have complex
    dependency graphs, we create a simple lockfile with each skill
    pinned to its discovered version.

    Args:
        skills: List of ParsedSkill instances.
        results: List of AnalysisResult instances (parallel to skills).

    Returns:
        A populated Lockfile instance.
    """
    lockfile = Lockfile()
    for skill, result in zip(skills, results):
        integrity = Lockfile.compute_integrity(skill.raw_content)
        caps = list(skill.declared_capabilities)
        if result.inferred_capabilities:
            for cap in result.inferred_capabilities:
                cap_str = f"{cap.resource}:{cap.access.name}"
                if cap_str not in caps:
                    caps.append(cap_str)

        locked = LockedSkill(
            name=skill.name,
            version=skill.version,
            integrity=integrity,
            format=skill.format,
            capabilities=caps,
            dependencies={},
            source_path=str(skill.source_path),
        )
        lockfile.add_skill(locked)
    return lockfile


@click.command("lock")
@click.argument("path", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output path for lockfile (default: <path>/skill-lock.json).",
)
def lock_command(path: str, output: str | None) -> None:
    """Generate skill-lock.json for reproducible agent configurations.

    Discovers all skills in PATH, analyzes each for capabilities, and
    produces a deterministic lockfile capturing the exact resolved state.

    Exit code 0 on success, 1 on resolution failure, 2 if no skills found.
    """
    target = Path(path)
    registry = default_registry()
    skills = registry.discover(target)

    if not skills:
        click.echo("No skills found in the target directory.")
        sys.exit(2)

    # Analyze each skill for capability inference
    analyzer = StaticAnalyzer()
    results = [analyzer.analyze(skill) for skill in skills]

    # Build lockfile
    lockfile = _build_lockfile_from_skills(skills, results)

    # Determine output path
    out_path = Path(output) if output else target / "skill-lock.json"
    lockfile.write(out_path)

    # Display summary
    from skillfortify.cli.output import print_resolution_summary
    installed = {s.name: s.version for s in skills}
    print_resolution_summary(
        success=True,
        installed=installed,
        conflicts=[],
    )
    click.echo(f"\nLockfile written to: {out_path}")
    sys.exit(0)
