"""Text extraction utilities for the OpenAI Agents SDK parser.

Provides compiled regex patterns and helper functions for extracting
URLs, environment variables, shell commands, and import names from
Python source text. Also contains the ``build_skill`` factory that
constructs ``ParsedSkill`` instances with pre-populated security
metadata.

These utilities are shared by ``openai_agents_extractors.py`` and
``openai_agents.py``.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill

# --------------------------------------------------------------------------- #
# Compiled patterns                                                            #
# --------------------------------------------------------------------------- #

URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

ENV_VAR_PATTERN = re.compile(
    r"""(?:"""
    r"""\$\{?([A-Z][A-Z0-9_]{1,})\}?"""
    r"""|os\.environ\[["']([A-Z][A-Z0-9_]{1,})["']\]"""
    r"""|os\.getenv\(["']([A-Z][A-Z0-9_]{1,})["']\)"""
    r""")""",
    re.MULTILINE,
)

SHELL_CALL_PATTERN = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))"
    r"""\s*\(\s*["']([^"']+)["']""",
)

# Format identifier for all ParsedSkill instances from this parser.
FORMAT = "openai_agents"


# --------------------------------------------------------------------------- #
# Text extraction functions                                                    #
# --------------------------------------------------------------------------- #

def extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from *text*."""
    return URL_PATTERN.findall(text)


def extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from *text*."""
    found: set[str] = set()
    for match in ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def extract_shell_commands(text: str) -> list[str]:
    """Extract shell command strings from subprocess/os calls."""
    return SHELL_CALL_PATTERN.findall(text)


def extract_imports(text: str) -> list[str]:
    """Extract top-level import package names via AST (regex fallback)."""
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _regex_import_fallback(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module.split(".")[0])
    return sorted(set(imports))


def _regex_import_fallback(text: str) -> list[str]:
    """Regex fallback for import extraction on unparseable files."""
    imports: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            parts = stripped.split()
            if len(parts) >= 2:
                imports.append(parts[1].split(".")[0])
    return sorted(set(imports))


# --------------------------------------------------------------------------- #
# Skill builder                                                                #
# --------------------------------------------------------------------------- #

def build_skill(
    name: str,
    description: str,
    body: str,
    path: Path,
    source: str,
    *,
    capabilities: list[str] | None = None,
    instructions: str = "",
) -> ParsedSkill:
    """Construct a ``ParsedSkill`` from extracted metadata.

    Args:
        name: Tool or agent name.
        description: Human-readable description.
        body: Source text of the tool/agent definition.
        path: Filesystem path to the source file.
        source: Full file source text (for dependency extraction).
        capabilities: Optional declared capability strings.
        instructions: Optional agent instruction text.

    Returns:
        A fully populated ``ParsedSkill`` instance.
    """
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=path,
        format=FORMAT,
        description=description,
        instructions=instructions,
        declared_capabilities=capabilities or [],
        code_blocks=[body] if body else [],
        urls=extract_urls(body),
        env_vars_referenced=extract_env_vars(body),
        shell_commands=extract_shell_commands(body),
        dependencies=extract_imports(source),
        raw_content=source,
    )
