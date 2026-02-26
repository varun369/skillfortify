"""Skill parsers for Claude Code, MCP, OpenClaw, LangChain, CrewAI, and AutoGen."""

from skillfortify.parsers.autogen import AutoGenParser
from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.claude_skills import ClaudeSkillsParser
from skillfortify.parsers.crewai import CrewAIParser
from skillfortify.parsers.langchain import LangChainParser
from skillfortify.parsers.mcp_config import McpConfigParser
from skillfortify.parsers.openclaw import OpenClawParser
from skillfortify.parsers.registry import ParserRegistry, default_registry

__all__ = [
    "AutoGenParser",
    "ParsedSkill",
    "SkillParser",
    "ClaudeSkillsParser",
    "CrewAIParser",
    "LangChainParser",
    "McpConfigParser",
    "OpenClawParser",
    "ParserRegistry",
    "default_registry",
]
