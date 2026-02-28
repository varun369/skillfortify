"""Extraction helpers for the Composio tools parser.

Provides regex-based and AST-based extraction functions for
security-relevant signals in Python files using the Composio SDK:
URLs, environment variables, shell commands, imports, Action enum
references, and App enum references.

Separated from the main parser module to keep each file under the
300-line hard cap per the open-source quality standard.
"""

from __future__ import annotations

import ast
import re

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

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

# Composio import markers for fast can_parse probe.
COMPOSIO_IMPORT_MARKERS = (
    "from composio",
    "import composio",
    "from composio_langchain",
    "from composio_crewai",
    "from composio_autogen",
    "from composio_openai",
)

# Regex for Action.XYZ references.
ACTION_PATTERN = re.compile(r"\bAction\.([A-Z][A-Z0-9_]+)\b")

# Regex for App.XYZ references.
APP_PATTERN = re.compile(r"\bApp\.([A-Z][A-Z0-9_]+)\b")

# Env var string pattern inside ComposioToolSet(api_key="env:...")
ENV_STRING_PATTERN = re.compile(r"""["']env:([A-Z][A-Z0-9_]+)["']""")

# Subdirectories to search for Composio tool files.
TOOL_DIR_NAMES = {"tools", "composio_tools", "integrations", "actions"}


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text.

    Args:
        text: Source text to scan for URLs.

    Returns:
        List of URL strings found in the text.
    """
    return URL_PATTERN.findall(text)


def extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from text.

    Detects three patterns:
    - Shell-style: ``$VAR`` or ``${VAR}``
    - Direct access: ``os.environ["VAR"]``
    - Getenv: ``os.getenv("VAR")``
    - Composio-specific: ``"env:VAR"`` string literals

    Args:
        text: Source text to scan for env var references.

    Returns:
        Sorted list of unique environment variable names.
    """
    found: set[str] = set()
    for match in ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    # Also capture "env:VAR_NAME" patterns used in ComposioToolSet.
    for match in ENV_STRING_PATTERN.finditer(text):
        found.add(match.group(1))
    return sorted(found)


def extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from subprocess/os calls in source.

    Args:
        text: Source text to scan for shell execution calls.

    Returns:
        List of shell command strings found.
    """
    return SHELL_CALL_PATTERN.findall(text)


def extract_imports(text: str) -> list[str]:
    """Extract top-level import module names from Python source.

    Uses the AST for accurate parsing with a regex fallback for files
    that have syntax errors.

    Args:
        text: Python source text.

    Returns:
        Sorted list of unique top-level import names.
    """
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


def extract_actions(text: str) -> list[str]:
    """Extract Action.XYZ enum references from source text.

    Args:
        text: Source text to scan for Action enum usage.

    Returns:
        Sorted list of unique Action enum names (without ``Action.`` prefix).
    """
    return sorted(set(ACTION_PATTERN.findall(text)))


def extract_apps(text: str) -> list[str]:
    """Extract App.XYZ enum references from source text.

    Args:
        text: Source text to scan for App enum usage.

    Returns:
        Sorted list of unique App enum names (without ``App.`` prefix).
    """
    return sorted(set(APP_PATTERN.findall(text)))


def has_composio_imports(text: str) -> bool:
    """Check if text contains Composio import statements.

    Args:
        text: Source text to check (typically first 4KB of a file).

    Returns:
        True if any Composio import marker is found.
    """
    return any(marker in text for marker in COMPOSIO_IMPORT_MARKERS)
