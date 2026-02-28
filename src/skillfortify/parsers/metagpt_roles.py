"""Parser for MetaGPT Role, Action, Team, and @register_tool definitions.

Extracts security metadata from Python files containing MetaGPT patterns:
Role subclasses, Action subclasses, @register_tool() functions, and
Team().hire() compositions.

References:
    Hong et al., "MetaGPT: Meta Programming for A Multi-Agent
    Collaborative Framework" (ICLR 2025 Oral).
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
_METAGPT_IMPORT_MARKERS = ("from metagpt", "import metagpt")
_ROLE_BASE_NAMES = ("Role",)
_ACTION_BASE_NAMES = ("Action",)


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from *text*."""
    return _URL_PATTERN.findall(text)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment-variable names from *text*."""
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def _extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from subprocess / os calls in source."""
    return _SHELL_CALL_PATTERN.findall(text)


def _extract_imports(text: str) -> list[str]:
    """Extract top-level package names via AST with regex fallback."""
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


def _has_metagpt_imports(text: str) -> bool:
    """Return True if *text* contains MetaGPT import statements."""
    return any(marker in text for marker in _METAGPT_IMPORT_MARKERS)


def _has_metagpt_pyproject(path: Path) -> bool:
    """Check if pyproject.toml in *path* lists metagpt as a dependency."""
    pyproject = path / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8")[:8192]
    except (OSError, UnicodeDecodeError):
        return False
    return "metagpt" in content.lower()


def _class_attr(node: ast.ClassDef, attr_name: str) -> str:
    """Return the string value of a class-level attribute named *attr_name*."""
    for item in node.body:
        target_name: str | None = None
        value: ast.expr | None = None
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            target_name, value = item.target.id, item.value
        elif isinstance(item, ast.Assign):
            for t in item.targets:
                if isinstance(t, ast.Name):
                    target_name, value = t.id, item.value
                    break
        if (
            target_name == attr_name
            and value is not None
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ):
            return value.value
    return ""


def _is_subclass_of(node: ast.ClassDef, base_names: tuple[str, ...]) -> bool:
    """Check whether *node* inherits from any of *base_names*."""
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in base_names:
            return True
        if isinstance(base, ast.Attribute) and base.attr in base_names:
            return True
    return False


def _build_skill(
    name: str, description: str, body: str,
    path: Path, source: str, *, skill_type: str = "",
) -> ParsedSkill:
    """Construct a ``ParsedSkill`` from extracted MetaGPT metadata."""
    desc = f"[{skill_type}] {description}".strip() if skill_type else description
    return ParsedSkill(
        name=name, version="unknown", source_path=path, format="metagpt",
        description=desc, code_blocks=[body] if body else [],
        urls=_extract_urls(body), env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source), raw_content=source,
    )


def _parse_roles(tree: ast.Module, source: str, path: Path) -> list[ParsedSkill]:
    """Extract ``ParsedSkill`` instances from Role subclasses."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _is_subclass_of(node, _ROLE_BASE_NAMES):
            continue
        name = _class_attr(node, "name") or node.name
        profile = _class_attr(node, "profile")
        goal = _class_attr(node, "goal")
        parts = [f"profile={profile}"] if profile else []
        if goal:
            parts.append(f"goal={goal}")
        body_text = ast.get_source_segment(source, node) or ""
        results.append(
            _build_skill(name, "; ".join(parts), body_text, path, source, skill_type="Role"),
        )
    return results


def _parse_actions(tree: ast.Module, source: str, path: Path) -> list[ParsedSkill]:
    """Extract ``ParsedSkill`` instances from Action subclasses."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _is_subclass_of(node, _ACTION_BASE_NAMES):
            continue
        name = _class_attr(node, "name") or node.name
        body_text = ast.get_source_segment(source, node) or ""
        results.append(
            _build_skill(name, "", body_text, path, source, skill_type="Action"),
        )
    return results


def _parse_register_tools(
    tree: ast.Module, source: str, path: Path,
) -> list[ParsedSkill]:
    """Extract ``ParsedSkill`` instances from ``@register_tool()`` functions."""
    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _has_register_tool_decorator(node):
            continue
        description = ast.get_docstring(node) or ""
        body_text = ast.get_source_segment(source, node) or ""
        results.append(
            _build_skill(node.name, description, body_text, path, source, skill_type="Tool"),
        )
    return results


def _has_register_tool_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if *node* has a ``@register_tool`` decorator."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Name) and func.id == "register_tool":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "register_tool":
                return True
        elif isinstance(dec, ast.Name) and dec.id == "register_tool":
            return True
        elif isinstance(dec, ast.Attribute) and dec.attr == "register_tool":
            return True
    return False


def _regex_fallback(source: str, file_path: Path) -> list[ParsedSkill]:
    """Use regex to extract skills when AST parsing fails."""
    results: list[ParsedSkill] = []
    for match in re.finditer(r"class\s+(\w+)\s*\(\s*(?:Role|Action)\s*\)", source):
        results.append(_build_skill(match.group(1), "", source, file_path, source))
    for match in re.finditer(r"@register_tool\s*\(.*?\)\s*\n\s*def\s+(\w+)", source):
        results.append(_build_skill(match.group(1), "", source, file_path, source))
    return results


class MetaGPTParser(SkillParser):
    """Parser for MetaGPT Role, Action, Team, and @register_tool definitions."""

    def can_parse(self, path: Path) -> bool:
        """Return True if *path* contains MetaGPT skill definitions."""
        if _has_metagpt_pyproject(path):
            return True
        return bool(self._find_python_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all MetaGPT skills found under *path*."""
        results: list[ParsedSkill] = []
        for py_file in self._find_python_files(path):
            results.extend(self._parse_file(py_file))
        return results

    def _parse_file(self, py_file: Path) -> list[ParsedSkill]:
        """Parse a single Python file for MetaGPT definitions."""
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return _regex_fallback(source, py_file)
        results: list[ParsedSkill] = []
        results.extend(_parse_roles(tree, source, py_file))
        results.extend(_parse_actions(tree, source, py_file))
        results.extend(_parse_register_tools(tree, source, py_file))
        return results

    def _find_python_files(self, path: Path) -> list[Path]:
        """Find Python files under *path* that contain MetaGPT markers."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in ("roles", "actions", "tools", "metagpt_roles"):
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)
        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_metagpt_imports(head):
                    candidates.append(py_file)
        return candidates
