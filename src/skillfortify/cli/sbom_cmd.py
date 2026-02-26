"""``skillfortify sbom <path>`` — Generate CycloneDX ASBOM for agent skills.

Discovers all skills in the target directory, runs static analysis on each,
and generates a CycloneDX 1.6 Agent Skill Bill of Materials (ASBOM) in JSON
format.

Exit Codes:
    0 — ASBOM generated successfully.
    2 — No skills found in the target path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from skillfortify.core.analyzer import StaticAnalyzer
from skillfortify.core.sbom import ASBOMGenerator, ASBOMMetadata
from skillfortify.parsers.registry import default_registry


@click.command("sbom")
@click.argument("path", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output", "-o",
    type=click.Path(),
    default=None,
    help="Output path for ASBOM (default: <path>/asbom.cdx.json).",
)
@click.option(
    "--project-name",
    type=str,
    default="agent-project",
    help="Name of the agent project (default: agent-project).",
)
@click.option(
    "--project-version",
    type=str,
    default="0.0.0",
    help="Version of the agent project (default: 0.0.0).",
)
def sbom_command(
    path: str,
    output: str | None,
    project_name: str,
    project_version: str,
) -> None:
    """Generate CycloneDX 1.6 Agent Skill Bill of Materials (ASBOM).

    Discovers all skills in PATH, analyzes each for security findings,
    and produces a CycloneDX 1.6 compliant ASBOM in JSON format.

    Exit code 0 on success, 2 if no skills found.
    """
    target = Path(path)
    registry = default_registry()
    skills = registry.discover(target)

    if not skills:
        click.echo("No skills found in the target directory.")
        sys.exit(2)

    # Analyze each skill
    analyzer = StaticAnalyzer()
    results = [analyzer.analyze(skill) for skill in skills]

    # Build ASBOM
    metadata = ASBOMMetadata(
        project_name=project_name,
        project_version=project_version,
    )
    generator = ASBOMGenerator(metadata=metadata)

    for skill, result in zip(skills, results):
        generator.add_from_parsed_skill(
            skill=skill,
            analysis_result=result,
        )

    # Write ASBOM
    out_path = Path(output) if output else target / "asbom.cdx.json"
    generator.write_json(out_path)

    # Display summary
    from skillfortify.cli.output import print_sbom_summary
    summary = generator.summary()
    print_sbom_summary(summary)
    click.echo(f"\nASBOM written to: {out_path}")
    sys.exit(0)
