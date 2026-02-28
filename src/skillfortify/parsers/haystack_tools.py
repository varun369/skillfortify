"""Parser for Haystack (deepset) pipeline and tool definitions.

Extracts security metadata from Python files using the Haystack framework:
Pipeline construction, Tool/create_tool_from_function wrappers, ToolInvoker
components, OpenAPIServiceConnector usage, Secret.from_env_var() calls,
generator configurations, and @component decorators.

References:
    Haystack by deepset (23K+ GitHub stars) -- enterprise RAG framework.
    https://docs.haystack.deepset.ai/
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

FORMAT_NAME = "haystack"

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

_SECRET_FROM_ENV_PATTERN = re.compile(
    r"""Secret\.from_env_var\(\s*["']([A-Z][A-Z0-9_]*)["']\s*\)""",
)

_HAYSTACK_IMPORT_MARKERS = (
    "from haystack",
    "import haystack",
)

# ---------------------------------------------------------------------------
# Low-level extraction helpers
# ---------------------------------------------------------------------------


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text."""
    return _URL_PATTERN.findall(text)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from text.

    Captures os.environ[], os.getenv(), $VAR, and Secret.from_env_var().
    """
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    for match in _SECRET_FROM_ENV_PATTERN.finditer(text):
        found.add(match.group(1))
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


def _has_haystack_imports(text: str) -> bool:
    """Check if text contains Haystack import statements."""
    return any(marker in text for marker in _HAYSTACK_IMPORT_MARKERS)


def _get_kwarg_str(call: ast.Call, key: str) -> str:
    """Extract a string keyword argument from an ast.Call node."""
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""


def _build_skill(
    name: str,
    description: str,
    body: str,
    path: Path,
    source: str,
    capabilities: list[str] | None = None,
) -> ParsedSkill:
    """Construct a ParsedSkill from extracted Haystack metadata."""
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


# ---------------------------------------------------------------------------
# Backward-compatible aliases for the extraction functions that moved to
# haystack_extractors.  Tests and external callers can still import from
# this module without breaking.
# ---------------------------------------------------------------------------


def _extract_tool_definitions(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract Tool/create_tool_from_function calls (delegates to extractors)."""
    from skillfortify.parsers.haystack_extractors import extract_tool_definitions
    return extract_tool_definitions(source, file_path)


def _extract_pipeline_components(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Extract add_component calls (delegates to extractors)."""
    from skillfortify.parsers.haystack_extractors import extract_pipeline_components
    return extract_pipeline_components(source, file_path)


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------


class HaystackParser(SkillParser):
    """Parser for Haystack pipeline and tool definitions.

    Detects Haystack projects by checking for ``from haystack`` imports in
    Python files or ``haystack-ai`` in pyproject.toml/requirements.txt.

    Extracts:
        - Tool definitions (Tool, create_tool_from_function)
        - Pipeline components (add_component calls)
        - Secret.from_env_var() environment variable references
        - OpenAPI connectors and external URLs
        - Shell commands and subprocess calls
    """

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains Haystack definitions."""
        return bool(self._find_haystack_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Haystack tools and pipelines in the directory."""
        from skillfortify.parsers.haystack_extractors import (
            extract_pipeline_components,
            extract_tool_definitions,
        )

        results: list[ParsedSkill] = []
        for py_file in self._find_haystack_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(extract_tool_definitions(source, py_file))
            results.extend(extract_pipeline_components(source, py_file))
        return results

    def _find_haystack_files(self, path: Path) -> list[Path]:
        """Find Python files containing Haystack definitions."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in ("pipelines", "tools", "agents", "components"):
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)

        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_haystack_imports(head):
                    candidates.append(py_file)
        return candidates
