"""Parser for LlamaIndex tool and agent definitions.

Extracts security-relevant metadata from Python files that use the
LlamaIndex framework (``llama_index``). Covers:

- **FunctionTool** definitions (``FunctionTool.from_defaults(fn=...)``)
- **QueryEngineTool** constructors with ``ToolMetadata``
- **Agent** configurations (``ReActAgent``, ``FunctionCallingAgent``)
- **Data reader / connector** usage (``SimpleWebPageReader``, etc.)
- **LLM provider** configurations (``OpenAI``, ``Anthropic``, etc.)
- URLs, environment variables, shell commands, and import dependencies

LlamaIndex is a major RAG framework (47K GitHub stars, 300+ LlamaHub
packages). Its tool and agent surface area is a key supply chain
attack vector for agentic AI applications.

References:
    "Agent Skills in the Wild" (arXiv:2601.10338, Jan 2026).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.llamaindex_extractors import (
    build_skill,
    is_agent_from_tools,
    is_data_reader,
    is_function_tool_call,
    is_query_engine_tool,
    parse_agent_call,
    parse_data_reader,
    parse_function_tool,
    parse_query_engine_tool,
)

_LLAMA_IMPORT_MARKERS = (
    "from llama_index",
    "import llama_index",
)

_TOOL_DIR_NAMES = {"tools", "llamaindex_tools", "agents"}


def _has_llama_imports(text: str) -> bool:
    """Check if *text* contains LlamaIndex import statements."""
    return any(marker in text for marker in _LLAMA_IMPORT_MARKERS)


def _extract_tools_from_source(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Parse a Python source file and extract LlamaIndex definitions.

    Uses the AST to walk through all ``ast.Call`` nodes and dispatch to
    the appropriate extractor based on the call target. Falls back to
    regex for files with syntax errors.

    Args:
        source: Full Python source text.
        file_path: Absolute path to the source file on disk.

    Returns:
        List of ``ParsedSkill`` instances found in the file.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _regex_fallback(source, file_path)

    results: list[ParsedSkill] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if is_function_tool_call(node):
            results.append(parse_function_tool(node, source, file_path))
        elif is_query_engine_tool(node):
            results.append(parse_query_engine_tool(node, source, file_path))
        elif is_agent_from_tools(node):
            results.append(parse_agent_call(node, source, file_path))
        elif is_data_reader(node):
            results.append(parse_data_reader(node, source, file_path))
    return results


def _regex_fallback(
    source: str, file_path: Path,
) -> list[ParsedSkill]:
    """Regex fallback for files that fail AST parsing.

    Attempts to find tool definitions using simple patterns when the
    source cannot be parsed into an AST (syntax errors, incomplete
    files, etc.).

    Args:
        source: Full Python source text (potentially malformed).
        file_path: Absolute path to the source file on disk.

    Returns:
        List of ``ParsedSkill`` instances extracted via regex.
    """
    results: list[ParsedSkill] = []
    patterns = (
        (r"FunctionTool\.from_defaults\s*\(", "function_tool"),
        (r"QueryEngineTool\s*\(", "query_engine_tool"),
        (r"ReActAgent\.from_tools\s*\(", "react_agent"),
    )
    for pattern, label in patterns:
        for _match in re.finditer(pattern, source):
            results.append(
                build_skill(label, "", source, file_path, source),
            )
    return results


class LlamaIndexParser(SkillParser):
    """Parser for LlamaIndex tool and agent definitions in Python files.

    Detects files containing ``from llama_index`` imports and extracts
    FunctionTool, QueryEngineTool, Agent, and data reader definitions.
    The parser scans the root directory and common subdirectories
    (``tools/``, ``agents/``, ``llamaindex_tools/``).
    """

    def can_parse(self, path: Path) -> bool:
        """Return True if *path* contains LlamaIndex tool files.

        Args:
            path: Root directory to probe.

        Returns:
            True if at least one Python file with LlamaIndex imports
            was found.
        """
        return bool(self._find_tool_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all LlamaIndex tool files under *path*.

        Reads each candidate Python file, extracts tool/agent/reader
        definitions, and returns a flat list of ``ParsedSkill`` objects.

        Args:
            path: Root directory to scan.

        Returns:
            List of ``ParsedSkill`` instances. Empty if no skills found
            or all files are malformed.
        """
        results: list[ParsedSkill] = []
        for py_file in self._find_tool_files(path):
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            results.extend(_extract_tools_from_source(source, py_file))
        return results

    def _find_tool_files(self, path: Path) -> list[Path]:
        """Find Python files containing LlamaIndex import markers.

        Searches the root directory and well-known subdirectories for
        ``.py`` files whose first 4 KiB contain a LlamaIndex import
        statement.

        Args:
            path: Root directory to search.

        Returns:
            Sorted list of candidate Python file paths.
        """
        candidates: list[Path] = []
        search_dirs = [path]
        for dir_name in _TOOL_DIR_NAMES:
            sub = path / dir_name
            if sub.is_dir():
                search_dirs.append(sub)
        for search_dir in search_dirs:
            for py_file in sorted(search_dir.glob("*.py")):
                try:
                    head = py_file.read_text(encoding="utf-8")[:4096]
                except (OSError, UnicodeDecodeError):
                    continue
                if _has_llama_imports(head):
                    candidates.append(py_file)
        return candidates
