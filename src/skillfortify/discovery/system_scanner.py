"""System-wide auto-discovery scanner for AI IDE configurations.

Scans the user's home directory for all installed AI development tools,
parses their MCP configurations and skill directories, and runs static
analysis on everything found. This powers the zero-argument
``skillfortify scan`` experience.

Discovery Algorithm:
    1. Known-IDE scan: check each ``IDEProfile`` against the home dir.
    2. Unknown-IDE heuristic: scan ``~/.*`` for any hidden directory
       containing MCP config filenames or skill subdirectories.
    3. For each discovered IDE, use ``ParserRegistry`` to parse skills.
    4. Run ``StaticAnalyzer`` on all parsed skills.
"""

from __future__ import annotations

import logging
import platform
from pathlib import Path

from skillfortify.core.analyzer import StaticAnalyzer
from skillfortify.discovery.ide_registry import (
    IDE_PROFILES,
    IDEProfile,
    MCP_CONFIG_FILENAMES,
)
from skillfortify.discovery.models import DiscoveredIDE, SystemScanResult
from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.registry import ParserRegistry, default_registry

logger = logging.getLogger(__name__)

# Dot-dirs already claimed by known profiles (stripped of leading dot).
_KNOWN_DOT_DIRS: set[str] = set()
for _prof in IDE_PROFILES:
    for _dd in _prof.dot_dirs:
        _KNOWN_DOT_DIRS.add(_dd.lstrip("."))


class SystemScanner:
    """Discovers and scans all AI IDE configurations on the system.

    Usage::

        scanner = SystemScanner()
        result = scanner.scan_system()
        for ide in result.ides_found:
            print(f"Found {ide.profile.name} at {ide.path}")
    """

    def _get_home(self, home: Path | None = None) -> Path:
        """Resolve the home directory to scan."""
        return home if home is not None else Path.home()

    def _current_platform(self) -> str:
        """Return the current platform identifier."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return "windows" if system == "windows" else "linux"

    def _profile_matches_platform(self, profile: IDEProfile) -> bool:
        """Check if an IDE profile applies to the current platform."""
        return profile.platform == "all" or profile.platform == self._current_platform()

    def _find_mcp_configs(self, base: Path) -> list[Path]:
        """Find MCP config files under a directory (up to 3 levels deep)."""
        configs: list[Path] = []
        try:
            for pattern in MCP_CONFIG_FILENAMES:
                for depth in [pattern, f"*/{pattern}", f"*/*/{pattern}"]:
                    try:
                        configs.extend(base.glob(depth))
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        return configs

    def _find_skill_dirs(self, base: Path) -> list[Path]:
        """Find 'skills' directories under a base path (up to 2 levels)."""
        dirs: list[Path] = []
        for pattern in ["skills", "*/skills"]:
            try:
                for match in base.glob(pattern):
                    if match.is_dir():
                        dirs.append(match)
            except (PermissionError, OSError):
                continue
        return dirs

    def discover_ides(self, home: Path | None = None) -> list[DiscoveredIDE]:
        """Find all AI IDEs/tools installed on the system.

        Args:
            home: Override the home directory (for testing).

        Returns:
            List of discovered IDEs, known profiles first, then unknowns.
        """
        home_dir = self._get_home(home)
        discovered: list[DiscoveredIDE] = []
        discovered.extend(self._discover_known_ides(home_dir))
        discovered.extend(self._discover_unknown_ides(home_dir))
        return discovered

    def _discover_known_ides(self, home_dir: Path) -> list[DiscoveredIDE]:
        """Check known IDE profiles against the home directory."""
        discovered: list[DiscoveredIDE] = []
        for profile in IDE_PROFILES:
            if not self._profile_matches_platform(profile):
                continue
            ide = self._probe_profile(home_dir, profile)
            if ide is not None:
                discovered.append(ide)
        return discovered

    def _probe_profile(self, home_dir: Path, profile: IDEProfile) -> DiscoveredIDE | None:
        """Probe a single IDE profile against the home directory."""
        found_path: Path | None = None
        for dot_dir in profile.dot_dirs:
            candidate = home_dir / dot_dir
            try:
                if candidate.is_dir():
                    found_path = candidate
                    break
            except (PermissionError, OSError):
                continue

        if found_path is None:
            return None

        mcp_configs: list[Path] = []
        for config_rel in profile.config_paths:
            config_path = home_dir / config_rel
            try:
                if config_path.is_file():
                    mcp_configs.append(config_path)
            except (PermissionError, OSError):
                continue
        mcp_configs.extend(self._find_mcp_configs(found_path))
        mcp_configs = list(dict.fromkeys(mcp_configs))

        skill_dirs: list[Path] = []
        for skill_rel in profile.skill_paths:
            skill_path = home_dir / skill_rel
            try:
                if skill_path.is_dir():
                    skill_dirs.append(skill_path)
            except (PermissionError, OSError):
                continue
        skill_dirs.extend(self._find_skill_dirs(found_path))
        skill_dirs = list(dict.fromkeys(skill_dirs))

        return DiscoveredIDE(
            profile=profile, path=found_path,
            mcp_configs=mcp_configs, skill_dirs=skill_dirs,
        )

    def _discover_unknown_ides(self, home_dir: Path) -> list[DiscoveredIDE]:
        """Scan for unknown AI tools via MCP config heuristic."""
        discovered: list[DiscoveredIDE] = []
        try:
            entries = sorted(home_dir.iterdir())
        except (PermissionError, OSError):
            return discovered

        for entry in entries:
            if not entry.name.startswith("."):
                continue
            try:
                if not entry.is_dir():
                    continue
            except (PermissionError, OSError):
                continue

            if entry.name.lstrip(".") in _KNOWN_DOT_DIRS:
                continue

            mcp_configs = self._find_mcp_configs(entry)
            skill_dirs = self._find_skill_dirs(entry)
            if mcp_configs or skill_dirs:
                synthetic = IDEProfile(
                    name=f"Unknown ({entry.name})",
                    short_name=entry.name.lstrip("."),
                    dot_dirs=[entry.name],
                )
                discovered.append(DiscoveredIDE(
                    profile=synthetic, path=entry,
                    mcp_configs=mcp_configs, skill_dirs=skill_dirs,
                ))
        return discovered

    def scan_system(self, home: Path | None = None) -> SystemScanResult:
        """Full system scan: discover IDEs, parse skills, analyze.

        Args:
            home: Override the home directory (for testing).

        Returns:
            A ``SystemScanResult`` with all IDEs, skills, and findings.
        """
        ides = self.discover_ides(home=home)
        registry = default_registry()
        analyzer = StaticAnalyzer()

        all_skills: list[ParsedSkill] = []
        for ide in ides:
            all_skills.extend(self._parse_ide_skills(ide, registry))

        all_results = []
        for skill in all_skills:
            try:
                all_results.append(analyzer.analyze(skill))
            except Exception:
                logger.warning("Failed to analyze: %s", skill.name, exc_info=True)

        return SystemScanResult(
            ides_found=ides, total_skills=len(all_skills),
            skills=all_skills, results=all_results,
        )

    def _parse_ide_skills(
        self, ide: DiscoveredIDE, registry: ParserRegistry,
    ) -> list[ParsedSkill]:
        """Parse all skills from a discovered IDE."""
        skills: list[ParsedSkill] = []
        scan_paths: list[Path] = [ide.path]
        for skill_dir in ide.skill_dirs:
            if skill_dir not in scan_paths:
                scan_paths.append(skill_dir)
        for mcp_config in ide.mcp_configs:
            config_parent = mcp_config.parent
            if config_parent not in scan_paths:
                scan_paths.append(config_parent)

        seen_names: set[str] = set()
        for scan_path in scan_paths:
            try:
                for skill in registry.discover(scan_path):
                    if skill.name not in seen_names:
                        seen_names.add(skill.name)
                        skills.append(skill)
            except (PermissionError, OSError):
                logger.warning("Permission denied: %s", scan_path)
            except Exception:
                logger.warning("Error scanning: %s", scan_path, exc_info=True)
        return skills
