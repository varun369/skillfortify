"""Parser for Composio tool definitions (Action/App/custom @action).

Extracts security-relevant metadata from Python files that use the
Composio SDK (26.5K stars, 500+ integrations). Composio acts as a
universal agent integration layer, connecting AI agents to external
services via pre-built actions and OAuth-managed app connections.

Detection heuristics:
    - ``from composio`` or ``import composio`` import statements
    - ``ComposioToolSet`` instantiation patterns
    - ``Action.<NAME>`` and ``App.<NAME>`` enum references
    - ``@action`` decorator for custom tool definitions

Security-relevant extraction:
    - Registered actions (``Action.GITHUB_CREATE_ISSUE``, etc.)
    - App integrations (``App.GITHUB``, ``App.SLACK``, etc.)
    - Custom ``@action`` definitions with their code bodies
    - Implied OAuth scopes from App integrations
    - Environment variables, URLs, shell commands in custom actions

References:
    Composio SDK: https://github.com/ComposioHQ/composio
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.composio_extractors import (
    TOOL_DIR_NAMES,
    extract_actions,
    extract_apps,
    extract_env_vars,
    extract_imports,
    extract_shell_commands,
    extract_urls,
    has_composio_imports,
)


# ---------------------------------------------------------------------------
# AST-based custom @action extraction
# ---------------------------------------------------------------------------


def _parse_custom_action(
    node: ast.FunctionDef, source: str, file_path: Path,
) -> ParsedSkill | None:
    """Extract a ParsedSkill from a Composio @action decorated function.

    Detects both ``@action`` and ``@action(toolname="...")`` forms.
    Extracts the toolname argument if present, otherwise uses the
    function name.

    Args:
        node: AST FunctionDef node to inspect.
        source: Full source text of the file.
        file_path: Path to the source file on disk.

    Returns:
        A ParsedSkill if the function is @action-decorated, else None.
    """
    toolname: str | None = None

    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "action":
            toolname = node.name
        elif isinstance(decorator, ast.Call):
            func = decorator.func
            is_action_call = (
                (isinstance(func, ast.Name) and func.id == "action")
                or (isinstance(func, ast.Attribute) and func.attr == "action")
            )
            if is_action_call:
                toolname = _extract_toolname_kwarg(decorator, node.name)

    if toolname is None:
        return None

    description = ast.get_docstring(node) or ""
    body_text = ast.get_source_segment(source, node) or ""
    return _build_skill(toolname, description, body_text, file_path, source)


def _extract_toolname_kwarg(call_node: ast.Call, default: str) -> str:
    """Extract the 'toolname' keyword argument from @action(...) call.

    Args:
        call_node: AST Call node for the decorator invocation.
        default: Fallback name if 'toolname' is not specified.

    Returns:
        The toolname string value, or default if not found.
    """
    for keyword in call_node.keywords:
        if keyword.arg == "toolname" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    return default


# ---------------------------------------------------------------------------
# Skill builders
# ---------------------------------------------------------------------------


def _build_capabilities(source: str) -> list[str]:
    """Build declared capabilities from Action and App references.

    Args:
        source: Full source text to scan.

    Returns:
        Sorted, deduplicated list of capability strings.
    """
    capabilities: list[str] = []
    capabilities.extend(f"action:{act}" for act in extract_actions(source))
    capabilities.extend(f"app:{app}" for app in extract_apps(source))
    return sorted(set(capabilities))


def _build_skill(
    name: str, description: str, body: str, path: Path, source: str,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted Composio tool metadata.

    Args:
        name: Tool name (from toolname kwarg or function name).
        description: Tool description (from docstring).
        body: Source segment of the tool body (for code blocks).
        path: Path to the source file on disk.
        source: Full source text of the file.

    Returns:
        A fully populated ParsedSkill instance.
    """
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=path,
        format="composio",
        description=description,
        code_blocks=[body] if body else [],
        urls=extract_urls(body),
        env_vars_referenced=extract_env_vars(source),
        shell_commands=extract_shell_commands(body),
        dependencies=extract_imports(source),
        declared_capabilities=_build_capabilities(source),
        raw_content=source,
    )


def _build_module_skill(file_path: Path, source: str) -> ParsedSkill:
    """Build a module-level ParsedSkill for files with no custom actions.

    When a file uses ComposioToolSet with Action/App references but has
    no custom @action definitions, we emit a single module-level skill
    capturing those references.

    Args:
        file_path: Path to the source file.
        source: Full source text.

    Returns:
        A ParsedSkill representing the module's Composio usage.
    """
    actions = extract_actions(source)
    apps = extract_apps(source)

    description_parts: list[str] = []
    if actions:
        description_parts.append(f"Actions: {', '.join(actions)}")
    if apps:
        description_parts.append(f"Apps: {', '.join(apps)}")

    return ParsedSkill(
        name=file_path.stem,
        version="unknown",
        source_path=file_path,
        format="composio",
        description="; ".join(description_parts),
        code_blocks=[],
        urls=extract_urls(source),
        env_vars_referenced=extract_env_vars(source),
        shell_commands=extract_shell_commands(source),
        dependencies=extract_imports(source),
        declared_capabilities=_build_capabilities(source),
        raw_content=source,
    )


# ---------------------------------------------------------------------------
# File-level parsing
# ---------------------------------------------------------------------------


def _parse_composio_file(file_path: Path) -> list[ParsedSkill]:
    """Parse a single Python file for Composio tool definitions.

    Strategy:
    1. AST-parse the file to find custom @action functions.
    2. If no custom actions found but Action/App refs exist, emit
       a module-level skill capturing those references.
    3. On SyntaxError, fall back to regex extraction.

    Args:
        file_path: Path to the Python file to parse.

    Returns:
        List of ParsedSkill instances found in the file.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback(source, file_path)

    custom_actions: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            skill = _parse_custom_action(node, source, file_path)
            if skill is not None:
                custom_actions.append(skill)

    if custom_actions:
        return custom_actions

    # No custom actions -- check for Action/App references.
    if extract_actions(source) or extract_apps(source):
        return [_build_module_skill(file_path, source)]

    return []


def _regex_fallback(source: str, file_path: Path) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing."""
    results: list[ParsedSkill] = []
    for match in re.finditer(r"@action\b.*\ndef\s+(\w+)", source):
        name = match.group(1)
        results.append(_build_skill(name, "", source, file_path, source))
    if not results and (extract_actions(source) or extract_apps(source)):
        results.append(_build_module_skill(file_path, source))
    return results


# ---------------------------------------------------------------------------
# Public parser class
# ---------------------------------------------------------------------------


class ComposioParser(SkillParser):
    """Parser for Composio tool definitions in Python files.

    Detects and extracts:
    - Action-based tool retrieval (``Action.GITHUB_CREATE_ISSUE``)
    - App-based integrations (``App.GITHUB``, ``App.SLACK``)
    - Custom ``@action`` decorated functions
    - Entity/connection management patterns
    - Security signals: env vars, URLs, shell commands
    """

    def can_parse(self, path: Path) -> bool:
        """Return True if directory contains Composio tool files."""
        return bool(self._find_tool_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Composio tool files and return ParsedSkill list."""
        results: list[ParsedSkill] = []
        for py_file in self._find_tool_files(path):
            results.extend(_parse_composio_file(py_file))
        return results

    def _find_tool_files(self, path: Path) -> list[Path]:
        """Find Python files with Composio markers in root or sub dirs."""
        candidates: list[Path] = []
        search_dirs = [path]
        for dir_name in TOOL_DIR_NAMES:
            sub = path / dir_name
            if sub.is_dir():
                search_dirs.append(sub)

        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if has_composio_imports(head):
                    candidates.append(py_file)
        return candidates
