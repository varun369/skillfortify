"""Parser for Microsoft Semantic Kernel plugin definitions.

Extracts security-relevant metadata from Python files with ``semantic_kernel``
imports and ``@kernel_function`` decorators. Each decorated method becomes a
separate ParsedSkill with URLs, env vars, shell commands, and dependencies.

References:
    Microsoft Semantic Kernel (27K GitHub stars, enterprise Azure AI).
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

_SK_IMPORT_MARKERS = ("from semantic_kernel", "import semantic_kernel")
_KERNEL_FUNCTION_MARKER = "@kernel_function"
_PLUGIN_DIR_NAMES = ("plugins", "semantic_kernel_plugins", "sk_plugins")


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
    """Extract shell commands from subprocess/os calls."""
    return _SHELL_CALL_PATTERN.findall(text)


def _extract_imports(text: str) -> list[str]:
    """Extract top-level import package names from Python source."""
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
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])
    return sorted(set(imports))


def _has_sk_imports(text: str) -> bool:
    """Return True if *text* contains Semantic Kernel import statements."""
    return any(marker in text for marker in _SK_IMPORT_MARKERS)


def _extract_kernel_function_skills(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Parse a Python file for classes with @kernel_function methods.

    Falls back to regex when the file has syntax errors.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback(source, file_path)
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            results.extend(_parse_plugin_class(node, source, file_path))
    return results


def _parse_plugin_class(
    class_node: ast.ClassDef, source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract ParsedSkill entries from a class with @kernel_function methods."""
    results: list[ParsedSkill] = []
    for item in class_node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_kernel_function_decorator(item):
            continue
        description = _extract_decorator_description(item)
        docstring = ast.get_docstring(item) or ""
        body_text = ast.get_source_segment(source, item) or ""
        results.append(_build_skill(
            name=item.name,
            description=description or docstring,
            class_name=class_node.name,
            body=body_text,
            file_path=file_path,
            source=source,
        ))
    return results


def _has_kernel_function_decorator(node: ast.FunctionDef) -> bool:
    """Return True if *node* has the @kernel_function decorator."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "kernel_function":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "kernel_function":
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "kernel_function":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "kernel_function":
                return True
    return False


def _extract_decorator_description(node: ast.FunctionDef) -> str:
    """Extract description= kwarg from @kernel_function(description=...)."""
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        for keyword in decorator.keywords:
            if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
    return ""


def _build_skill(
    name: str, description: str, class_name: str,
    body: str, file_path: Path, source: str,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted Semantic Kernel metadata."""
    full_description = f"[{class_name}] {description}" if class_name else description
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=file_path,
        format="semantic_kernel",
        description=full_description,
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
    pattern = re.compile(r"@kernel_function[^\n]*\n\s*def\s+(\w+)", re.MULTILINE)
    for match in pattern.finditer(source):
        results.append(_build_skill(
            name=match.group(1), description="", class_name="",
            body=source, file_path=file_path, source=source,
        ))
    return results


class SemanticKernelParser(SkillParser):
    """Parser for Microsoft Semantic Kernel plugin definitions.

    Detects Python files with ``semantic_kernel`` imports and
    ``@kernel_function`` decorators. Extracts each decorated method
    as a ParsedSkill with security-relevant metadata.
    """

    def can_parse(self, path: Path) -> bool:
        """Return True if directory contains Semantic Kernel plugin files."""
        return bool(self._find_sk_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Semantic Kernel plugins in the directory."""
        results: list[ParsedSkill] = []
        for py_file in self._find_sk_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(_extract_kernel_function_skills(source, py_file))
        return results

    def _find_sk_files(self, path: Path) -> list[Path]:
        """Find Python files with Semantic Kernel markers in root or subdirs."""
        candidates: list[Path] = []
        search_dirs = [path]
        for dir_name in _PLUGIN_DIR_NAMES:
            sub = path / dir_name
            if sub.is_dir():
                search_dirs.append(sub)
        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_sk_imports(head) or _KERNEL_FUNCTION_MARKER in head:
                    candidates.append(py_file)
        return candidates
