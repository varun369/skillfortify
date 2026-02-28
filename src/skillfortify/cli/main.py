"""SkillFortify CLI — Formal verification for agent skill supply chains.

Entry point for the ``skillfortify`` command-line tool. Registers all
subcommands under a single Click group.

Commands:
    scan       — Discover and analyze skills (directory or system-wide).
    verify     — Formally verify a single skill file.
    lock       — Generate skill-lock.json for reproducible installs.
    trust      — Compute and display trust score for a skill.
    sbom       — Generate CycloneDX 1.6 Agent Skill Bill of Materials.
    frameworks — List all 22 supported agent frameworks.
    dashboard  — Generate an HTML security report.

Usage::

    skillfortify scan                           # Auto-discover all AI tools
    skillfortify scan --system                  # Explicit system-wide scan
    skillfortify scan ./my-agent-project        # Scan specific directory
    skillfortify verify ./skills/deploy.md
    skillfortify lock ./my-agent-project
    skillfortify trust ./skills/deploy.md
    skillfortify sbom ./my-agent-project
    skillfortify frameworks
    skillfortify dashboard                      # System-wide dashboard
    skillfortify dashboard ./my-agent-project   # Directory dashboard
"""

from __future__ import annotations

import click

from skillfortify import __version__, _PRODUCT_PROVENANCE
from skillfortify.cli.dashboard_cmd import dashboard_command
from skillfortify.cli.frameworks_cmd import frameworks_command
from skillfortify.cli.lock import lock_command
from skillfortify.cli.registry_cmd import registry_scan_command
from skillfortify.cli.sbom_cmd import sbom_command
from skillfortify.cli.scan import scan_command
from skillfortify.cli.trust_cmd import trust_command
from skillfortify.cli.verify import verify_command


@click.group()
@click.version_option(version=f"{__version__} ({_PRODUCT_PROVENANCE})")
def cli() -> None:
    """SkillFortify: Formal verification for agent skill supply chains.

    Analyze, verify, and secure agent skills across all 22 supported
    agent frameworks. Detect malicious patterns, enforce capability
    bounds, and generate supply chain documentation.
    """


# Register all subcommands
cli.add_command(scan_command)
cli.add_command(verify_command)
cli.add_command(lock_command)
cli.add_command(trust_command)
cli.add_command(sbom_command)
cli.add_command(frameworks_command)
cli.add_command(dashboard_command)
cli.add_command(registry_scan_command)
