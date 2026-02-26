"""Parser for LangChain tool definitions (BaseTool subclasses / @tool).

Extracts security-relevant metadata (shell commands, URLs, env vars,
dependencies, code blocks) from class-based and decorator-based tool
definitions found in Python files with ``langchain`` / ``langchain_core``
imports.
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

# Detect shell-execution calls in Python source (for pattern scanning).
_SHELL_CALL_PATTERN = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))"
    r"""\s*\(\s*["']([^"']+)["']""",
)

# LangChain import markers -- used for fast can_parse probe.
_LANGCHAIN_IMPORT_MARKERS = (
    "from langchain",
    "from langchain_core",
    "import langchain",
)

# Patterns that indicate a directory is a tools directory.
_TOOL_DIR_NAMES = {"tools", "langchain_tools"}


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
    """Extract import names from Python source text using AST."""
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Fallback: regex for lines starting with import/from.
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


def _has_langchain_imports(text: str) -> bool:
    """Check if text contains LangChain import statements."""
    return any(marker in text for marker in _LANGCHAIN_IMPORT_MARKERS)


def _has_tool_decorator(text: str) -> bool:
    """Check if text contains @tool decorator."""
    return bool(re.search(r"@tool\b", text))


def _has_basetool_subclass(text: str) -> bool:
    """Check if text contains a BaseTool subclass."""
    return bool(re.search(r"class\s+\w+\s*\(\s*BaseTool\s*\)", text))


def _extract_tools_from_source(source: str, file_path: Path) -> list[ParsedSkill]:
    """Parse a Python source file and extract LangChain tool definitions.

    Uses the AST to find class-based (BaseTool subclasses) and decorator-based
    (@tool) tool definitions. Falls back to regex for files with syntax errors.
    """
    results: list[ParsedSkill] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # File has syntax errors -- extract what we can via regex.
        return _extract_tools_regex_fallback(source, file_path)

    for node in ast.walk(tree):
        skill = None
        if isinstance(node, ast.ClassDef):
            skill = _parse_class_tool(node, source, file_path)
        elif isinstance(node, ast.FunctionDef):
            skill = _parse_function_tool(node, source, file_path)
        if skill is not None:
            results.append(skill)

    return results


def _parse_class_tool(
    node: ast.ClassDef, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Extract a ParsedSkill from a BaseTool subclass."""
    # Check if this class inherits from BaseTool.
    is_base_tool = any(
        (isinstance(base, ast.Name) and base.id == "BaseTool")
        or (isinstance(base, ast.Attribute) and base.attr == "BaseTool")
        for base in node.bases
    )
    if not is_base_tool:
        return None

    name = node.name
    description = ""

    # Extract name/description from class body assignments.
    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                    if target.id == "name":
                        name = str(item.value.value)
                    elif target.id == "description":
                        description = str(item.value.value)
        elif isinstance(item, ast.AnnAssign):
            if (
                isinstance(item.target, ast.Name)
                and item.value is not None
                and isinstance(item.value, ast.Constant)
            ):
                if item.target.id == "name":
                    name = str(item.value.value)
                elif item.target.id == "description":
                    description = str(item.value.value)

    body_text = ast.get_source_segment(source, node) or ""
    return _build_parsed_skill(name, description, body_text, file_path, source)


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
    return _build_parsed_skill(name, description, body_text, file_path, source)


def _build_parsed_skill(
    name: str,
    description: str,
    body_text: str,
    file_path: Path,
    full_source: str,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted tool metadata."""
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=file_path,
        format="langchain",
        description=description,
        code_blocks=[body_text] if body_text else [],
        urls=_extract_urls(body_text),
        env_vars_referenced=_extract_env_vars(body_text),
        shell_commands=_extract_shell_commands(body_text),
        dependencies=_extract_imports(full_source),
        raw_content=full_source,
    )


def _extract_tools_regex_fallback(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing."""
    results: list[ParsedSkill] = []

    # Find class-based tools.
    for match in re.finditer(r"class\s+(\w+)\s*\(\s*BaseTool\s*\)", source):
        name = match.group(1)
        results.append(
            _build_parsed_skill(name, "", source, file_path, source),
        )

    # Find decorator-based tools.
    for match in re.finditer(r"@tool\s*\n\s*def\s+(\w+)", source):
        name = match.group(1)
        results.append(
            _build_parsed_skill(name, "", source, file_path, source),
        )

    return results


class LangChainParser(SkillParser):
    """Parser for LangChain tool definitions in Python files."""

    def can_parse(self, path: Path) -> bool:
        """Return True if directory contains LangChain tool files."""
        return any(self._find_tool_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all LangChain tool files and return ParsedSkill list."""
        results: list[ParsedSkill] = []
        for py_file in self._find_tool_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(_extract_tools_from_source(source, py_file))
        return results

    def _find_tool_files(self, path: Path) -> list[Path]:
        """Find Python files with LangChain markers in root or tools/ dirs."""
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
                if (
                    _has_langchain_imports(head)
                    or _has_tool_decorator(head)
                    or _has_basetool_subclass(head)
                ):
                    candidates.append(py_file)
        return candidates
