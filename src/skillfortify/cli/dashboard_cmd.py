"""``skillfortify dashboard [path]`` -- Generate an HTML security report.

Discovers all skills in the target directory (or system-wide with
``--system``), runs static analysis, and produces a self-contained HTML
dashboard. Optionally opens the report in the default browser.

Exit Codes:
    0 -- Report generated successfully.
    2 -- No skills found in the target path or on the system.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import click

from skillfortify.core.analyzer import StaticAnalyzer
from skillfortify.dashboard.generator import DashboardGenerator
from skillfortify.parsers.registry import default_registry

_DEFAULT_OUTPUT = "skillfortify-report.html"


def _run_directory_dashboard(
    path: str,
    output: str | None,
    title: str,
    open_browser: bool,
) -> None:
    """Generate dashboard from a specific directory scan.

    Args:
        path: Filesystem path to scan.
        output: Output HTML file path override.
        title: Report title.
        open_browser: Whether to open the report in a browser.
    """
    target = Path(path)
    registry = default_registry()
    skills = registry.discover(target)

    if not skills:
        click.echo("No skills found in the target directory.")
        sys.exit(2)

    analyzer = StaticAnalyzer()
    results = [analyzer.analyze(skill) for skill in skills]

    out_path = Path(output) if output else target / _DEFAULT_OUTPUT
    _write_dashboard(out_path, title, results, skills, open_browser)


def _run_system_dashboard(
    output: str | None,
    title: str,
    open_browser: bool,
) -> None:
    """Generate dashboard from a system-wide auto-discovery scan.

    Args:
        output: Output HTML file path override.
        title: Report title.
        open_browser: Whether to open the report in a browser.
    """
    from skillfortify.discovery import SystemScanner

    scanner = SystemScanner()
    result = scanner.scan_system()

    if not result.skills:
        click.echo("No skills found across any AI tools on this system.")
        sys.exit(2)

    out_path = Path(output) if output else Path.cwd() / _DEFAULT_OUTPUT
    _write_dashboard(
        out_path, title, result.results, result.skills, open_browser,
    )


def _write_dashboard(
    out_path: Path,
    title: str,
    results: list,
    skills: list,
    open_browser: bool,
) -> None:
    """Write the HTML dashboard and print summary.

    Args:
        out_path: Path to write the HTML file.
        title: Report title.
        results: Analysis results list.
        skills: Parsed skills list.
        open_browser: Whether to open the report in a browser.
    """
    generator = DashboardGenerator(title=title)
    resolved = generator.write(out_path, results=results, skills=skills)

    safe = sum(1 for r in results if r.is_safe)
    unsafe = len(results) - safe

    click.echo(f"Dashboard generated: {resolved}")
    click.echo(f"  Skills: {len(results)} ({safe} safe, {unsafe} unsafe)")

    if open_browser:
        webbrowser.open(resolved.as_uri())


@click.command("dashboard")
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
    "--output", "-o",
    type=click.Path(),
    default=None,
    help=f"Output HTML file path (default: {_DEFAULT_OUTPUT}).",
)
@click.option(
    "--title", "-t",
    type=str,
    default="SkillFortify Security Report",
    help="Report title shown in the HTML header.",
)
@click.option(
    "--open", "open_browser",
    is_flag=True,
    default=False,
    help="Open the report in the default browser after generation.",
)
def dashboard_command(
    path: str | None,
    system: bool,
    output: str | None,
    title: str,
    open_browser: bool,
) -> None:
    """Generate an HTML security dashboard for agent skills.

    When PATH is provided, scans that specific directory. When omitted or
    when --system is passed, auto-discovers all AI tools on the system
    and generates a unified report.
    """
    if path is None or system:
        _run_system_dashboard(output, title, open_browser)
    else:
        _run_directory_dashboard(path, output, title, open_browser)
