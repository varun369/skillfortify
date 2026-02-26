"""Parser registry for auto-detecting agent skill formats.

The ``ParserRegistry`` orchestrates skill discovery by maintaining a list
of registered ``SkillParser`` instances and probing each one against a
target directory. This enables the ``skillfortify scan <path>`` command to
automatically detect Claude Code, MCP, and OpenClaw formats without
the user specifying which parser to use.

The design follows the classic Registry pattern (Fowler, 2002) with a
functional ``default_registry()`` factory that pre-registers all built-in
parsers. Custom parsers can be added via ``register()`` for extensibility
-- important for future format support (e.g., LangChain tools, AutoGen
agents).

Discovery Algorithm
-------------------
``discover(path)`` iterates over registered parsers in registration order:

1. For each parser, call ``can_parse(path)``.
2. If True, call ``parse(path)`` and collect the results.
3. Continue to the next parser (a directory may contain multiple formats).
4. Return the aggregated list of ``ParsedSkill`` instances.

This is intentionally simple -- O(n) in the number of registered parsers,
where n is typically 3. The ``can_parse()`` calls are cheap filesystem probes.
"""

from __future__ import annotations

from pathlib import Path

from skillfortify.parsers.autogen import AutoGenParser
from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.claude_skills import ClaudeSkillsParser
from skillfortify.parsers.crewai import CrewAIParser
from skillfortify.parsers.langchain import LangChainParser
from skillfortify.parsers.mcp_config import McpConfigParser
from skillfortify.parsers.openclaw import OpenClawParser


class ParserRegistry:
    """Registry of skill parsers for auto-discovery.

    Maintains an ordered list of ``SkillParser`` instances. The ``discover()``
    method tries each parser against a directory and aggregates results.

    Attributes:
        parsers: Ordered list of registered parser instances.
    """

    def __init__(self) -> None:
        self.parsers: list[SkillParser] = []

    def register(self, parser: SkillParser) -> None:
        """Add a parser to the registry.

        Parsers are tried in registration order during ``discover()``.

        Args:
            parser: A ``SkillParser`` instance to register.
        """
        self.parsers.append(parser)

    def discover(self, path: Path) -> list[ParsedSkill]:
        """Discover all skills in a directory using registered parsers.

        Tries each registered parser's ``can_parse()`` method against the
        directory. For every parser that returns True, calls ``parse()``
        and collects the results. A single directory may yield skills from
        multiple formats (e.g., a project with both ``.claude/skills/``
        and ``mcp.json``).

        Args:
            path: Root directory to scan for skills.

        Returns:
            Aggregated list of ``ParsedSkill`` instances from all parsers
            that matched. Empty if no parsers matched or no skills found.
        """
        all_skills: list[ParsedSkill] = []
        for parser in self.parsers:
            if parser.can_parse(path):
                skills = parser.parse(path)
                all_skills.extend(skills)
        return all_skills


def default_registry() -> ParserRegistry:
    """Create a ParserRegistry pre-loaded with all built-in parsers.

    The default registry includes:
    1. ``ClaudeSkillsParser`` -- Claude Code skills (.claude/skills/*.md)
    2. ``McpConfigParser`` -- MCP server configs (mcp.json, etc.)
    3. ``OpenClawParser`` -- OpenClaw skills (.claw/*.yaml)
    4. ``LangChainParser`` -- LangChain tools (BaseTool / @tool in .py)
    5. ``CrewAIParser`` -- CrewAI tools (crew.yaml + BaseTool in .py)
    6. ``AutoGenParser`` -- AutoGen tools (register_for_llm / schemas)

    Returns:
        A ParserRegistry with all six built-in parsers registered.
    """
    registry = ParserRegistry()
    registry.register(ClaudeSkillsParser())
    registry.register(McpConfigParser())
    registry.register(OpenClawParser())
    registry.register(LangChainParser())
    registry.register(CrewAIParser())
    registry.register(AutoGenParser())
    return registry
