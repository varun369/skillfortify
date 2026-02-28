"""Parser for CAMEL-AI agent and toolkit definitions.

Extracts security metadata from Python files containing CAMEL-AI imports
(ChatAgent, RolePlaying, Workforce, FunctionTool, toolkit classes).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

_URL_RE = re.compile(r"https?://[^\s\"'`)\]>]+")
_ENV_RE = re.compile(
    r"""(?:\$\{?([A-Z][A-Z0-9_]{1,})\}?"""
    r"""|os\.environ\[["']([A-Z][A-Z0-9_]{1,})["']\]"""
    r"""|os\.getenv\(["']([A-Z][A-Z0-9_]{1,})["']\))""",
    re.MULTILINE,
)
_SHELL_RE = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))"
    r"""\s*\(\s*["']([^"']+)["']""",
)

_CAMEL_MARKERS = ("from camel", "import camel")

_TOOLKIT_CLASSES = (
    "SearchToolkit", "CodeExecutionToolkit", "MathToolkit",
    "GoogleMapsToolkit", "WeatherToolkit", "SlackToolkit",
    "TwitterToolkit", "GithubToolkit", "GoogleScholarToolkit",
    "HuggingFaceToolkit", "RetrievalToolkit", "DalleToolkit",
)

_AGENT_CLASSES = (
    "ChatAgent", "RolePlaying", "Workforce",
    "CriticAgent", "TaskSpecifyAgent", "EmbodiedAgent",
)

_TOOLKIT_CAPS: dict[str, list[str]] = {
    "SearchToolkit": ["network:read"],
    "CodeExecutionToolkit": ["code:execute", "filesystem:write"],
    "MathToolkit": ["compute"],
    "GoogleMapsToolkit": ["network:read", "location:read"],
    "WeatherToolkit": ["network:read"],
    "SlackToolkit": ["network:read", "network:write"],
    "TwitterToolkit": ["network:read", "network:write"],
    "GithubToolkit": ["network:read", "network:write"],
    "GoogleScholarToolkit": ["network:read"],
    "HuggingFaceToolkit": ["network:read", "compute"],
    "RetrievalToolkit": ["filesystem:read"],
    "DalleToolkit": ["network:read", "network:write"],
}


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from *text*."""
    return _URL_RE.findall(text)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from *text*."""
    found: set[str] = set()
    for m in _ENV_RE.finditer(text):
        for g in m.groups():
            if g:
                found.add(g)
    return sorted(found)


def _extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from subprocess/os calls."""
    return _SHELL_RE.findall(text)


def _extract_imports(text: str) -> list[str]:
    """Extract top-level import package names via AST (regex fallback)."""
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(("import ", "from ")):
                parts = s.split()
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


def _has_camel_imports(text: str) -> bool:
    """Return True if *text* contains CAMEL-AI import statements."""
    return any(m in text for m in _CAMEL_MARKERS)


def _build_skill(
    name: str, desc: str, body: str, path: Path, source: str,
    caps: list[str] | None = None,
) -> ParsedSkill:
    """Construct a ``ParsedSkill`` from extracted CAMEL-AI metadata."""
    return ParsedSkill(
        name=name, version="unknown", source_path=path, format="camel",
        description=desc, declared_capabilities=caps or [],
        code_blocks=[body] if body else [],
        urls=_extract_urls(body), env_vars_referenced=_extract_env_vars(body),
        shell_commands=_extract_shell_commands(body),
        dependencies=_extract_imports(source), raw_content=source,
    )


def _get_call_name(node: ast.Call) -> str | None:
    """Extract the simple function/class name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _extract_string_kwarg(node: ast.Call, name: str) -> str | None:
    """Extract a string keyword argument value from a Call node."""
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    if name == "system_message":
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return str(arg.value)
    return None


def _extract_toolkit_skills(source: str, fp: Path) -> list[ParsedSkill]:
    """Extract skills from toolkit instantiations and FunctionTool wraps."""
    results: list[ParsedSkill] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_toolkits(source, fp)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = _get_call_name(node)
        if not fn:
            continue
        if fn in _TOOLKIT_CLASSES:
            body = ast.get_source_segment(source, node) or ""
            results.append(_build_skill(
                fn, f"CAMEL-AI {fn}", body, fp, source, _TOOLKIT_CAPS.get(fn, []),
            ))
        if fn == "FunctionTool" and node.args:
            wrapped = ast.get_source_segment(source, node.args[0]) or "unknown_function"
            body = ast.get_source_segment(source, node) or ""
            results.append(_build_skill(
                f"FunctionTool({wrapped})", f"FunctionTool wrapping {wrapped}",
                body, fp, source,
            ))
    return results


def _extract_agent_skills(source: str, fp: Path) -> list[ParsedSkill]:
    """Extract skills from agent/society class instantiations."""
    results: list[ParsedSkill] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_agents(source, fp)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = _get_call_name(node)
        if fn not in _AGENT_CLASSES:
            continue
        desc = _extract_string_kwarg(node, "system_message") or ""
        role = (
            _extract_string_kwarg(node, "assistant_role_name")
            or _extract_string_kwarg(node, "role_name")
            or ""
        )
        body = ast.get_source_segment(source, node) or ""
        results.append(_build_skill(role or fn, desc, body, fp, source))
    return results


def _regex_toolkits(source: str, fp: Path) -> list[ParsedSkill]:
    """Regex fallback for toolkit instantiations in unparseable files."""
    results: list[ParsedSkill] = []
    for tk in _TOOLKIT_CLASSES:
        if re.search(rf"\b{tk}\s*\(", source):
            results.append(_build_skill(
                tk, f"CAMEL-AI {tk}", source, fp, source, _TOOLKIT_CAPS.get(tk, []),
            ))
    return results


def _regex_agents(source: str, fp: Path) -> list[ParsedSkill]:
    """Regex fallback for agent instantiations in unparseable files."""
    results: list[ParsedSkill] = []
    for cls in _AGENT_CLASSES:
        if re.search(rf"\b{cls}\s*\(", source):
            results.append(_build_skill(cls, f"CAMEL-AI {cls}", source, fp, source))
    return results


class CamelAIParser(SkillParser):
    """Parser for CAMEL-AI toolkit and agent definitions."""

    def can_parse(self, path: Path) -> bool:
        """Check if directory contains CAMEL-AI definitions."""
        pyproject = path / "pyproject.toml"
        if pyproject.is_file():
            try:
                if "camel-ai" in pyproject.read_text(encoding="utf-8"):
                    return True
            except (OSError, UnicodeDecodeError):
                pass
        return bool(self._find_camel_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all CAMEL-AI tools and agents in the directory."""
        results: list[ParsedSkill] = []
        for py_file in self._find_camel_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(_extract_toolkit_skills(source, py_file))
            results.extend(_extract_agent_skills(source, py_file))
        return results

    def _find_camel_files(self, path: Path) -> list[Path]:
        """Find Python files containing CAMEL-AI imports."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub in ("agents", "tools", "camel_agents"):
            d = path / sub
            if d.is_dir():
                search_dirs.append(d)
        for sd in search_dirs:
            for py in sorted(sd.glob("*.py")):
                try:
                    head = py.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_camel_imports(head):
                    candidates.append(py)
        return candidates
