"""Parser for AutoGen tool definitions (register_for_llm / function schemas).

Extracts security metadata from Python files containing AutoGen
``@agent.register_for_llm`` decorated functions and function schema
dict literals (name/description/parameters).
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

# AutoGen import markers.
_AUTOGEN_IMPORT_MARKERS = (
    "from autogen",
    "import autogen",
    "from pyautogen",
    "import pyautogen",
)

# Decorator patterns for register_for_llm.
_REGISTER_DECORATOR = re.compile(r"register_for_llm")

# Function schema dict pattern.
_FUNC_SCHEMA_PATTERN = re.compile(
    r"""["']name["']\s*:\s*["'](\w+)["']""",
)


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


def _has_autogen_imports(text: str) -> bool:
    """Check if text contains AutoGen import statements."""
    return any(marker in text for marker in _AUTOGEN_IMPORT_MARKERS)


def _has_register_decorator(text: str) -> bool:
    """Check if text contains register_for_llm decorator."""
    return bool(_REGISTER_DECORATOR.search(text))


def _has_function_schema(text: str) -> bool:
    """Check if text contains function schema dicts."""
    return '"name"' in text and '"description"' in text and '"parameters"' in text


def _build_skill(
    name: str, description: str, body: str, path: Path, source: str,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted AutoGen tool metadata."""
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=path,
        format="autogen",
        description=description,
        code_blocks=[body] if body else [],
        urls=_extract_urls(body),
        env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source),
        raw_content=source,
    )


def _extract_register_for_llm_tools(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract tools decorated with @agent.register_for_llm."""
    results: list[ParsedSkill] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback_decorators(source, file_path)

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # Check for register_for_llm in decorators.
        reg_desc = ""
        is_registered = False
        for dec in node.decorator_list:
            if _is_register_for_llm(dec):
                is_registered = True
                reg_desc = _extract_description_kwarg(dec)
                break

        if not is_registered:
            continue

        name = node.name
        description = reg_desc or ast.get_docstring(node) or ""
        body_text = ast.get_source_segment(source, node) or ""
        results.append(_build_skill(name, description, body_text, file_path, source))

    return results


def _is_register_for_llm(decorator: ast.expr) -> bool:
    """Check if a decorator node is a register_for_llm call."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr == "register_for_llm":
            return True
    return False


def _extract_description_kwarg(call_node: ast.expr) -> str:
    """Extract the description keyword argument from a decorator call."""
    if not isinstance(call_node, ast.Call):
        return ""
    for kw in call_node.keywords:
        if kw.arg == "description" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""


def _extract_function_schemas(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract tools from function schema dict literals."""
    results: list[ParsedSkill] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue

        name_val = None
        desc_val = None
        has_parameters = False

        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant):
                continue
            if key.value == "name" and isinstance(value, ast.Constant):
                name_val = str(value.value)
            elif key.value == "description" and isinstance(value, ast.Constant):
                desc_val = str(value.value)
            elif key.value == "parameters":
                has_parameters = True

        if name_val and desc_val and has_parameters:
            body = ast.get_source_segment(source, node) or ""
            results.append(
                _build_skill(name_val, desc_val, body, file_path, source),
            )

    return results


def _regex_fallback_decorators(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Regex fallback for register_for_llm decorated functions."""
    results: list[ParsedSkill] = []
    pattern = re.compile(
        r"register_for_llm\s*\(.*?\)\s*\n\s*def\s+(\w+)",
        re.DOTALL,
    )
    for match in pattern.finditer(source):
        results.append(
            _build_skill(match.group(1), "", source, file_path, source),
        )
    return results


class AutoGenParser(SkillParser):
    """Parser for AutoGen tool definitions (register_for_llm + schemas)."""

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains AutoGen tool definitions."""
        return bool(self._find_tool_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all AutoGen tools in the directory."""
        results: list[ParsedSkill] = []
        for py_file in self._find_tool_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            results.extend(_extract_register_for_llm_tools(source, py_file))
            results.extend(_extract_function_schemas(source, py_file))

        return results

    def _find_tool_files(self, path: Path) -> list[Path]:
        """Find Python files containing AutoGen tool definitions."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in ("tools", "autogen_tools"):
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)

        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if (
                    _has_autogen_imports(head)
                    or _has_register_decorator(head)
                    or _has_function_schema(head)
                ):
                    candidates.append(py_file)
        return candidates
