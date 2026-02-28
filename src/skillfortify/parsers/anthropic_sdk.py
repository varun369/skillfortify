"""Parser for Anthropic Agent SDK tool definitions.

Detects and analyses Python files that use the ``claude_agent_sdk``
package (Anthropic's official Agent SDK with hooks and MCP native
support). Extracted entities include:

- ``@tool`` decorated functions (primary tool pattern)
- ``Agent(...)`` instantiations (name, model, tools, instructions)
- ``MCPServer(...)`` connections (command, args)
- ``Hook`` subclass definitions (lifecycle callbacks)
- Sub-agent references (Agent used as tool inside another Agent)

Heavy AST extraction logic is delegated to
``anthropic_sdk_extractors`` to keep this module focused on the
public ``AnthropicSDKParser`` class and filesystem probing.

References:
    Anthropic Agent SDK documentation (2025-2026).
    "Agent Skills in the Wild" (arXiv:2601.10338, Jan 2026).
"""

from __future__ import annotations

import ast
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.anthropic_sdk_extractors import (
    extract_agents,
    extract_hooks,
    extract_mcp_servers,
    extract_tools,
    regex_fallback,
)

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #

_IMPORT_MARKERS = (
    "from claude_agent_sdk",
    "import claude_agent_sdk",
)

_PIP_PACKAGE = "claude-agent-sdk"

_SEARCH_SUBDIRS = ("tools", "agents", "src")

_HEAD_BYTES = 4096


# --------------------------------------------------------------------------- #
# Filesystem helpers                                                           #
# --------------------------------------------------------------------------- #

def _has_sdk_imports(text: str) -> bool:
    """Return True if *text* contains Anthropic Agent SDK import markers."""
    return any(marker in text for marker in _IMPORT_MARKERS)


def _has_sdk_dependency(path: Path) -> bool:
    """Check pyproject.toml or requirements*.txt for claude-agent-sdk."""
    for req_name in ("requirements.txt", "requirements-dev.txt"):
        req_file = path / req_name
        if req_file.is_file():
            try:
                if _PIP_PACKAGE in req_file.read_text(encoding="utf-8"):
                    return True
            except (OSError, UnicodeDecodeError):
                pass
    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        try:
            if _PIP_PACKAGE in pyproject.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            pass
    return False


# --------------------------------------------------------------------------- #
# Public parser class                                                          #
# --------------------------------------------------------------------------- #

class AnthropicSDKParser(SkillParser):
    """Parser for Anthropic Agent SDK tool definitions.

    Detects Python files using the ``claude_agent_sdk`` package and
    extracts ``@tool`` functions, ``Agent(...)`` instantiations,
    ``MCPServer(...)`` connections, and ``Hook`` subclass definitions.
    """

    def can_parse(self, path: Path) -> bool:
        """Check if *path* contains Anthropic Agent SDK definitions.

        Probes for:
        1. ``claude-agent-sdk`` in requirements or pyproject.toml.
        2. Python files with ``from claude_agent_sdk`` import markers.

        Args:
            path: Root directory to probe.

        Returns:
            True if Anthropic SDK patterns are detected.
        """
        if _has_sdk_dependency(path):
            return True
        return bool(self._find_sdk_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Anthropic Agent SDK skills in *path*.

        Args:
            path: Root directory to scan.

        Returns:
            List of ``ParsedSkill`` instances. Empty if nothing found.
        """
        results: list[ParsedSkill] = []
        for py_file in self._find_sdk_files(path):
            results.extend(self._parse_file(py_file))
        return results

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _parse_file(self, py_file: Path) -> list[ParsedSkill]:
        """Parse a single Python file for Anthropic SDK patterns."""
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return regex_fallback(source, py_file)

        skills: list[ParsedSkill] = []
        skills.extend(extract_tools(tree, source, py_file))
        skills.extend(extract_agents(tree, source, py_file))
        skills.extend(extract_mcp_servers(tree, source, py_file))
        skills.extend(extract_hooks(tree, source, py_file))
        return skills

    def _find_sdk_files(self, path: Path) -> list[Path]:
        """Find Python files containing Anthropic SDK patterns."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in _SEARCH_SUBDIRS:
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)
        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:_HEAD_BYTES]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_sdk_imports(head):
                    candidates.append(py_file)
        return candidates
