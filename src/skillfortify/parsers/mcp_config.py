"""Parser for MCP (Model Context Protocol) server configurations.

MCP servers are configured via JSON files in the project root. Three filename
conventions are supported:

- ``mcp.json`` -- Standard location used by Claude Code and other MCP clients.
- ``.mcp.json`` -- Hidden-file variant for projects that prefer dotfiles.
- ``claude_desktop_config.json`` -- Used by Claude Desktop application.

Each file contains an ``mcpServers`` top-level key whose value is a map of
server name to server configuration:

.. code-block:: json

    {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
          "env": { "NODE_ENV": "production" }
        }
      }
    }

Security Relevance
------------------
Each MCP server entry represents a skill with significant security surface:

- **command + args** -- Shell execution (EXECUTE phase attack surface).
  The command may invoke untrusted npm packages via ``npx -y``, which
  auto-installs without confirmation.
- **env** -- Environment variables often contain secrets (GITHUB_TOKEN,
  DATABASE_URL, API_KEY). These are captured as ``env_vars_referenced``.
- **npm packages in args** -- Transitive supply chain dependencies. Packages
  prefixed with ``@`` are scoped npm packages and are captured as
  ``dependencies``.

References:
    Model Context Protocol specification (2025): JSON configuration format
    for MCP server declarations.

    CVE-2026-25253: Remote code execution in OpenClaw via malicious MCP
    server configurations.
"""

from __future__ import annotations

import json
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

# MCP config filenames to probe, in priority order.
_MCP_CONFIG_FILENAMES = (
    "mcp.json",
    "mcp_servers.json",
    "mcp_settings.json",
    "mcp_config.json",
    ".mcp.json",
    "claude_desktop_config.json",
)

# Top-level keys that contain server maps across different MCP clients.
_MCP_SERVER_KEYS = ("mcpServers", "mcp", "servers")


def _extract_npm_packages(args: list[str]) -> list[str]:
    """Extract npm package references from command arguments.

    Looks for arguments that start with ``@`` (scoped packages) or contain
    a ``/`` (namespaced packages), which are strong signals for npm package
    names.

    Args:
        args: Command-line argument list from the MCP server config.

    Returns:
        List of probable npm package names.
    """
    packages: list[str] = []
    for arg in args:
        # Skip flags and non-package-like arguments.
        if arg.startswith("-") or arg.startswith("/"):
            continue
        # Scoped npm packages: @org/package-name
        if arg.startswith("@") and "/" in arg:
            packages.append(arg)
    return packages


class McpConfigParser(SkillParser):
    """Parser for MCP server configurations in JSON format.

    Discovery logic:
        1. Check for any of the known MCP config filenames in the root directory.
        2. If at least one exists and contains a non-empty ``mcpServers`` map,
           ``can_parse()`` returns True.

    Parse logic:
        1. Read and parse JSON from the config file.
        2. Iterate over ``mcpServers`` entries.
        3. For each server, extract command, args, env, and dependencies.
        4. Construct a ``ParsedSkill`` with format="mcp".
    """

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains an MCP server configuration.

        Args:
            path: Root directory to probe.

        Returns:
            True if a valid MCP config file with non-empty mcpServers exists.
        """
        for filename in _MCP_CONFIG_FILENAMES:
            config_file = path / filename
            if config_file.is_file():
                return True
        return False

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all MCP server entries from ALL configuration files.

        Scans every known config filename and aggregates servers from all
        files found. Deduplicates by server name so the same MCP server
        declared in multiple config files is only reported once.

        Args:
            path: Root directory containing MCP config file(s).

        Returns:
            List of ParsedSkill instances, one per unique MCP server.
            Empty if no config found or all configs are malformed.
        """
        results: list[ParsedSkill] = []
        seen_names: set[str] = set()
        for filename in _MCP_CONFIG_FILENAMES:
            config_file = path / filename
            if config_file.is_file():
                for skill in self._parse_config(config_file):
                    if skill.name not in seen_names:
                        seen_names.add(skill.name)
                        results.append(skill)
        return results

    def _parse_config(self, config_path: Path) -> list[ParsedSkill]:
        """Parse a single MCP configuration file.

        Args:
            config_path: Path to the JSON config file.

        Returns:
            List of ParsedSkill instances. Empty on parse error.
        """
        try:
            raw_content = config_path.read_text(encoding="utf-8")
            data = json.loads(raw_content)
        except (OSError, json.JSONDecodeError):
            return []

        servers: dict = {}
        for key in _MCP_SERVER_KEYS:
            candidate = data.get(key, {})
            if isinstance(candidate, dict) and candidate:
                servers.update(candidate)
        if not servers:
            return []

        results: list[ParsedSkill] = []
        for server_name, server_config in servers.items():
            skill = self._parse_server_entry(server_name, server_config, config_path)
            if skill is not None:
                results.append(skill)
        return results

    def _parse_server_entry(
        self,
        name: str,
        config: dict,
        config_path: Path,
    ) -> ParsedSkill | None:
        """Parse a single MCP server entry into a ParsedSkill.

        Args:
            name: Server name (the key in the mcpServers map).
            config: Server configuration dict (command, args, env).
            config_path: Path to the config file (for source_path).

        Returns:
            A ParsedSkill, or None if the entry is malformed.
        """
        if not isinstance(config, dict):
            return None

        command = config.get("command", "")
        args = config.get("args", [])
        env = config.get("env", {})

        if not isinstance(args, list):
            args = []
        if not isinstance(env, dict):
            env = {}

        # Build the full command line as a shell command.
        full_command = " ".join([command] + [str(a) for a in args])
        shell_commands = [full_command] if command else []

        # Extract env var names.
        env_vars = sorted(env.keys())

        # Extract npm package dependencies from args.
        dependencies = _extract_npm_packages([str(a) for a in args])

        # Description includes the command for quick identification.
        description = f"MCP server: {full_command}" if command else f"MCP server: {name}"

        return ParsedSkill(
            name=name,
            version="unknown",
            source_path=config_path,
            format="mcp",
            description=description,
            shell_commands=shell_commands,
            env_vars_referenced=env_vars,
            dependencies=dependencies,
            raw_content=json.dumps(config, indent=2),
        )
