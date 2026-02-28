"""Data models for the discovery module.

Contains the result types produced by ``SystemScanner``: individual IDE
discovery records and the aggregate system scan result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skillfortify.core.analyzer import AnalysisResult
from skillfortify.discovery.ide_registry import IDEProfile
from skillfortify.parsers.base import ParsedSkill


@dataclass
class DiscoveredIDE:
    """A single AI IDE/tool discovered on the system.

    Attributes:
        profile: The matching ``IDEProfile`` (or a synthetic one for
            unknown tools discovered by the heuristic scanner).
        path: Absolute path to the IDE's dot-directory.
        mcp_configs: MCP configuration files found within this IDE.
        skill_dirs: Skill directories found within this IDE.
    """

    profile: IDEProfile
    path: Path
    mcp_configs: list[Path] = field(default_factory=list)
    skill_dirs: list[Path] = field(default_factory=list)


@dataclass
class SystemScanResult:
    """Complete result of a system-wide scan.

    Attributes:
        ides_found: All AI tools discovered on the system.
        total_skills: Count of skills parsed across all IDEs.
        skills: All parsed skills from all IDEs.
        results: Static analysis results for each parsed skill.
    """

    ides_found: list[DiscoveredIDE]
    total_skills: int
    skills: list[ParsedSkill]
    results: list[AnalysisResult]
