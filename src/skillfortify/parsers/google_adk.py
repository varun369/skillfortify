"""Parser for Google ADK (Agent Development Kit) tool definitions.

Extracts security metadata from Python files using Google ADK: Agent
constructors, FunctionTool wrappers, built-in tools, MCPToolset,
OpenAPIToolset, sub-agent references, and callback hooks.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

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

_ADK_IMPORT_MARKERS = (
    "from google.adk",
    "import google.adk",
    "from google import adk",
)

_ADK_BUILTIN_TOOLS = frozenset({
    "google_search",
    "code_execution",
    "built_in_code_execution",
})

_ADK_CALLBACK_NAMES = frozenset({
    "before_tool_callback",
    "after_tool_callback",
    "before_model_callback",
    "after_model_callback",
    "before_agent_callback",
    "after_agent_callback",
})

FORMAT_NAME = "google_adk"



def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text."""
    return _URL_PATTERN.findall(text)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from text."""
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def _extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from subprocess/os calls in source."""
    return _SHELL_CALL_PATTERN.findall(text)


def _extract_imports(text: str) -> list[str]:
    """Extract top-level import package names via AST, regex fallback."""
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
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return sorted(set(imports))


def _has_adk_imports(text: str) -> bool:
    """Check if text contains Google ADK import statements."""
    return any(marker in text for marker in _ADK_IMPORT_MARKERS)


def _build_skill(
    name: str,
    description: str,
    body: str,
    path: Path,
    source: str,
    capabilities: list[str] | None = None,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted Google ADK metadata."""
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=path,
        format=FORMAT_NAME,
        description=description,
        declared_capabilities=capabilities or [],
        code_blocks=[body] if body else [],
        urls=_extract_urls(body),
        env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source),
        raw_content=source,
    )



def _is_agent_constructor(call: ast.Call) -> bool:
    """Check if a Call node is google.adk.Agent(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "Agent":
        return True
    if isinstance(func, ast.Attribute) and func.attr == "Agent":
        return True
    return False


def _get_kwarg_str(call: ast.Call, key: str) -> str:
    """Extract a string keyword argument from an ast.Call node."""
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""


def _get_agent_tools(call: ast.Call) -> list[str]:
    """Extract tool names from the tools=[...] keyword of Agent()."""
    for kw in call.keywords:
        if kw.arg != "tools":
            continue
        if isinstance(kw.value, ast.List):
            return _extract_list_element_names(kw.value)
    return []


def _extract_list_element_names(lst: ast.List) -> list[str]:
    """Extract string identifiers from a list of AST elements."""
    names: list[str] = []
    for elt in lst.elts:
        if isinstance(elt, ast.Name):
            names.append(elt.id)
        elif isinstance(elt, ast.Attribute):
            names.append(elt.attr)
        elif isinstance(elt, ast.Call):
            func = elt.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                names.append(func.attr)
    return names


def _tools_to_capabilities(tool_names: list[str]) -> list[str]:
    """Map tool references to declared capability strings."""
    capabilities: list[str] = []
    for tool_name in tool_names:
        if tool_name in _ADK_BUILTIN_TOOLS:
            capabilities.append(f"builtin:{tool_name}")
        else:
            capabilities.append(f"tool:{tool_name}")
    return capabilities



def _parse_agent_call(
    call: ast.Call, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Parse an Agent(...) call and extract metadata."""
    name = _get_kwarg_str(call, "name") or "unnamed_agent"
    instruction = _get_kwarg_str(call, "instruction") or ""
    model = _get_kwarg_str(call, "model") or ""
    description = instruction or f"Google ADK agent (model={model})"
    tools_list = _get_agent_tools(call)
    capabilities = _tools_to_capabilities(tools_list)
    body = ast.get_source_segment(source, call) or ""
    return _build_skill(name, description, body, file_path, source, capabilities)


def _extract_agent_definitions(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract Agent() constructor calls from Python AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback_agents(source, file_path)

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_agent_constructor(node):
            continue
        skill = _parse_agent_call(node, source, file_path)
        if skill is not None:
            results.append(skill)
    return results


def _regex_fallback_agents(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Regex fallback for Agent(...) definitions in unparseable source."""
    results: list[ParsedSkill] = []
    pattern = re.compile(
        r"""Agent\s*\([^)]*name\s*=\s*["'](\w+)["']""",
        re.DOTALL,
    )
    for match in pattern.finditer(source):
        results.append(
            _build_skill(match.group(1), "", source, file_path, source),
        )
    return results



class GoogleADKParser(SkillParser):
    """Parser for Google ADK agent and tool definitions."""

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains Google ADK definitions."""
        return bool(self._find_adk_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Google ADK tools and agents in the directory."""
        from skillfortify.parsers.google_adk_extractors import (
            extract_function_tools,
            extract_mcp_toolsets,
            extract_openapi_toolsets,
        )

        results: list[ParsedSkill] = []
        for py_file in self._find_adk_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(_extract_agent_definitions(source, py_file))
            results.extend(extract_function_tools(source, py_file))
            results.extend(extract_mcp_toolsets(source, py_file))
            results.extend(extract_openapi_toolsets(source, py_file))
        return results

    def _find_adk_files(self, path: Path) -> list[Path]:
        """Find Python files containing Google ADK definitions."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in ("tools", "agents", "adk_agents"):
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)

        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_adk_imports(head):
                    candidates.append(py_file)
        return candidates
