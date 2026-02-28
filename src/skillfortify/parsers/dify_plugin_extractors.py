"""Extraction helpers for Dify plugin parsing.

Provides functions for extracting security-relevant metadata from Dify
plugin manifests and provider configs: URLs, environment variables,
shell commands, credentials, dependencies, and tool descriptions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

# --- Constants -----------------------------------------------------------

DIFY_MANIFEST_FILENAMES = ("manifest.yaml", "manifest.yml", "manifest.json")
DIFY_PLUGIN_DIR = ".dify"
DIFY_PLUGIN_TYPES = frozenset({"tool", "model", "extension", "bundle"})
DIFY_IMPORT_MARKER = "dify_plugin"
PROVIDER_CREDENTIAL_KEY = "credentials_for_provider"
YAML_EXTENSIONS = ("*.yaml", "*.yml")

_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

_ENV_VAR_PATTERN = re.compile(
    r"""(?:"""
    r"""\$\{?([A-Z][A-Z0-9_]{1,})\}?"""
    r"""|(?:^|[\s=:])([A-Z][A-Z_]{1,}[A-Z0-9_]*)(?=[=\s"'`])"""
    r""")""",
    re.MULTILINE,
)

_SHELL_COMMAND_PATTERN = re.compile(
    r"(?:curl|wget|bash|sh|rm|chmod|chown|pip|npm|apt-get|yum"
    r"|docker|kubectl|ssh|scp|nc|ncat)\s+[^\n]{3,}",
)


# --- URL / env / shell extraction ----------------------------------------


def extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text.

    Args:
        text: Raw text to scan.

    Returns:
        List of URL strings found.
    """
    return _URL_PATTERN.findall(text)


def extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from text.

    Args:
        text: Raw text to scan.

    Returns:
        Sorted list of unique env var names.
    """
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from raw text content.

    Args:
        text: Raw text to scan for shell invocations.

    Returns:
        List of shell command strings.
    """
    return _SHELL_COMMAND_PATTERN.findall(text)


# --- Credential extraction -----------------------------------------------


def extract_credentials(data: dict[str, Any]) -> list[str]:
    """Extract credential variable names from a Dify config block.

    Walks ``credentials_for_provider`` entries and collects the
    ``variable`` field from each credential declaration.

    Args:
        data: Dictionary (manifest, tool block, or provider config).

    Returns:
        List of credential variable names.
    """
    creds = data.get(PROVIDER_CREDENTIAL_KEY, [])
    if not isinstance(creds, list):
        return []
    result: list[str] = []
    for entry in creds:
        if isinstance(entry, dict):
            var_name = entry.get("variable", "")
            if var_name:
                result.append(str(var_name))
    return result


# --- File loaders --------------------------------------------------------


def safe_load_yaml(file_path: Path) -> dict[str, Any] | None:
    """Load a YAML file, returning None on any error.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Parsed dict, or None if malformed or unreadable.
    """
    try:
        raw = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def safe_load_json(file_path: Path) -> dict[str, Any] | None:
    """Load a JSON file, returning None on any error.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed dict, or None if malformed or unreadable.
    """
    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


# --- Schema / description helpers ----------------------------------------


def is_dify_manifest(data: dict[str, Any]) -> bool:
    """Check if a parsed dict looks like a Dify plugin manifest.

    Args:
        data: Parsed YAML/JSON dict.

    Returns:
        True if the data matches Dify manifest schema heuristics.
    """
    plugin_type = data.get("type", "")
    return str(plugin_type).lower() in DIFY_PLUGIN_TYPES


def extract_tool_descriptions(data: dict[str, Any]) -> str:
    """Extract human-readable description text from tool blocks.

    Args:
        data: Parsed manifest dict.

    Returns:
        Concatenated description text.
    """
    parts: list[str] = []
    description = data.get("description", "")
    if isinstance(description, str):
        parts.append(description)
    elif isinstance(description, dict):
        for value in description.values():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, dict):
                parts.extend(str(val) for val in value.values())

    tool_block = data.get("tool", {})
    if isinstance(tool_block, dict):
        tool_desc = tool_block.get("description", {})
        if isinstance(tool_desc, dict):
            for lang_block in tool_desc.values():
                if isinstance(lang_block, str):
                    parts.append(lang_block)
                elif isinstance(lang_block, dict):
                    parts.extend(str(val) for val in lang_block.values())
    return "\n".join(parts)


def parse_multi_tools(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract individual tool definitions from a multi-tool manifest.

    Args:
        data: Parsed manifest dict.

    Returns:
        List of tool definition dicts.
    """
    tools = data.get("tools", [])
    if not isinstance(tools, list):
        return []
    return [tool for tool in tools if isinstance(tool, dict)]


def extract_dependencies(data: dict[str, Any]) -> list[str]:
    """Extract dependency declarations from manifest.

    Args:
        data: Parsed manifest dict.

    Returns:
        List of dependency strings.
    """
    deps = data.get("dependencies", [])
    if not isinstance(deps, list):
        return []
    return [str(dep) for dep in deps]
