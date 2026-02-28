"""Deep scanner for MCP (Model Context Protocol) server source code.

Unlike ``McpConfigParser`` which analyses JSON configuration files, this
parser inspects the **actual server implementation** (Python / TypeScript / JS)
to extract security-relevant metadata:

- Tool, resource, and prompt definitions
- Environment variable access (especially sensitive ones)
- Shell command execution (subprocess, child_process)
- Network operations (httpx, requests, fetch)
- File system operations (open, pathlib, shutil)

Detection heuristics:
    Python  -- ``from mcp.server import Server`` or ``from mcp import Server``
    TS / JS -- ``import { Server } from "@modelcontextprotocol/sdk"``
    package.json -- ``@modelcontextprotocol/sdk`` in dependencies
    pyproject.toml -- ``mcp`` in project dependencies

Security Relevance:
    MCP servers execute with the host's full privileges.  A malicious or
    overprivileged server can exfiltrate data, run shell commands, or read
    credentials.  This parser surfaces those capabilities so the static
    analyser can flag them.

References:
    CVE-2026-25253: RCE via malicious MCP server configuration.
    ClawHavoc (Feb 2026): 1,200+ malicious skills infiltrated marketplace.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.mcp_server_python import (
    extract_capabilities,
    extract_env_vars,
    extract_shell_commands,
    extract_tools,
    extract_urls,
    has_python_mcp_import,
    has_sensitive_env_vars,
)
from skillfortify.parsers.mcp_server_ts import (
    analyse_typescript,
    has_ts_mcp_import,
)

# ── Constants ──────────────────────────────────────────────────────────────

_MCP_SERVER_FILENAMES = ("server.py", "main.py", "index.ts", "index.js")


# ── Main parser class ─────────────────────────────────────────────────────

class McpServerParser(SkillParser):
    """Deep scanner for MCP server source code implementations.

    Analyses Python files via AST and TypeScript/JS via regex to extract
    tool definitions, capabilities, env vars, URLs, and shell commands.
    """

    def can_parse(self, path: Path) -> bool:
        """Detect MCP server source code in a directory.

        Args:
            path: Root directory to probe.

        Returns:
            True if MCP server source files or dependency manifests found.
        """
        if not path.is_dir():
            return False
        for filename in _MCP_SERVER_FILENAMES:
            candidate = path / filename
            if candidate.is_file() and _file_has_mcp_import(candidate):
                return True
        if _package_json_has_mcp(path):
            return True
        if _pyproject_has_mcp(path):
            return True
        return False

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all MCP server source files in the directory.

        Args:
            path: Root directory to scan.

        Returns:
            List of ParsedSkill instances with format ``"mcp_server"``.
        """
        if not path.is_dir():
            return []
        results: list[ParsedSkill] = []
        for child in sorted(path.iterdir()):
            if child.suffix == ".py" and _file_has_mcp_import(child):
                results.extend(_parse_python_server(child))
            elif child.suffix in (".ts", ".js") and _file_has_mcp_import(child):
                results.extend(_parse_ts_server(child))
        return results


# ── File-level detection helpers ───────────────────────────────────────────

def _file_has_mcp_import(filepath: Path) -> bool:
    """Check if a file contains MCP SDK import statements."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    if filepath.suffix == ".py":
        return has_python_mcp_import(content)
    if filepath.suffix in (".ts", ".js"):
        return has_ts_mcp_import(content)
    return False


def _package_json_has_mcp(directory: Path) -> bool:
    """Check if package.json lists the MCP SDK as a dependency."""
    pkg_path = directory / "package.json"
    if not pkg_path.is_file():
        return False
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    for dep_key in ("dependencies", "devDependencies"):
        deps = data.get(dep_key, {})
        if isinstance(deps, dict) and "@modelcontextprotocol/sdk" in deps:
            return True
    return False


def _pyproject_has_mcp(directory: Path) -> bool:
    """Check if pyproject.toml lists ``mcp`` as a dependency."""
    pyproject = directory / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(re.search(r'["\']mcp[>=<~!\s"\']', content))


# ── Per-file parse functions ───────────────────────────────────────────────

def _parse_python_server(filepath: Path) -> list[ParsedSkill]:
    """Parse a single Python MCP server file into ParsedSkill(s)."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError:
        return []
    tools = extract_tools(source)
    env_vars = extract_env_vars(source)
    caps = extract_capabilities(source)
    urls = extract_urls(source)
    shell_cmds = extract_shell_commands(source)
    if has_sensitive_env_vars(env_vars) and "credentials:read" not in caps:
        caps = sorted(set(caps) | {"credentials:read"})
    name = filepath.stem
    description = f"MCP server ({len(tools)} tools): {', '.join(tools[:5])}"
    return [ParsedSkill(
        name=name,
        version="unknown",
        source_path=filepath,
        format="mcp_server",
        description=description,
        declared_capabilities=caps,
        env_vars_referenced=env_vars,
        urls=urls,
        shell_commands=shell_cmds,
        code_blocks=[source],
        raw_content=source,
    )]


def _parse_ts_server(filepath: Path) -> list[ParsedSkill]:
    """Parse a single TypeScript/JS MCP server file into ParsedSkill(s)."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError:
        return []
    info = analyse_typescript(source)
    name = filepath.stem
    tools = info["tools"]
    description = f"MCP server ({len(tools)} tools): {', '.join(tools[:5])}"
    return [ParsedSkill(
        name=name,
        version="unknown",
        source_path=filepath,
        format="mcp_server",
        description=description,
        declared_capabilities=info["capabilities"],
        env_vars_referenced=info["env_vars"],
        urls=info["urls"],
        shell_commands=info["shell_cmds"],
        code_blocks=[source],
        raw_content=source,
    )]
