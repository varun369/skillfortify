"""Rich output formatting helpers for the SkillFortify CLI.

Provides consistent, severity-colored terminal output for scan results,
analysis details, trust scores, resolution summaries, and SBOM statistics.

Severity Color Mapping (aligned with CVSS v4.0):
    CRITICAL = bold red, HIGH = yellow, MEDIUM = cyan, LOW = green
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skillfortify.core.analyzer import AnalysisResult, Severity
from skillfortify.core.trust import TrustLevel, TrustScore

_SEVERITY_STYLES: dict[Severity, str] = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "yellow",
    Severity.MEDIUM: "cyan",
    Severity.LOW: "green",
}

_TRUST_LEVEL_STYLES: dict[TrustLevel, str] = {
    TrustLevel.UNSIGNED: "bold red",
    TrustLevel.SIGNED: "yellow",
    TrustLevel.COMMUNITY_VERIFIED: "cyan",
    TrustLevel.FORMALLY_VERIFIED: "bold green",
}

console = Console()


def severity_style(severity: Severity) -> str:
    """Return the Rich style string for a given severity level."""
    return _SEVERITY_STYLES.get(severity, "white")


def trust_level_style(level: TrustLevel) -> str:
    """Return the Rich style string for a given trust level."""
    return _TRUST_LEVEL_STYLES.get(level, "white")


def print_scan_results(results: list[AnalysisResult]) -> None:
    """Print a summary table of scan results for multiple skills.

    Args:
        results: List of analysis results from scanning a directory.
    """
    if not results:
        console.print("[dim]No skills found to scan.[/dim]")
        return

    table = Table(title="SkillFortify Scan Results", show_header=True, header_style="bold")
    table.add_column("Skill", style="bold")
    table.add_column("Format", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Findings", justify="right")
    table.add_column("Max Severity", justify="center")

    for result in results:
        if result.is_safe:
            status = Text("SAFE", style="bold green")
            max_sev = Text("-", style="dim")
        else:
            status = Text("UNSAFE", style="bold red")
            sev = result.max_severity
            sev_name = sev.name if sev else "UNKNOWN"
            style = severity_style(sev) if sev else "white"
            max_sev = Text(sev_name, style=style)

        table.add_row(result.skill_name, "-", status, str(len(result.findings)), max_sev)

    console.print(table)
    _print_scan_summary(results)


def _print_scan_summary(results: list[AnalysisResult]) -> None:
    """Print a one-line summary after scan results table."""
    total = len(results)
    safe = sum(1 for r in results if r.is_safe)
    unsafe = total - safe
    total_findings = sum(len(r.findings) for r in results)
    parts = [f"[bold]{total}[/bold] skills scanned"]
    if safe > 0:
        parts.append(f"[green]{safe} safe[/green]")
    if unsafe > 0:
        parts.append(f"[red]{unsafe} unsafe[/red]")
    parts.append(f"{total_findings} total findings")
    console.print(" | ".join(parts))


def print_analysis_detail(result: AnalysisResult) -> None:
    """Print detailed analysis output for a single skill.

    Args:
        result: Analysis result for one skill.
    """
    if result.is_safe:
        verdict = Text("SAFE", style="bold green")
    else:
        verdict = Text("UNSAFE", style="bold red")

    header = Text.assemble(
        ("Skill: ", "bold"), (result.skill_name, ""),
        ("  Status: ", "bold"), verdict,
    )
    console.print(Panel(header, title="Verification Result"))

    # Inferred capabilities
    if result.inferred_capabilities and len(result.inferred_capabilities) > 0:
        cap_table = Table(title="Inferred Capabilities", show_header=True)
        cap_table.add_column("Resource", style="bold")
        cap_table.add_column("Access Level")
        for cap in result.inferred_capabilities:
            cap_table.add_row(cap.resource, cap.access.name)
        console.print(cap_table)

    # Findings
    if result.findings:
        findings_table = Table(title="Findings", show_header=True)
        findings_table.add_column("Severity", justify="center")
        findings_table.add_column("Type")
        findings_table.add_column("Message")
        findings_table.add_column("Evidence", style="dim")
        for f in result.findings:
            style = severity_style(f.severity)
            findings_table.add_row(
                Text(f.severity.name, style=style), f.finding_type,
                f.message, f.evidence[:80],
            )
        console.print(findings_table)
    else:
        console.print("[green]No findings. Skill passed all checks.[/green]")


def print_trust_score(score: TrustScore) -> None:
    """Print a formatted trust score breakdown.

    Args:
        score: Computed trust score for a skill.
    """
    level_style = trust_level_style(score.level)
    level_text = Text(score.level.name, style=level_style)

    header = Text.assemble(
        ("Skill: ", "bold"), (score.skill_name, ""),
        ("  Version: ", "bold"), (score.version, "dim"),
    )
    console.print(Panel(header, title="Trust Score"))
    console.print(f"  Intrinsic Score: [bold]{score.intrinsic_score:.3f}[/bold]")
    console.print(f"  Effective Score: [bold]{score.effective_score:.3f}[/bold]")
    console.print("  Trust Level:     ", level_text)

    sig_table = Table(title="Signal Breakdown", show_header=True)
    sig_table.add_column("Signal", style="bold")
    sig_table.add_column("Value", justify="right")
    for name, value in score.signals.as_dict().items():
        sig_table.add_row(name.capitalize(), f"{value:.3f}")
    console.print(sig_table)


def print_resolution_summary(
    success: bool,
    installed: dict[str, str],
    conflicts: list[str],
) -> None:
    """Print dependency resolution results.

    Args:
        success: Whether resolution succeeded.
        installed: Skill-name to version mapping (if success).
        conflicts: Conflict descriptions (if failure).
    """
    if success:
        console.print(
            Panel("[bold green]Resolution successful[/bold green]",
                  title="Dependency Resolution")
        )
        if installed:
            table = Table(show_header=True)
            table.add_column("Skill", style="bold")
            table.add_column("Resolved Version")
            for name in sorted(installed):
                table.add_row(name, installed[name])
            console.print(table)
        else:
            console.print("[dim]No skills to resolve.[/dim]")
    else:
        console.print(
            Panel("[bold red]Resolution failed[/bold red]",
                  title="Dependency Resolution")
        )
        for conflict in conflicts:
            console.print(f"  [red]- {conflict}[/red]")


def print_sbom_summary(summary: dict[str, Any]) -> None:
    """Print a summary of the generated ASBOM.

    Args:
        summary: Dictionary from ``ASBOMGenerator.summary()``.
    """
    console.print(
        Panel("[bold]Agent Skill Bill of Materials (ASBOM)[/bold]",
              title="SBOM Summary")
    )
    console.print(f"  Total skills:  [bold]{summary.get('total', 0)}[/bold]")
    console.print(f"  Safe:          [green]{summary.get('safe', 0)}[/green]")
    console.print(f"  Unsafe:        [red]{summary.get('unsafe', 0)}[/red]")
    console.print(f"  Total findings: {summary.get('total_findings', 0)}")

    formats = summary.get("formats", {})
    if formats:
        fmt_table = Table(title="Format Distribution", show_header=True)
        fmt_table.add_column("Format", style="bold")
        fmt_table.add_column("Count", justify="right")
        for fmt, count in sorted(formats.items()):
            fmt_table.add_row(fmt, str(count))
        console.print(fmt_table)

    trust_dist = summary.get("trust_distribution", {})
    if trust_dist:
        trust_table = Table(title="Trust Distribution", show_header=True)
        trust_table.add_column("Level", style="bold")
        trust_table.add_column("Count", justify="right")
        for level, count in sorted(trust_dist.items()):
            trust_table.add_row(level, str(count))
        console.print(trust_table)


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout.

    Args:
        data: Any JSON-serializable data structure.
    """
    console.print_json(json.dumps(data, default=str))
