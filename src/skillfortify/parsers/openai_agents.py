"""Parser for OpenAI Agents SDK tool definitions.

Detects and analyses Python files that use the ``agents`` package (the
OpenAI Agents SDK, which replaced Swarm). Extracted entities include:

- ``@function_tool`` decorated functions (primary tool pattern)
- ``Agent(...)`` instantiations (name, instructions, model, handoffs)
- ``MCPServerStdio`` / ``MCPServerHTTP`` connections
- Hosted tool imports (WebSearchTool, FileSearchTool, CodeInterpreterTool)
- ``InputGuardrail`` / ``OutputGuardrail`` usage
- Agent-to-agent handoff patterns

Heavy AST extraction logic is delegated to
``openai_agents_extractors`` to keep this module focused on the
public ``OpenAIAgentsParser`` class and filesystem probing.

References:
    OpenAI Agents SDK documentation (2025-2026).
    "Agent Skills in the Wild" (arXiv:2601.10338, Jan 2026).
"""

from __future__ import annotations

import ast
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.openai_agents_extractors import (
    extract_agents,
    extract_function_tools,
    extract_hosted_tools,
    extract_mcp_servers,
    regex_fallback,
)

# --------------------------------------------------------------------------- #
# Constants                                                                    #
# --------------------------------------------------------------------------- #

# Import markers that signal OpenAI Agents SDK usage.
_AGENTS_IMPORT_MARKERS = (
    "from agents import",
    "from agents.",
    "from agents ",
    "import agents",
    "from openai.agents",
)

# Package name that appears in pyproject.toml / requirements.txt.
_PIP_PACKAGE = "openai-agents"

# Subdirectories to probe for agent Python files.
_SEARCH_SUBDIRS = ("tools", "agents", "src")

# Maximum bytes to read for the fast ``can_parse`` probe.
_HEAD_BYTES = 4096


# --------------------------------------------------------------------------- #
# Filesystem helpers                                                           #
# --------------------------------------------------------------------------- #

def _has_agents_imports(text: str) -> bool:
    """Return True if *text* contains OpenAI Agents SDK import markers."""
    return any(marker in text for marker in _AGENTS_IMPORT_MARKERS)


def _has_agents_dependency(path: Path) -> bool:
    """Check pyproject.toml or requirements*.txt for openai-agents."""
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

class OpenAIAgentsParser(SkillParser):
    """Parser for OpenAI Agents SDK tool definitions.

    Detects Python files using the ``agents`` package and extracts
    ``@function_tool`` functions, ``Agent(...)`` instantiations,
    MCP server connections, hosted tool imports, guardrails, and
    handoffs.
    """

    def can_parse(self, path: Path) -> bool:
        """Check if *path* contains OpenAI Agents SDK definitions.

        Probes for:
        1. ``openai-agents`` in requirements or pyproject.toml.
        2. Python files with ``from agents import`` markers.

        Args:
            path: Root directory to probe.

        Returns:
            True if Agents SDK patterns are detected.
        """
        if _has_agents_dependency(path):
            return True
        return bool(self._find_agent_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all OpenAI Agents SDK skills in *path*.

        Args:
            path: Root directory to scan.

        Returns:
            List of ``ParsedSkill`` instances. Empty if nothing found.
        """
        results: list[ParsedSkill] = []
        for py_file in self._find_agent_files(path):
            results.extend(self._parse_file(py_file))
        return results

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _parse_file(self, py_file: Path) -> list[ParsedSkill]:
        """Parse a single Python file for Agents SDK patterns."""
        try:
            source = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return regex_fallback(source, py_file)

        skills: list[ParsedSkill] = []
        skills.extend(extract_function_tools(tree, source, py_file))
        skills.extend(extract_agents(tree, source, py_file))
        skills.extend(extract_hosted_tools(tree, source, py_file))
        skills.extend(extract_mcp_servers(tree, source, py_file))
        return skills

    def _find_agent_files(self, path: Path) -> list[Path]:
        """Find Python files containing Agents SDK patterns."""
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
                if _has_agents_imports(head):
                    candidates.append(py_file)
        return candidates
