"""``skillfortify scan [path]`` — Discover and analyze agent skills.

When called with a path, scans that specific directory for skills.
When called with no arguments or ``--system``, auto-discovers all AI
IDEs/tools on the system and scans everything found.

Exit Codes:
    0 — All skills passed analysis (no findings above threshold).
    1 — One or more skills have findings at or above the severity threshold.
    2 — No skills found in the target path or on the system.
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


def _run_directory_scan(
    path: str,
    output_format: str,
    severity_threshold: str,
) -> None:
    """Run a targeted scan on a specific directory.

    Args:
        path: Filesystem path to scan.
        output_format: Output format (text, json, html).
        severity_threshold: Minimum severity string.
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

    threshold = _SEVERITY_MAP[severity_threshold]
    results = _filter_results(results, threshold)

    _output_results(results, skills, output_format, target)

    has_findings = any(not r.is_safe for r in results)
    sys.exit(1 if has_findings else 0)


def _run_system_scan(
    output_format: str,
    severity_threshold: str,
) -> None:
    """Run a system-wide auto-discovery scan.

    Args:
        output_format: Output format (text, json, html).
        severity_threshold: Minimum severity string.
    """
    from skillfortify.discovery import SystemScanner

    scanner = SystemScanner()
    result = scanner.scan_system()

    if output_format == "text":
        _print_discovery_table(result)

    if not result.skills:
        if output_format == "json":
            click.echo(json.dumps({
                "ides_found": len(result.ides_found),
                "skills": [],
                "summary": "No skills found on system",
            }))
        elif output_format == "text":
            click.echo("\nNo skills found across any AI tools.")
        sys.exit(2)

    threshold = _SEVERITY_MAP[severity_threshold]
    results = _filter_results(result.results, threshold)

    _output_results(results, result.skills, output_format, None)

    has_findings = any(not r.is_safe for r in results)
    sys.exit(1 if has_findings else 0)


def _print_discovery_table(result: object) -> None:
    """Print the IDE discovery summary table.

    Args:
        result: A ``SystemScanResult`` instance.
    """
    from skillfortify.discovery import SystemScanResult

    if not isinstance(result, SystemScanResult):
        return

    click.echo("")
    click.echo("SkillFortify System Scan")
    click.echo("\u2550" * 40)
    click.echo("")
    click.echo("Discovered AI Tools:")

    for ide in result.ides_found:
        n_configs = len(ide.mcp_configs)
        n_skills = len(ide.skill_dirs)
        has_content = n_configs > 0 or n_skills > 0
        marker = "\u2713" if has_content else "\u25cb"
        path_str = str(ide.path).replace(str(Path.home()), "~")
        parts = [f"  {marker} {ide.profile.name:<18s} {path_str:<25s}"]
        details: list[str] = []
        if n_skills > 0:
            details.append(f"{n_skills} skill dir(s)")
        if n_configs > 0:
            details.append(f"{n_configs} MCP config(s)")
        if not details:
            details.append("(no skills detected)")
        parts.append(", ".join(details))
        click.echo("  ".join(parts))

    click.echo("")
    active = sum(
        1 for ide in result.ides_found
        if ide.mcp_configs or ide.skill_dirs
    )
    click.echo(
        f"Scanning {result.total_skills} skills across "
        f"{active} active IDE(s)..."
    )
    click.echo("")


def _output_results(
    results: list[AnalysisResult],
    skills: list,
    output_format: str,
    target: Path | None,
) -> None:
    """Dispatch results to the appropriate output formatter.

    Args:
        results: Filtered analysis results.
        skills: Parsed skills list (for HTML report).
        output_format: One of "text", "json", "html".
        target: Target directory (for HTML output path). None for system scan.
    """
    if output_format == "json":
        click.echo(json.dumps(_results_to_json(results), indent=2))
    elif output_format == "html":
        from skillfortify.dashboard.generator import DashboardGenerator
        gen = DashboardGenerator()
        out_path = (target or Path.cwd()) / "skillfortify-report.html"
        gen.write(out_path, results=results, skills=skills)
        click.echo(f"HTML report written to: {out_path.resolve()}")
    else:
        from skillfortify.cli.output import print_scan_results
        print_scan_results(results)


@click.command("scan")
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=False),
    required=False,
    default=None,
)
@click.option(
    "--system",
    is_flag=True,
    default=False,
    help="Scan all AI tools on this system (auto-discovery).",
)
@click.option(
    "--format", "output_format",
    type=click.Choice(["text", "json", "html"]),
    default="text",
    help="Output format: text (default), json, or html.",
)
@click.option(
    "--severity-threshold",
    type=click.Choice(["low", "medium", "high", "critical"]),
    default="low",
    help="Minimum severity to report (default: low).",
)
def scan_command(
    path: str | None,
    system: bool,
    output_format: str,
    severity_threshold: str,
) -> None:
    """Discover and analyze agent skills.

    When PATH is provided, scans that specific directory. When omitted or
    when --system is passed, auto-discovers all AI tools on the system
    (Claude Code, Cursor, VS Code, Windsurf, etc.) and scans everything.

    Exit code 0 if all skills are safe, 1 if any findings exist.
    """
    if path is None or system:
        _run_system_scan(output_format, severity_threshold)
    else:
        _run_directory_scan(path, output_format, severity_threshold)
