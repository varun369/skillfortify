"""Regex-based analysis helpers for TypeScript/JS MCP server scanning.

Since TypeScript and JavaScript files cannot be parsed by Python's ``ast``
module, this module uses regular expressions to extract security-relevant
metadata from MCP server source code written in TS/JS.

Extraction targets:
- Tool registrations (``server.tool("name", ...)``)
- ``process.env`` references
- URL patterns (HTTP/HTTPS)
- Shell execution (child_process, exec, spawn)
- Filesystem access (fs.* calls)
- Network operations (fetch, axios, http)

This module is an internal helper for ``McpServerParser``.
"""

from __future__ import annotations

import re

# ── Compiled patterns ──────────────────────────────────────────────────────

_TS_MCP_IMPORT_PATTERNS = (
    re.compile(
        r'''import\s+\{[^}]*Server[^}]*\}\s+from\s+["']@modelcontextprotocol/sdk'''
    ),
    re.compile(r'''require\s*\(\s*["']@modelcontextprotocol/sdk'''),
)

_TS_TOOL_PATTERN = re.compile(r"""\w+\.tool\s*\(\s*["']([^"']+)["']""")
_TS_ENV_PATTERN = re.compile(r"process\.env\.(\w+)")
_URL_PATTERN = re.compile(r"https?://[^\s\"'`,)\]}>]+")

_TS_EXEC_PATTERNS = (
    re.compile(r"\bchild_process\b"),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\bspawn\s*\("),
)
_TS_FS_PATTERN = re.compile(r"\bfs\.\w+")
_TS_NET_PATTERNS = (
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\baxios\b"),
    re.compile(r"\bhttp\.\w+"),
)

_SENSITIVE_ENV_PATTERNS = re.compile(
    r"(SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL|PRIVATE)", re.IGNORECASE
)


# ── Public functions ───────────────────────────────────────────────────────

def has_ts_mcp_import(content: str) -> bool:
    """Return True if content has a TS/JS MCP SDK import or require."""
    return any(pat.search(content) for pat in _TS_MCP_IMPORT_PATTERNS)


def analyse_typescript(source: str) -> dict:
    """Extract security metadata from TypeScript/JS MCP server source.

    Args:
        source: TypeScript or JavaScript source code string.

    Returns:
        Dictionary with keys: ``tools``, ``env_vars``, ``urls``,
        ``shell_cmds``, ``capabilities``.
    """
    tools = _TS_TOOL_PATTERN.findall(source)
    env_vars = _TS_ENV_PATTERN.findall(source)
    urls = _URL_PATTERN.findall(source)
    shell_cmds = [p.pattern for p in _TS_EXEC_PATTERNS if p.search(source)]

    caps: set[str] = set()
    if env_vars:
        caps.add("env:read")
    if any(p.search(source) for p in _TS_NET_PATTERNS):
        caps.update(("network:read", "network:write"))
    if _TS_FS_PATTERN.search(source):
        caps.update(("filesystem:read", "filesystem:write"))
    if shell_cmds:
        caps.add("system:execute")
    if any(_SENSITIVE_ENV_PATTERNS.search(var) for var in env_vars):
        caps.add("credentials:read")

    return {
        "tools": tools,
        "env_vars": sorted(set(env_vars)),
        "urls": urls,
        "shell_cmds": shell_cmds,
        "capabilities": sorted(caps),
    }
