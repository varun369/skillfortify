"""Parser for PydanticAI agent and tool definitions.

Extracts security metadata from Python files using PydanticAI: Agent
constructors, @agent.tool / @agent.tool_plain decorated functions, MCP
server connections, dependency types, URLs, env vars, and shell commands.

Detection: ``from pydantic_ai`` imports, ``pyproject.toml`` with
``pydantic-ai``, ``Agent(`` calls, ``@agent.tool`` decorators.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

FORMAT_NAME = "pydanticai"

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
_PYDANTICAI_IMPORT_MARKERS = ("from pydantic_ai", "import pydantic_ai")
_TOOL_DIR_NAMES = {"tools", "agents", "pydanticai_agents"}


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
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])
    return sorted(set(imports))


def _has_pydanticai_imports(text: str) -> bool:
    """Check if text contains PydanticAI import statements."""
    return any(marker in text for marker in _PYDANTICAI_IMPORT_MARKERS)


def _build_skill(
    name: str, description: str, body: str,
    path: Path, source: str, capabilities: list[str] | None = None,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted PydanticAI metadata."""
    return ParsedSkill(
        name=name, version="unknown", source_path=path,
        format=FORMAT_NAME, description=description,
        declared_capabilities=capabilities or [],
        code_blocks=[body] if body else [],
        urls=_extract_urls(body),
        env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source),
        raw_content=source,
    )


def _get_kwarg_str(call: ast.Call, key: str) -> str:
    """Extract a string keyword argument from an ast.Call node."""
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""


def _is_agent_tool_decorator(decorator: ast.expr) -> str | None:
    """Return 'tool' or 'tool_plain' if decorator matches, else None."""
    if isinstance(decorator, ast.Attribute):
        if decorator.attr in ("tool", "tool_plain"):
            return decorator.attr
    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
        if decorator.func.attr in ("tool", "tool_plain"):
            return decorator.func.attr
    return None


def _parse_tool_function(
    node: ast.FunctionDef, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Extract a ParsedSkill from an @agent.tool / @agent.tool_plain func."""
    tool_type: str | None = None
    for dec in node.decorator_list:
        tool_type = _is_agent_tool_decorator(dec)
        if tool_type is not None:
            break
    if tool_type is None:
        return None
    name = node.name
    description = ast.get_docstring(node) or ""
    body_text = ast.get_source_segment(source, node) or ""
    return _build_skill(name, description, body_text, file_path, source, [f"decorator:{tool_type}"])


def _is_agent_constructor(call: ast.Call) -> bool:
    """Check if a Call node is pydantic_ai.Agent(...)."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "Agent":
        return True
    return isinstance(func, ast.Attribute) and func.attr == "Agent"


def _parse_agent_call(
    call: ast.Call, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Parse an Agent(...) constructor call and extract metadata."""
    model = ""
    if call.args and isinstance(call.args[0], ast.Constant):
        model = str(call.args[0].value)
    if not model:
        model = _get_kwarg_str(call, "model")
    system_prompt = _get_kwarg_str(call, "system_prompt")
    deps_type = _get_kwarg_str(call, "deps_type")
    parts = []
    if system_prompt:
        parts.append(system_prompt)
    if model:
        parts.append(f"model={model}")
    if deps_type:
        parts.append(f"deps_type={deps_type}")
    description = "; ".join(parts) if parts else "PydanticAI Agent"
    name = f"agent_{model.replace(':', '_')}" if model else "unnamed_agent"
    capabilities: list[str] = []
    if model:
        capabilities.append(f"model:{model}")
    for kw in call.keywords:
        if kw.arg == "mcp_servers" and isinstance(kw.value, ast.List):
            for elt in kw.value.elts:
                if isinstance(elt, ast.Name):
                    capabilities.append(f"mcp_server:{elt.id}")
    body = ast.get_source_segment(source, call) or ""
    return _build_skill(name, description, body, file_path, source, capabilities)


def _extract_definitions(source: str, file_path: Path) -> list[ParsedSkill]:
    """Extract all PydanticAI Agent and tool definitions from source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback(source, file_path)
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_agent_constructor(node):
            skill = _parse_agent_call(node, source, file_path)
            if skill is not None:
                results.append(skill)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            skill = _parse_tool_function(node, source, file_path)
            if skill is not None:
                results.append(skill)
    return results


def _regex_fallback(source: str, file_path: Path) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing."""
    results: list[ParsedSkill] = []
    for match in re.finditer(r"""Agent\s*\(\s*["']([^"']+)["']""", source):
        results.append(
            _build_skill(f"agent_{match.group(1)}", "", source, file_path, source),
        )
    for match in re.finditer(r"@\w+\.(?:tool|tool_plain)\s*\n\s*def\s+(\w+)", source):
        results.append(
            _build_skill(match.group(1), "", source, file_path, source),
        )
    return results


class PydanticAIParser(SkillParser):
    """Parser for PydanticAI agent and tool definitions."""

    def can_parse(self, path: Path) -> bool:
        """Return True if directory contains PydanticAI agent files."""
        if self._has_pyproject_dependency(path):
            return True
        return bool(self._find_pydanticai_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all PydanticAI agent and tool definitions."""
        results: list[ParsedSkill] = []
        for py_file in self._find_pydanticai_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(_extract_definitions(source, py_file))
        return results

    def _find_pydanticai_files(self, path: Path) -> list[Path]:
        """Find Python files containing PydanticAI definitions."""
        candidates: list[Path] = []
        search_dirs = [path]
        for dir_name in _TOOL_DIR_NAMES:
            sub = path / dir_name
            if sub.is_dir():
                search_dirs.append(sub)
        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_pydanticai_imports(head):
                    candidates.append(py_file)
        return candidates

    @staticmethod
    def _has_pyproject_dependency(path: Path) -> bool:
        """Check pyproject.toml for pydantic-ai in dependencies."""
        pyproject = path / "pyproject.toml"
        if not pyproject.is_file():
            return False
        try:
            content = pyproject.read_text(encoding="utf-8")[:8192]
        except (OSError, UnicodeDecodeError):
            return False
        return "pydantic-ai" in content or "pydantic_ai" in content
