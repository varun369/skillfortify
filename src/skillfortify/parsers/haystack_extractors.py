"""AST extraction helpers for Haystack tool and pipeline definitions.

This module contains the AST-walking extractors for Haystack patterns:
Tool/create_tool_from_function wrappers, Pipeline.add_component() calls,
component capability mapping, and regex fallbacks for malformed source.

Separated from the main ``haystack_tools`` module to respect the 300-line
cap and single-responsibility principle.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.haystack_tools import (
    _build_skill,
    _get_kwarg_str,
)

# ---------------------------------------------------------------------------
# Tool detection helpers
# ---------------------------------------------------------------------------


def _is_create_tool_call(call: ast.Call) -> bool:
    """Check if a Call node is create_tool_from_function(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "create_tool_from_function":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "create_tool_from_function":
        return True
    return False


def _is_tool_constructor(call: ast.Call) -> bool:
    """Check if a Call node is Tool(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "Tool":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "Tool":
        return True
    return False


def _get_tool_function_name(call: ast.Call) -> str:
    """Get the function name from create_tool_from_function(fn) or Tool(function=fn)."""
    if _is_create_tool_call(call) and call.args:
        if isinstance(call.args[0], ast.Name):
            return call.args[0].id
    for kw in call.keywords:
        if kw.arg == "function" and isinstance(kw.value, ast.Name):
            return kw.value.id
    return ""


# ---------------------------------------------------------------------------
# Tool extraction
# ---------------------------------------------------------------------------


def extract_tool_definitions(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract Tool() and create_tool_from_function() calls from AST.

    For each tool call, finds the referenced function definition and
    extracts its docstring and body as security-relevant metadata.

    Args:
        source: Python source code to analyse.
        file_path: Path to the source file on disk.

    Returns:
        List of ParsedSkill instances for each Haystack tool found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback_tools(source, file_path)

    referenced_funcs: set[str] = set()
    tool_names: dict[str, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_create_tool_call(node) or _is_tool_constructor(node):
            fn_name = _get_tool_function_name(node)
            if fn_name:
                referenced_funcs.add(fn_name)
            tool_name = _get_kwarg_str(node, "name") or fn_name
            if fn_name:
                tool_names[fn_name] = tool_name

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in referenced_funcs:
            continue
        desc = ast.get_docstring(node) or ""
        body = ast.get_source_segment(source, node) or ""
        display_name = tool_names.get(node.name, node.name)
        results.append(
            _build_skill(display_name, desc, body, file_path, source),
        )
    return results


def _regex_fallback_tools(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Regex fallback for tool definitions in unparseable source."""
    results: list[ParsedSkill] = []
    pattern = re.compile(
        r"""create_tool_from_function\s*\(\s*(\w+)\s*\)""",
    )
    for match in pattern.finditer(source):
        results.append(
            _build_skill(match.group(1), "", source, file_path, source),
        )
    return results


# ---------------------------------------------------------------------------
# Pipeline component extraction
# ---------------------------------------------------------------------------


def _is_add_component_call(call: ast.Call) -> bool:
    """Check if a Call node is *.add_component(...)."""
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr == "add_component"


def _parse_add_component(call: ast.Call) -> tuple[str, str]:
    """Extract (component_name, component_type) from add_component(name, Cls(...))."""
    comp_name = ""
    comp_type = ""
    if call.args and isinstance(call.args[0], ast.Constant):
        comp_name = str(call.args[0].value)
    if len(call.args) >= 2:
        comp_type = _get_call_name(call.args[1])
    return comp_name, comp_type


def _get_call_name(node: ast.expr) -> str:
    """Extract the callable name from an expression node."""
    if isinstance(node, ast.Call):
        return _get_call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _component_capabilities(comp_type: str) -> list[str]:
    """Map Haystack component types to capability strings."""
    caps: list[str] = []
    lower = comp_type.lower()
    if "generator" in lower:
        caps.append("llm:generate")
    if "openapi" in lower or "connector" in lower:
        caps.append("network:external_api")
    if "tool" in lower:
        caps.append("tool:invoke")
    if "retriever" in lower:
        caps.append("data:retrieve")
    if "converter" in lower:
        caps.append("data:convert")
    return caps


def extract_pipeline_components(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract pipeline add_component() calls from AST.

    Detects generator, connector, and converter components added to
    Haystack pipelines via pipe.add_component("name", ComponentClass(...)).

    Args:
        source: Python source code to analyse.
        file_path: Path to the source file on disk.

    Returns:
        List of ParsedSkill instances for each pipeline component found.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_add_component_call(node):
            continue
        comp_name, comp_type = _parse_add_component(node)
        if not comp_name:
            continue
        body = ast.get_source_segment(source, node) or ""
        caps = _component_capabilities(comp_type)
        results.append(
            _build_skill(comp_name, f"Haystack component: {comp_type}",
                         body, file_path, source, caps),
        )
    return results
