"""Base interface and data structures for agent skill parsers.

Every parser in SkillShield implements the ``SkillParser`` abstract base class,
which provides two methods:

- ``can_parse(path)`` -- Probe a directory to determine if this parser can
  handle the skill format found there.
- ``parse(path)`` -- Extract all security-relevant metadata from the skills
  in that directory.

The ``ParsedSkill`` dataclass is the universal intermediate representation
for all skill formats. It captures everything the downstream static analyser,
capability lattice, and threat model need without coupling to any single
format's schema.

The fields are chosen to cover the attack surfaces identified in the DY-Skill
threat model:

- **shell_commands**: Potential EXECUTE-phase attacks (shell access).
- **urls**: Potential DATA_EXFILTRATION endpoints.
- **env_vars_referenced**: Potential credential exposure (DEPLOY_TOKEN, etc.).
- **dependencies**: Transitive supply chain attack surface.
- **code_blocks**: Raw code for deeper static analysis.
- **declared_capabilities**: What the skill claims it can do (input to POLA check).

References:
    "Agent Skills in the Wild" (arXiv:2601.10338, Jan 2026). Identified 14
    vulnerability patterns across 42,447 skills -- our ParsedSkill fields
    are designed to capture signals for all 14 patterns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedSkill:
    """Universal intermediate representation for a parsed agent skill.

    This dataclass captures all security-relevant metadata regardless of the
    source format (Claude, MCP, OpenClaw). Downstream analysers operate on
    this representation rather than format-specific structures.

    Attributes:
        name: Human-readable skill identifier (e.g., "weather-api").
        version: Semantic version string. Defaults to "unknown" when the
            format does not declare a version.
        source_path: Absolute path to the skill file on disk.
        format: Parser format identifier ("claude", "mcp", "openclaw").
        description: Short human-readable summary of what the skill does.
        instructions: Full instruction text (prompts, usage guides).
        declared_capabilities: Capability strings the skill explicitly claims
            (e.g., ["network:read", "filesystem:write"]).
        dependencies: Package/skill names this skill depends on.
        code_blocks: Extracted code blocks from documentation or config.
        urls: All URLs referenced in the skill content.
        env_vars_referenced: Environment variable names found in the content.
            Particularly security-sensitive when matching patterns like
            SECRET, KEY, TOKEN, PASSWORD, CREDENTIAL.
        shell_commands: Shell command strings found in the skill content.
        raw_content: The complete raw text of the skill file, preserved
            for deeper analysis passes.
    """

    name: str
    version: str
    source_path: Path
    format: str  # "claude", "mcp", "openclaw"
    description: str = ""
    instructions: str = ""
    declared_capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    env_vars_referenced: list[str] = field(default_factory=list)
    shell_commands: list[str] = field(default_factory=list)
    raw_content: str = ""


class SkillParser(ABC):
    """Abstract base class for agent skill parsers.

    Each concrete parser knows how to detect and extract skills from a
    specific format. The two-phase API (probe then parse) allows the
    ``ParserRegistry`` to efficiently try multiple parsers against a
    directory without committing to a full parse until a match is found.
    """

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Probe a directory to determine if this parser can handle it.

        The check should be fast and based on file/directory existence,
        not on full content parsing. For example, the Claude parser checks
        for ``.claude/skills/*.md`` files.

        Args:
            path: Root directory to probe.

        Returns:
            True if the directory contains skills this parser understands.
        """

    @abstractmethod
    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all skills found in the given directory.

        Must not raise on malformed content -- return an empty list or
        skip individual malformed files while parsing the rest.

        Args:
            path: Root directory to scan.

        Returns:
            List of ``ParsedSkill`` instances. Empty if no skills found
            or all files are malformed.
        """
