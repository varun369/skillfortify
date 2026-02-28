"""Extraction helpers for Google ADK MCPToolset, OpenAPIToolset, and callbacks.

This module contains the specialised AST-walking extractors for advanced
Google ADK patterns: MCPToolset connections, OpenAPIToolset references,
FunctionTool wrappers, and callback hook definitions.

Separated from the main ``google_adk`` module to respect the 300-line cap
and single-responsibility principle.
"""

from __future__ import annotations

import ast
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.google_adk import (
    _ADK_BUILTIN_TOOLS,
    _ADK_CALLBACK_NAMES,
    _build_skill,
    _get_agent_tools,
    _get_kwarg_str,
    _is_agent_constructor,
)

# ---------------------------------------------------------------------------
# FunctionTool wrapper extraction
# ---------------------------------------------------------------------------


def _is_function_tool_call(call: ast.Call) -> bool:
    """Check if a Call node is FunctionTool(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "FunctionTool":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "FunctionTool":
        return True
    return False


def _get_function_tool_name(call: ast.Call) -> str:
    """Get the function name from FunctionTool(func_name)."""
    if call.args and isinstance(call.args[0], ast.Name):
        return call.args[0].id
    return ""


def extract_function_tools(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract plain Python functions referenced in Agent tools lists.

    Collects function names from Agent(tools=[...]) and FunctionTool()
    wrappers, then matches them to actual function definitions in the
    AST. Built-in tools and callback hooks are excluded.

    Args:
        source: Python source code to analyse.
        file_path: Path to the source file on disk.

    Returns:
        List of ParsedSkill instances for each function tool found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    referenced: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_agent_constructor(node):
            referenced.update(_get_agent_tools(node))
        if isinstance(node, ast.Call) and _is_function_tool_call(node):
            name = _get_function_tool_name(node)
            if name:
                referenced.add(name)

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in referenced:
            continue
        if node.name in _ADK_BUILTIN_TOOLS:
            continue
        if node.name in _ADK_CALLBACK_NAMES:
            continue
        desc = ast.get_docstring(node) or ""
        body = ast.get_source_segment(source, node) or ""
        results.append(
            _build_skill(node.name, desc, body, file_path, source),
        )
    return results


# ---------------------------------------------------------------------------
# MCPToolset extraction
# ---------------------------------------------------------------------------


def _is_mcp_toolset_call(call: ast.Call) -> bool:
    """Check if a Call node is MCPToolset(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "MCPToolset":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "MCPToolset":
        return True
    return False


def _extract_stdio_params(call: ast.Call) -> list[str]:
    """Extract command/args from connection_params inside MCPToolset.

    Handles both keyword-argument style (StdioServerParameters(command=...))
    and dict-literal style ({"command": ..., "args": [...]}).
    """
    params: list[str] = []
    for node in ast.walk(call):
        if isinstance(node, ast.keyword) and node.arg in ("command", "args"):
            _collect_constant_values(node.value, params)
        elif isinstance(node, ast.Dict):
            _collect_dict_params(node, params)
    return params


def _collect_constant_values(node: ast.expr, out: list[str]) -> None:
    """Append constant string values from a node or list node."""
    if isinstance(node, ast.Constant):
        out.append(str(node.value))
    elif isinstance(node, ast.List):
        for elt in node.elts:
            if isinstance(elt, ast.Constant):
                out.append(str(elt.value))


def _collect_dict_params(dict_node: ast.Dict, out: list[str]) -> None:
    """Extract 'command' and 'args' values from a dict literal."""
    for key, value in zip(dict_node.keys, dict_node.values):
        if not isinstance(key, ast.Constant):
            continue
        if key.value in ("command", "args"):
            _collect_constant_values(value, out)


def extract_mcp_toolsets(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract MCPToolset connection parameters from source.

    Args:
        source: Python source code to analyse.
        file_path: Path to the source file on disk.

    Returns:
        List of ParsedSkill instances for each MCPToolset found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_mcp_toolset_call(node):
            continue
        body = ast.get_source_segment(source, node) or ""
        cmd_args = _extract_stdio_params(node)
        caps = [f"mcp:{arg}" for arg in cmd_args if arg]
        results.append(_build_skill(
            name="MCPToolset",
            description=f"MCP connection: {' '.join(cmd_args)}",
            body=body,
            path=file_path,
            source=source,
            capabilities=caps,
        ))
    return results


# ---------------------------------------------------------------------------
# OpenAPIToolset extraction
# ---------------------------------------------------------------------------


def _is_openapi_toolset_call(call: ast.Call) -> bool:
    """Check if a Call node is OpenAPIToolset(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "OpenAPIToolset":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "OpenAPIToolset":
        return True
    return False


def extract_openapi_toolsets(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract OpenAPIToolset references from source.

    Args:
        source: Python source code to analyse.
        file_path: Path to the source file on disk.

    Returns:
        List of ParsedSkill instances for each OpenAPIToolset found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_openapi_toolset_call(node):
            continue
        body = ast.get_source_segment(source, node) or ""
        spec_type = _get_kwarg_str(node, "spec_str_type") or "unknown"
        results.append(_build_skill(
            name="OpenAPIToolset",
            description=f"OpenAPI toolset (spec_type={spec_type})",
            body=body,
            path=file_path,
            source=source,
            capabilities=["openapi:external_api"],
        ))
    return results


# ---------------------------------------------------------------------------
# Callback extraction
# ---------------------------------------------------------------------------


def extract_callbacks(source: str) -> list[str]:
    """Extract callback function names from ADK agent source.

    Args:
        source: Python source code to analyse.

    Returns:
        List of callback function names found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    callbacks: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name in _ADK_CALLBACK_NAMES:
                callbacks.append(node.name)
        if isinstance(node, ast.keyword):
            if node.arg in _ADK_CALLBACK_NAMES:
                callbacks.append(node.arg)
    return callbacks
