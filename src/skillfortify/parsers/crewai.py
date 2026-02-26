"""Parser for CrewAI tool definitions (YAML configs + Python tool files).

Extracts security metadata from crew.yaml / agents.yaml tool references
and Python files with ``crewai`` imports containing BaseTool subclasses
or @tool decorated functions.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

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

# Detect shell-execution calls in Python source (for pattern scanning).
_SHELL_CALL_PATTERN = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))"
    r"""\s*\(\s*["']([^"']+)["']""",
)

# CrewAI import markers.
_CREWAI_IMPORT_MARKERS = (
    "from crewai",
    "import crewai",
)

# YAML config filenames.
_CREW_CONFIG_FILES = ("crew.yaml", "crew.yml", "agents.yaml", "agents.yml")


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
    """Extract import names from Python source via AST with regex fallback."""
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
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


def _has_crewai_imports(text: str) -> bool:
    """Check if text contains CrewAI import statements."""
    return any(marker in text for marker in _CREWAI_IMPORT_MARKERS)


def _parse_yaml_config(config_path: Path) -> list[ParsedSkill]:
    """Parse a CrewAI YAML config to extract tool references.

    YAML configs declare agents with tool lists. Each tool reference
    is captured as a minimal ParsedSkill so the registry can flag
    tools that are referenced but not yet analysed.
    """
    try:
        raw = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError):
        return []

    if not isinstance(data, dict):
        return []

    results: list[ParsedSkill] = []
    agents = data.get("agents", {})
    if isinstance(agents, dict):
        for agent_name, agent_cfg in agents.items():
            if not isinstance(agent_cfg, dict):
                continue
            tools = agent_cfg.get("tools", [])
            if not isinstance(tools, list):
                continue
            for tool_name in tools:
                results.append(ParsedSkill(
                    name=str(tool_name),
                    version="unknown",
                    source_path=config_path,
                    format="crewai",
                    description=f"Tool referenced by agent '{agent_name}'",
                    raw_content=raw,
                ))
    return results


def _parse_python_tool_file(py_file: Path) -> list[ParsedSkill]:
    """Parse a Python file for CrewAI BaseTool subclasses and @tool funcs."""
    try:
        source = py_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback(source, py_file)

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        skill = None
        if isinstance(node, ast.ClassDef):
            skill = _parse_class_tool(node, source, py_file)
        elif isinstance(node, ast.FunctionDef):
            skill = _parse_function_tool(node, source, py_file)
        if skill is not None:
            results.append(skill)
    return results


def _parse_class_tool(
    node: ast.ClassDef, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Extract a ParsedSkill from a CrewAI BaseTool subclass."""
    is_base_tool = any(
        (isinstance(b, ast.Name) and b.id == "BaseTool")
        or (isinstance(b, ast.Attribute) and b.attr == "BaseTool")
        for b in node.bases
    )
    if not is_base_tool:
        return None

    name = node.name
    description = ""

    for item in node.body:
        if isinstance(item, ast.AnnAssign):
            if (
                isinstance(item.target, ast.Name)
                and item.value is not None
                and isinstance(item.value, ast.Constant)
            ):
                if item.target.id == "name":
                    name = str(item.value.value)
                elif item.target.id == "description":
                    description = str(item.value.value)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                    if target.id == "name":
                        name = str(item.value.value)
                    elif target.id == "description":
                        description = str(item.value.value)

    body_text = ast.get_source_segment(source, node) or ""
    return _build_skill(name, description, body_text, file_path, source)


def _parse_function_tool(
    node: ast.FunctionDef, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Extract a ParsedSkill from a @tool decorated function."""
    has_tool_dec = any(
        (isinstance(d, ast.Name) and d.id == "tool")
        or (isinstance(d, ast.Attribute) and d.attr == "tool")
        for d in node.decorator_list
    )
    if not has_tool_dec:
        return None

    name = node.name
    description = ast.get_docstring(node) or ""
    body_text = ast.get_source_segment(source, node) or ""
    return _build_skill(name, description, body_text, file_path, source)


def _build_skill(
    name: str, description: str, body: str, path: Path, source: str,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted CrewAI tool metadata."""
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=path,
        format="crewai",
        description=description,
        code_blocks=[body] if body else [],
        urls=_extract_urls(body),
        env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source),
        raw_content=source,
    )


def _regex_fallback(source: str, file_path: Path) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing."""
    results: list[ParsedSkill] = []
    for match in re.finditer(r"class\s+(\w+)\s*\(\s*BaseTool\s*\)", source):
        results.append(_build_skill(match.group(1), "", source, file_path, source))
    for match in re.finditer(r"@tool\s*\n\s*def\s+(\w+)", source):
        results.append(_build_skill(match.group(1), "", source, file_path, source))
    return results


class CrewAIParser(SkillParser):
    """Parser for CrewAI tool definitions (YAML configs + Python files)."""

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains CrewAI tool definitions."""
        # Check YAML configs.
        for cfg_name in _CREW_CONFIG_FILES:
            if (path / cfg_name).is_file():
                return True
        # Check Python files for crewai imports.
        return bool(self._find_python_tool_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all CrewAI tools in the directory."""
        results: list[ParsedSkill] = []

        # Parse YAML configs.
        for cfg_name in _CREW_CONFIG_FILES:
            cfg_path = path / cfg_name
            if cfg_path.is_file():
                results.extend(_parse_yaml_config(cfg_path))

        # Parse Python tool files.
        for py_file in self._find_python_tool_files(path):
            results.extend(_parse_python_tool_file(py_file))

        return results

    def _find_python_tool_files(self, path: Path) -> list[Path]:
        """Find Python files containing CrewAI tool definitions."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in ("tools", "crewai_tools"):
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)

        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_crewai_imports(head):
                    candidates.append(py_file)
        return candidates
