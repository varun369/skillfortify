"""``skillfortify verify <skill-path>`` — Formally verify a single skill file.

Parses the skill (auto-detecting format by walking up the directory tree),
runs full three-phase static analysis, and shows detailed capability inference
results including POLA (Principle of Least Authority) compliance.

Exit Codes:
    0 — Skill passed all verification checks.
    1 — Skill has one or more security findings.
    2 — Skill file could not be parsed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from skillfortify.core.analyzer import StaticAnalyzer
from skillfortify.parsers.registry import default_registry


def _find_project_root(skill_path: Path) -> Path | None:
    """Walk up from a skill file to find the project root.

    The project root is the directory where a parser's ``can_parse()``
    returns True. For Claude skills at ``.claude/skills/foo.md``, the
    root is two levels above the skills directory.

    Args:
        skill_path: Absolute path to the skill file.

    Returns:
        The project root directory, or None if not found.
    """
    registry = default_registry()
    current = skill_path.parent
    # Walk up at most 5 levels to find a parseable root
    for _ in range(5):
        skills = registry.discover(current)
        if skills:
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _result_to_json(result, skill_format: str) -> dict:
    """Convert a single analysis result to JSON-serializable dict.

    Args:
        result: AnalysisResult from the static analyzer.
        skill_format: The detected skill format string.

    Returns:
        Dictionary with complete verification details.
    """
    caps = []
    if result.inferred_capabilities:
        caps = [
            {"resource": c.resource, "access": c.access.name}
            for c in result.inferred_capabilities
        ]
    findings = [
        {
            "severity": f.severity.name,
            "message": f.message,
            "attack_class": f.attack_class,
            "finding_type": f.finding_type,
            "evidence": f.evidence,
        }
        for f in result.findings
    ]
    return {
        "skill_name": result.skill_name,
        "format": skill_format,
        "is_safe": result.is_safe,
        "max_severity": result.max_severity.name if result.max_severity else None,
        "inferred_capabilities": caps,
        "findings": findings,
    }


@click.command("verify")
@click.argument("skill_path", type=click.Path(exists=True))
@click.option(
    "--format", "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
def verify_command(skill_path: str, output_format: str) -> None:
    """Formally verify a single agent skill file.

    Parses the skill at SKILL_PATH, runs three-phase static analysis,
    and shows detailed capability inference and POLA compliance results.

    Exit code 0 if the skill is safe, 1 if findings exist.
    """
    target = Path(skill_path)
    resolved = target.resolve()

    # Find project root by walking up directory tree
    root = _find_project_root(resolved)
    if root is None:
        if output_format == "json":
            click.echo(json.dumps({
                "error": f"Could not parse skill at: {skill_path}",
            }))
        else:
            click.echo(f"Error: Could not parse skill at: {skill_path}")
        sys.exit(2)

    # Discover all skills from the project root
    registry = default_registry()
    all_skills = registry.discover(root)

    # Find the skill matching this specific file path
    matched = [
        s for s in all_skills
        if Path(s.source_path).resolve() == resolved
    ]

    if not matched:
        if output_format == "json":
            click.echo(json.dumps({
                "error": f"Could not parse skill at: {skill_path}",
            }))
        else:
            click.echo(f"Error: Could not parse skill at: {skill_path}")
        sys.exit(2)

    skill = matched[0]
    analyzer = StaticAnalyzer()
    result = analyzer.analyze(skill)

    if output_format == "json":
        click.echo(json.dumps(
            _result_to_json(result, skill.format), indent=2
        ))
    else:
        from skillfortify.cli.output import print_analysis_detail
        print_analysis_detail(result)

    sys.exit(0 if result.is_safe else 1)
