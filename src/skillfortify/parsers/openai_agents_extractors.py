"""AST extraction helpers for the OpenAI Agents SDK parser.

Contains the AST traversal functions that pull security-relevant
metadata from Python files using the Agents SDK. Text extraction
utilities and the ``build_skill`` factory live in
``openai_agents_utils.py``.

Extracted entities:
- ``@function_tool`` decorated functions
- ``Agent(...)`` instantiations (name, instructions, handoffs, guardrails)
- Hosted tool imports (WebSearchTool, FileSearchTool, etc.)
- MCPServerStdio / MCPServerHTTP connections
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.openai_agents_utils import build_skill

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #

# Hosted tool class names exposed by the SDK.
HOSTED_TOOL_NAMES = frozenset({
    "WebSearchTool",
    "FileSearchTool",
    "CodeInterpreterTool",
    "ComputerTool",
})

# MCP server class names.
MCP_SERVER_NAMES = frozenset({
    "MCPServerStdio",
    "MCPServerHTTP",
    "MCPServerSse",
    "MCPServerStreamableHttp",
})


# --------------------------------------------------------------------------- #
# @function_tool extraction                                                    #
# --------------------------------------------------------------------------- #

def extract_function_tools(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract ``@function_tool`` decorated functions from *tree*."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_function_tool_decorator(node):
            continue
        name = node.name
        description = ast.get_docstring(node) or ""
        body_text = ast.get_source_segment(source, node) or ""
        results.append(build_skill(name, description, body_text, path, source))
    return results


def _has_function_tool_decorator(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Return True if *node* has a ``@function_tool`` decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "function_tool":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "function_tool":
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name) and func.id == "function_tool":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "function_tool":
                return True
    return False


# --------------------------------------------------------------------------- #
# Agent(...) extraction                                                        #
# --------------------------------------------------------------------------- #

def extract_agents(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract ``Agent(...)`` instantiations from *tree*."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_agent_call(node):
            continue
        info = _parse_agent_kwargs(node)
        if not info.get("name"):
            continue
        capabilities = _collect_agent_capabilities(node, info)
        body_text = ast.get_source_segment(source, node) or ""
        results.append(build_skill(
            name=info["name"],
            description=info.get("handoff_description", ""),
            body=body_text,
            path=path,
            source=source,
            capabilities=capabilities,
            instructions=info.get("instructions", ""),
        ))
    return results


def _is_agent_call(node: ast.Call) -> bool:
    """Return True if the Call node invokes ``Agent(...)``."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "Agent":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "Agent":
        return True
    return False


def _parse_agent_kwargs(node: ast.Call) -> dict[str, str]:
    """Extract string-valued keyword arguments from an Agent call."""
    info: dict[str, str] = {}
    for kw in node.keywords:
        if kw.arg and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                info[kw.arg] = kw.value.value
    return info


def _collect_agent_capabilities(
    node: ast.Call, info: dict[str, str],
) -> list[str]:
    """Derive capability strings from Agent keyword arguments."""
    caps: list[str] = []
    for kw in node.keywords:
        if kw.arg == "handoffs" and isinstance(kw.value, ast.List):
            caps.append("agent_handoff")
        if kw.arg == "mcp_servers":
            caps.append("mcp_access")
        if kw.arg == "input_guardrails":
            caps.append("input_guardrail")
        if kw.arg == "output_guardrails":
            caps.append("output_guardrail")
    if info.get("model"):
        caps.append(f"model:{info['model']}")
    return caps


# --------------------------------------------------------------------------- #
# Hosted tools extraction                                                      #
# --------------------------------------------------------------------------- #

def extract_hosted_tools(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Detect hosted tool imports (WebSearchTool, etc.)."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if not node.module:
            continue
        for alias in node.names:
            if alias.name in HOSTED_TOOL_NAMES:
                results.append(build_skill(
                    name=alias.name,
                    description=f"OpenAI hosted tool: {alias.name}",
                    body="",
                    path=path,
                    source=source,
                    capabilities=[f"hosted:{alias.name}"],
                ))
    return results


# --------------------------------------------------------------------------- #
# MCP server extraction                                                        #
# --------------------------------------------------------------------------- #

def extract_mcp_servers(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract MCPServerStdio/MCPServerHTTP instantiations."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        class_name = _get_call_name(node)
        if class_name not in MCP_SERVER_NAMES:
            continue
        info = _parse_mcp_kwargs(node)
        body_text = ast.get_source_segment(source, node) or ""
        name = info.get("command") or info.get("url") or class_name
        caps = [f"mcp:{class_name}"]
        results.append(build_skill(
            name=name,
            description=f"MCP server connection via {class_name}",
            body=body_text,
            path=path,
            source=source,
            capabilities=caps,
        ))
    return results


def _get_call_name(node: ast.Call) -> str:
    """Return the simple name of a Call node's function."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _parse_mcp_kwargs(node: ast.Call) -> dict[str, str]:
    """Extract relevant kwargs from MCPServer* instantiations."""
    info: dict[str, str] = {}
    for kw in node.keywords:
        if kw.arg == "command" and isinstance(kw.value, ast.Constant):
            info["command"] = str(kw.value.value)
        elif kw.arg == "url" and isinstance(kw.value, ast.Constant):
            info["url"] = str(kw.value.value)
    return info


# --------------------------------------------------------------------------- #
# Regex fallback                                                               #
# --------------------------------------------------------------------------- #

def regex_fallback(source: str, file_path: Path) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing."""
    results: list[ParsedSkill] = []
    for match in re.finditer(
        r"@function_tool\s*[\n(].*?def\s+(\w+)", source, re.DOTALL,
    ):
        results.append(
            build_skill(match.group(1), "", source, file_path, source),
        )
    return results
