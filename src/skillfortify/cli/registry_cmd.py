"""``skillfortify registry-scan`` — Scan remote agent skill registries.

Supports three registries:
    mcp  — Official MCP server registry
    pypi — PyPI agent-tool packages
    npm  — npm agent-tool packages

Usage::

    skillfortify registry-scan mcp --limit 50
    skillfortify registry-scan pypi --keyword "mcp-server" --limit 20
    skillfortify registry-scan npm --keyword "@modelcontextprotocol"
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from skillfortify.registry.base import RegistryScanner


def _run_async(coro: object) -> object:
    """Run an async coroutine in a synchronous context.

    Args:
        coro: Awaitable coroutine to execute.

    Returns:
        The coroutine's return value.
    """
    return asyncio.run(coro)  # type: ignore[arg-type]


def _get_scanner(registry: str) -> RegistryScanner:
    """Create the appropriate scanner for a registry name.

    Args:
        registry: One of "mcp", "pypi", "npm".

    Returns:
        A RegistryScanner instance.

    Raises:
        SystemExit: If httpx is not installed.
    """
    try:
        import httpx  # noqa: F401
    except ImportError:
        click.echo(
            "Error: httpx is required for registry scanning.\n"
            "Install it with: pip install skillfortify[registry]",
            err=True,
        )
        sys.exit(1)

    if registry == "mcp":
        from skillfortify.registry.mcp_registry import MCPRegistryScanner
        return MCPRegistryScanner()
    elif registry == "pypi":
        from skillfortify.registry.pypi_scanner import PyPIScanner
        return PyPIScanner()
    elif registry == "npm":
        from skillfortify.registry.npm_scanner import NpmScanner
        return NpmScanner()
    else:
        click.echo(f"Unknown registry: {registry}", err=True)
        sys.exit(1)


def _format_text_output(results: list, stats: object) -> None:
    """Print scan results in human-readable text format.

    Args:
        results: List of AnalysisResult objects.
        stats: RegistryStats object.
    """
    from skillfortify.cli.output import print_scan_results
    print_scan_results(results)
    click.echo(f"\nRegistry: {stats.registry_name}")  # type: ignore[attr-defined]
    click.echo(
        f"Total: {stats.total_entries} | "  # type: ignore[attr-defined]
        f"Scanned: {stats.scanned} | "  # type: ignore[attr-defined]
        f"Safe: {stats.safe} | "  # type: ignore[attr-defined]
        f"Unsafe: {stats.unsafe} | "  # type: ignore[attr-defined]
        f"Critical: {stats.critical_findings}"  # type: ignore[attr-defined]
    )


def _format_json_output(results: list, stats: object) -> None:
    """Print scan results as JSON.

    Args:
        results: List of AnalysisResult objects.
        stats: RegistryStats object.
    """
    from dataclasses import asdict
    output = {
        "stats": asdict(stats),  # type: ignore[arg-type]
        "results": [
            {
                "skill_name": r.skill_name,
                "is_safe": r.is_safe,
                "findings_count": len(r.findings),
                "findings": [
                    {
                        "severity": f.severity.name,
                        "message": f.message,
                        "attack_class": f.attack_class,
                        "evidence": f.evidence,
                    }
                    for f in r.findings
                ],
            }
            for r in results
        ],
    }
    click.echo(json.dumps(output, indent=2))


@click.command("registry-scan")
@click.argument("registry", type=click.Choice(["mcp", "pypi", "npm"]))
@click.option("--limit", default=50, type=int, help="Max entries to scan (default 50).")
@click.option("--keyword", default="", help="Search keyword to filter packages.")
@click.option(
    "--format", "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text).",
)
def registry_scan_command(
    registry: str,
    limit: int,
    keyword: str,
    output_format: str,
) -> None:
    """Scan a remote agent skill registry for supply chain risks.

    Supported registries: mcp, pypi, npm.

    Examples:

        skillfortify registry-scan mcp --limit 20

        skillfortify registry-scan pypi --keyword "mcp-server"

        skillfortify registry-scan npm --format json
    """
    scanner = _get_scanner(registry)
    results, stats = _run_async(
        scanner.scan_registry(limit=limit, keyword=keyword)
    )

    if output_format == "json":
        _format_json_output(results, stats)
    else:
        _format_text_output(results, stats)

    has_findings = any(not r.is_safe for r in results)
    sys.exit(1 if has_findings else 0)
