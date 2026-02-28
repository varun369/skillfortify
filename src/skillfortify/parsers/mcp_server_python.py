"""Python AST-based analysis helpers for MCP server deep scanning.

Extracts tool/resource/prompt definitions, environment variable references,
security capabilities, shell command invocations, and URLs from Python MCP
server source code using the ``ast`` module for reliable parsing.

This module is an internal helper for ``McpServerParser``.  All public
functions accept source code as a string and return extracted metadata.
"""

from __future__ import annotations

import ast
import re

# ── Constants ──────────────────────────────────────────────────────────────

_NETWORK_MODULES = frozenset({"httpx", "requests", "aiohttp", "urllib"})
_FS_MODULES = frozenset({"shutil"})

# Shell-execution function names used as detection strings (not invoked).
_SHELL_FUNCTION_NAMES = frozenset({
    "subprocess.run", "subprocess.Popen",
    "subprocess.call", "subprocess.check_output",
    "subprocess.check_call",
})

_SENSITIVE_ENV_PATTERNS = re.compile(
    r"(SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL|PRIVATE)", re.IGNORECASE
)

_URL_PATTERN = re.compile(r"https?://[^\s\"'`,)\]}>]+")

_PYTHON_MCP_IMPORT_PATTERNS = (
    re.compile(r"from\s+mcp\.server\s+import"),
    re.compile(r"from\s+mcp\s+import\s+Server"),
)


# ── AST utility functions ──────────────────────────────────────────────────

def _dotted_name(node: ast.expr) -> str:
    """Build a dotted name string from an AST attribute chain."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _decorator_name(node: ast.expr) -> str:
    """Return the leaf name of a decorator AST node."""
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_os_environ(node: ast.expr) -> bool:
    """Check whether *node* represents ``os.environ``."""
    return _dotted_name(node) == "os.environ"


# ── Public extraction functions ────────────────────────────────────────────

def has_python_mcp_import(content: str) -> bool:
    """Return True if content has a Python MCP SDK import."""
    return any(pat.search(content) for pat in _PYTHON_MCP_IMPORT_PATTERNS)


def extract_tools(source: str) -> list[str]:
    """Extract tool/resource/prompt function names from decorator calls.

    Args:
        source: Python source code string.

    Returns:
        List of function names decorated with tool/resource/prompt.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names: list[str] = []
    decorators_of_interest = {"tool", "resource", "prompt"}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if _decorator_name(dec) in decorators_of_interest:
                names.append(node.name)
    return names


def extract_env_vars(source: str) -> list[str]:
    """Find os.environ / os.getenv references via AST.

    Args:
        source: Python source code string.

    Returns:
        Sorted, deduplicated list of environment variable names.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    env_vars: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if _is_os_environ(node.value) and isinstance(node.slice, ast.Constant):
                env_vars.append(str(node.slice.value))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _dotted_name(node.func)
        if func_name in ("os.environ.get", "os.getenv") and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                env_vars.append(first_arg.value)
    return sorted(set(env_vars))


def extract_capabilities(source: str) -> list[str]:
    """Infer security capabilities from import statements and call sites.

    Args:
        source: Python source code string.

    Returns:
        Sorted list of capability strings (e.g. ``"network:read"``).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    caps: set[str] = set()
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])
    if imported_modules & _NETWORK_MODULES:
        caps.update(("network:read", "network:write"))
    if "subprocess" in imported_modules:
        caps.add("system:execute")
    if imported_modules & _FS_MODULES:
        caps.update(("filesystem:read", "filesystem:write"))
    if "os" in imported_modules:
        caps.add("env:read")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _dotted_name(node.func) == "open":
            caps.update(("filesystem:read", "filesystem:write"))
    return sorted(caps)


def extract_shell_commands(source: str) -> list[str]:
    """Find shell command invocations in Python source.

    Args:
        source: Python source code string.

    Returns:
        List of dotted function names that invoke shell commands.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    cmds: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = _dotted_name(node.func)
            if func_name in _SHELL_FUNCTION_NAMES:
                cmds.append(func_name)
    return cmds


def extract_urls(source: str) -> list[str]:
    """Find HTTP/HTTPS URL patterns in source code.

    Args:
        source: Python source code string.

    Returns:
        List of URL strings found.
    """
    return _URL_PATTERN.findall(source)


def has_sensitive_env_vars(env_vars: list[str]) -> bool:
    """Check if any env var name matches a sensitive pattern.

    Args:
        env_vars: List of environment variable names.

    Returns:
        True if any name contains SECRET, KEY, TOKEN, PASSWORD, etc.
    """
    return any(_SENSITIVE_ENV_PATTERNS.search(var) for var in env_vars)
