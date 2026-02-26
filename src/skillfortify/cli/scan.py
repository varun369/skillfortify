"""``skillfortify scan <path>`` — Discover and analyze all skills in a directory.

Uses the ``ParserRegistry`` to auto-detect skill formats (Claude, MCP,
OpenClaw) and runs the ``StaticAnalyzer`` on each discovered skill.

Exit Codes:
    0 — All skills passed analysis (no findings above threshold).
    1 — One or more skills have findings at or above the severity threshold.
    2 — No skills found in the target path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from skillfortify.core.analyzer import AnalysisResult, Severity, StaticAnalyzer
from skillfortify.parsers.registry import default_registry

# Severity threshold mapping (string -> IntEnum)
_SEVERITY_MAP: dict[str, Severity] = {
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


def _filter_results(
    results: list[AnalysisResult],
    threshold: Severity,
) -> list[AnalysisResult]:
    """Filter analysis results to only include findings at or above threshold.

    Args:
        results: Raw analysis results from the analyzer.
        threshold: Minimum severity to report.

    Returns:
        Filtered list where each result only contains findings >= threshold.
    """
    filtered: list[AnalysisResult] = []
    for result in results:
        kept = [f for f in result.findings if f.severity >= threshold]
        is_safe = len(kept) == 0
        filtered.append(
            AnalysisResult(
                skill_name=result.skill_name,
                is_safe=is_safe,
                findings=kept,
                inferred_capabilities=result.inferred_capabilities,
            )
        )
    return filtered


def _results_to_json(results: list[AnalysisResult]) -> list[dict]:
    """Convert analysis results to JSON-serializable dicts.

    Args:
        results: Analysis results to serialize.

    Returns:
        List of dictionaries, one per analyzed skill.
    """
    out: list[dict] = []
    for r in results:
        caps = []
        if r.inferred_capabilities:
            caps = [
                {"resource": c.resource, "access": c.access.name}
                for c in r.inferred_capabilities
            ]
        findings = [
            {
                "severity": f.severity.name,
                "message": f.message,
                "attack_class": f.attack_class,
                "finding_type": f.finding_type,
                "evidence": f.evidence,
            }
            for f in r.findings
        ]
        out.append({
            "skill_name": r.skill_name,
            "is_safe": r.is_safe,
            "findings_count": len(r.findings),
            "max_severity": r.max_severity.name if r.max_severity else None,
            "inferred_capabilities": caps,
            "findings": findings,
        })
    return out


@click.command("scan")
@click.argument("path", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--format", "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--severity-threshold",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="low",
    help="Minimum severity to report (default: low).",
)
def scan_command(
    path: str,
    output_format: str,
    severity_threshold: str,
) -> None:
    """Discover and analyze all agent skills in PATH.

    Scans the target directory for Claude Code, MCP, and OpenClaw skill
    formats. Runs three-phase static analysis on each discovered skill
    and reports security findings.

    Exit code 0 if all skills are safe, 1 if any findings exist.
    """
    target = Path(path)
    registry = default_registry()
    skills = registry.discover(target)

    if not skills:
        if output_format == "json":
            click.echo(json.dumps({"skills": [], "summary": "No skills found"}))
        else:
            click.echo("No skills found in the target directory.")
        sys.exit(2)

    analyzer = StaticAnalyzer()
    results = [analyzer.analyze(skill) for skill in skills]

    # Apply severity threshold filter
    threshold = _SEVERITY_MAP[severity_threshold]
    results = _filter_results(results, threshold)

    if output_format == "json":
        click.echo(json.dumps(_results_to_json(results), indent=2))
    else:
        from skillfortify.cli.output import print_scan_results
        print_scan_results(results)

    # Exit code: 1 if any skill is unsafe after filtering
    has_findings = any(not r.is_safe for r in results)
    sys.exit(1 if has_findings else 0)
