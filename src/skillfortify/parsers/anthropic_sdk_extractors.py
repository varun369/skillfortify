"""AST extraction helpers for the Anthropic Agent SDK parser.

Extracts ``@tool`` functions, ``Agent(...)`` instantiations,
``MCPServer(...)`` connections, and ``Hook`` subclass definitions.
Also provides regex patterns and the ``build_skill`` factory.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill

FORMAT_NAME = "anthropic_sdk"

_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

_ENV_VAR_PATTERN = re.compile(
    r"""(?:"""
    r"""\$\{?([A-Z][A-Z0-9_]{1,})\}?"""
    r"""|os\.environ\[["']([A-Z][A-Z0-9_]{1,})["']\]"""
    r"""|os\.getenv\(["']([A-Z][A-Z0-9_]{1,})["']\)"""
    r""")""",
    re.MULTILINE,
)

_SHELL_CALL_PATTERN = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))"
    r"""\s*\(\s*["']([^"']+)["']""",
)


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from *text*."""
    return _URL_PATTERN.findall(text)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from *text*."""
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def _extract_shell_commands(text: str) -> list[str]:
    """Extract shell command strings from subprocess/os calls."""
    return _SHELL_CALL_PATTERN.findall(text)


def _extract_imports(text: str) -> list[str]:
    """Extract top-level import package names via AST with regex fallback."""
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                parts = stripped.split()
                if len(parts) >= 2:
                    imports.append(parts[1].split(".")[0])
        return sorted(set(imports))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])
    return sorted(set(imports))


def _build_skill(
    name: str,
    description: str,
    body: str,
    path: Path,
    source: str,
    *,
    capabilities: list[str] | None = None,
    instructions: str = "",
) -> ParsedSkill:
    """Construct a ``ParsedSkill`` from extracted Anthropic SDK metadata."""
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=path,
        format=FORMAT_NAME,
        description=description,
        instructions=instructions,
        declared_capabilities=capabilities or [],
        code_blocks=[body] if body else [],
        urls=_extract_urls(body),
        env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source),
        raw_content=source,
    )


def _has_tool_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if *node* has a ``@tool`` decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "tool":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "tool":
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name) and func.id == "tool":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "tool":
                return True
    return False


def extract_tools(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract ``@tool`` decorated functions from *tree*."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_tool_decorator(node):
            continue
        name = node.name
        description = ast.get_docstring(node) or ""
        body_text = ast.get_source_segment(source, node) or ""
        results.append(_build_skill(name, description, body_text, path, source))
    return results


def _is_agent_call(node: ast.Call) -> bool:
    """Return True if the Call node invokes ``Agent(...)``."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "Agent":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "Agent":
        return True
    return False


def _get_kwarg_str(call: ast.Call, key: str) -> str:
    """Extract a string keyword argument value from an ast.Call node."""
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                return kw.value.value
    return ""


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
        name = _get_kwarg_str(node, "name")
        if not name:
            continue
        model = _get_kwarg_str(node, "model")
        instructions = _get_kwarg_str(node, "instructions")
        caps: list[str] = []
        if model:
            caps.append(f"model:{model}")
        for kw in node.keywords:
            if kw.arg == "hooks":
                caps.append("lifecycle_hooks")
            if kw.arg == "tools" and isinstance(kw.value, ast.List):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Name):
                        caps.append(f"tool:{elt.id}")
        body_text = ast.get_source_segment(source, node) or ""
        results.append(_build_skill(
            name=name,
            description=instructions or f"Anthropic SDK agent (model={model})",
            body=body_text,
            path=path,
            source=source,
            capabilities=caps,
            instructions=instructions,
        ))
    return results


def _is_mcp_server_call(node: ast.Call) -> bool:
    """Return True if the Call node invokes ``MCPServer(...)``."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "MCPServer":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "MCPServer":
        return True
    return False


def extract_mcp_servers(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract ``MCPServer(...)`` instantiations from *tree*."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_mcp_server_call(node):
            continue
        command = _get_kwarg_str(node, "command")
        body_text = ast.get_source_segment(source, node) or ""
        name = command or "MCPServer"
        caps = [f"mcp:{command}"] if command else ["mcp:unknown"]
        results.append(_build_skill(
            name=name,
            description=f"MCP server connection via MCPServer (command={command})",
            body=body_text,
            path=path,
            source=source,
            capabilities=caps,
        ))
    return results


def extract_hooks(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract ``Hook`` subclass definitions from *tree*."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            (isinstance(b, ast.Name) and b.id == "Hook")
            or (isinstance(b, ast.Attribute) and b.attr == "Hook")
            for b in node.bases
        ):
            continue
        name = node.name
        description = ast.get_docstring(node) or ""
        methods = [
            n.name for n in ast.walk(node)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name != "__init__"
        ]
        caps = [f"hook:{m}" for m in methods]
        body_text = ast.get_source_segment(source, node) or ""
        results.append(_build_skill(
            name=name,
            description=description,
            body=body_text,
            path=path,
            source=source,
            capabilities=caps,
        ))
    return results


def regex_fallback(source: str, file_path: Path) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing."""
    results: list[ParsedSkill] = []
    for match in re.finditer(r"@tool\s*[\n(].*?def\s+(\w+)", source, re.DOTALL):
        results.append(
            _build_skill(match.group(1), "", source, file_path, source),
        )
    return results
