"""``skillfortify trust <skill-path>`` — Compute and display trust score.

Parses a single skill, runs the static analyzer for a behavioral signal,
computes trust using the TrustEngine, and displays the resulting score
breakdown with SLSA-inspired trust level mapping.

Exit Codes:
    0 — Trust score computed and displayed.
    2 — Skill file could not be parsed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from skillfortify.core.analyzer import Severity, StaticAnalyzer
from skillfortify.core.trust import TrustEngine, TrustSignals
from skillfortify.parsers.registry import default_registry

# Default baseline values for signals we cannot measure locally.
# Provenance, community, and historical signals require external data
# sources (registries, review systems, CVE databases). We use 0.5 as
# a neutral baseline -- "no information, assume middle ground."
_DEFAULT_PROVENANCE: float = 0.5
_DEFAULT_COMMUNITY: float = 0.5
_DEFAULT_HISTORICAL: float = 0.5


def _find_project_root(skill_path: Path) -> Path | None:
    """Walk up from a skill file to find the project root.

    Args:
        skill_path: Absolute path to the skill file.

    Returns:
        The project root directory, or None if not found.
    """
    registry = default_registry()
    current = skill_path.parent
    for _ in range(5):
        skills = registry.discover(current)
        if skills:
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _compute_behavioral_signal(result) -> float:
    """Derive a behavioral trust signal from static analysis results.

    Maps the analysis result to a [0, 1] score:
    - 1.0 if no findings (clean analysis).
    - Decremented by severity-weighted penalties per finding.
    - Minimum of 0.0.

    Args:
        result: An AnalysisResult from the StaticAnalyzer.

    Returns:
        Behavioral signal in [0, 1].
    """
    if result.is_safe:
        return 1.0

    penalty_map = {
        Severity.LOW: 0.05,
        Severity.MEDIUM: 0.10,
        Severity.HIGH: 0.20,
        Severity.CRITICAL: 0.35,
    }
    total_penalty = sum(
        penalty_map.get(f.severity, 0.1) for f in result.findings
    )
    return max(0.0, 1.0 - total_penalty)


def _trust_score_to_json(score) -> dict:
    """Convert a TrustScore to a JSON-serializable dict.

    Args:
        score: TrustScore instance from the trust engine.

    Returns:
        Dictionary with all trust score fields.
    """
    return {
        "skill_name": score.skill_name,
        "version": score.version,
        "intrinsic_score": round(score.intrinsic_score, 4),
        "effective_score": round(score.effective_score, 4),
        "level": score.level.name,
        "signals": score.signals.as_dict(),
    }


@click.command("trust")
@click.argument("skill_path", type=click.Path(exists=True))
@click.option(
    "--format", "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
def trust_command(skill_path: str, output_format: str) -> None:
    """Compute and display trust score for an agent skill.

    Parses the skill at SKILL_PATH, runs static analysis for a behavioral
    signal, and computes a multi-signal trust score. Provenance, community,
    and historical signals use baseline defaults (0.5) since real data
    sources are not yet connected.

    Exit code 0 on success, 2 if the skill cannot be parsed.
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

    # Find the matching skill
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

    # Run analysis for behavioral signal
    analyzer = StaticAnalyzer()
    result = analyzer.analyze(skill)
    behavioral = _compute_behavioral_signal(result)

    # Compute trust score
    signals = TrustSignals(
        provenance=_DEFAULT_PROVENANCE,
        behavioral=behavioral,
        community=_DEFAULT_COMMUNITY,
        historical=_DEFAULT_HISTORICAL,
    )
    engine = TrustEngine()
    trust_score = engine.compute_score(
        skill_name=skill.name,
        version=skill.version,
        signals=signals,
    )

    if output_format == "json":
        click.echo(json.dumps(_trust_score_to_json(trust_score), indent=2))
    else:
        from skillfortify.cli.output import print_trust_score
        print_trust_score(trust_score)

    sys.exit(0)
