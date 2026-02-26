"""SkillFortify CLI — Formal verification for agent skill supply chains.

Entry point for the ``skillfortify`` command-line tool. Registers all
subcommands under a single Click group.

Commands:
    scan    — Discover and analyze all skills in a directory.
    verify  — Formally verify a single skill file.
    lock    — Generate skill-lock.json for reproducible installs.
    trust   — Compute and display trust score for a skill.
    sbom    — Generate CycloneDX 1.6 Agent Skill Bill of Materials.

Usage::

    skillfortify scan ./my-agent-project
    skillfortify verify ./my-agent-project/.claude/skills/deploy.md
    skillfortify lock ./my-agent-project
    skillfortify trust ./my-agent-project/.claude/skills/deploy.md
    skillfortify sbom ./my-agent-project
"""

from __future__ import annotations

import click

from skillfortify import __version__, _PRODUCT_PROVENANCE
from skillfortify.cli.lock import lock_command
from skillfortify.cli.sbom_cmd import sbom_command
from skillfortify.cli.scan import scan_command
from skillfortify.cli.trust_cmd import trust_command
from skillfortify.cli.verify import verify_command


@click.group()
@click.version_option(version=f"{__version__} ({_PRODUCT_PROVENANCE})")
def cli() -> None:
    """SkillFortify: Formal verification for agent skill supply chains.

    Analyze, verify, and secure agent skills across Claude Code, MCP,
    and OpenClaw formats. Detect malicious patterns, enforce capability
    bounds, and generate supply chain documentation.
    """


# Register all subcommands
cli.add_command(scan_command)
cli.add_command(verify_command)
cli.add_command(lock_command)
cli.add_command(trust_command)
cli.add_command(sbom_command)
