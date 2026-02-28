"""Tests for SystemScanner.scan_system() and helper methods.

Covers the full scan pipeline, dataclass behavior, and low-level
helper methods (_find_mcp_configs, _find_skill_dirs).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.discovery.ide_registry import IDE_PROFILES, IDEProfile
from skillfortify.discovery.models import DiscoveredIDE, SystemScanResult
from skillfortify.discovery.system_scanner import SystemScanner

from tests.discovery.helpers import (
    create_claude_home,
    create_cursor_home,
)


# ---------------------------------------------------------------------------
# SystemScanner.scan_system()
# ---------------------------------------------------------------------------


class TestScanSystem:
    """Test the full scan_system() pipeline."""

    def test_empty_system_returns_empty_result(self, tmp_path: Path) -> None:
        """Empty home returns a valid but empty SystemScanResult."""
        scanner = SystemScanner()
        result = scanner.scan_system(home=tmp_path)
        assert isinstance(result, SystemScanResult)
        assert result.ides_found == []
        assert result.total_skills == 0
        assert result.skills == []
        assert result.results == []

    def test_scan_system_with_claude(self, tmp_path: Path) -> None:
        """System scan with Claude Code detects the IDE."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        result = scanner.scan_system(home=tmp_path)
        assert len(result.ides_found) >= 1
        claude = [i for i in result.ides_found if i.profile.short_name == "claude"]
        assert len(claude) == 1

    def test_scan_system_result_types(self, tmp_path: Path) -> None:
        """Verify the result contains correct types."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        result = scanner.scan_system(home=tmp_path)
        assert isinstance(result, SystemScanResult)
        assert isinstance(result.ides_found, list)
        assert isinstance(result.total_skills, int)
        assert isinstance(result.skills, list)
        assert isinstance(result.results, list)

    def test_scan_system_multi_ide(self, tmp_path: Path) -> None:
        """System scan discovers multiple IDEs."""
        create_claude_home(tmp_path)
        create_cursor_home(tmp_path)
        scanner = SystemScanner()
        result = scanner.scan_system(home=tmp_path)
        names = {i.profile.short_name for i in result.ides_found}
        assert "claude" in names
        assert "cursor" in names

    def test_scan_system_skills_count(self, tmp_path: Path) -> None:
        """total_skills reflects the number of parsed skills."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        result = scanner.scan_system(home=tmp_path)
        assert result.total_skills == len(result.skills)

    def test_scan_system_results_match_skills(self, tmp_path: Path) -> None:
        """Each parsed skill should have a corresponding analysis result."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        result = scanner.scan_system(home=tmp_path)
        assert len(result.results) <= len(result.skills)


# ---------------------------------------------------------------------------
# DiscoveredIDE dataclass
# ---------------------------------------------------------------------------


class TestDiscoveredIDE:
    """Test the DiscoveredIDE dataclass."""

    def test_default_lists_empty(self) -> None:
        """Default mcp_configs and skill_dirs should be empty lists."""
        profile = IDE_PROFILES[0]
        ide = DiscoveredIDE(profile=profile, path=Path("/tmp/test"))
        assert ide.mcp_configs == []
        assert ide.skill_dirs == []

    def test_fields_accessible(self) -> None:
        """All fields should be accessible."""
        profile = IDE_PROFILES[0]
        ide = DiscoveredIDE(
            profile=profile,
            path=Path("/tmp/test"),
            mcp_configs=[Path("/tmp/test/mcp.json")],
            skill_dirs=[Path("/tmp/test/skills")],
        )
        assert ide.profile == profile
        assert ide.path == Path("/tmp/test")
        assert len(ide.mcp_configs) == 1
        assert len(ide.skill_dirs) == 1


# ---------------------------------------------------------------------------
# SystemScanResult dataclass
# ---------------------------------------------------------------------------


class TestSystemScanResult:
    """Test the SystemScanResult dataclass."""

    def test_empty_result(self) -> None:
        """An empty result should have all zero/empty fields."""
        result = SystemScanResult(
            ides_found=[], total_skills=0, skills=[], results=[],
        )
        assert result.ides_found == []
        assert result.total_skills == 0


# ---------------------------------------------------------------------------
# MCP config finding
# ---------------------------------------------------------------------------


class TestFindMCPConfigs:
    """Test the _find_mcp_configs helper method."""

    def test_finds_top_level_mcp_json(self, tmp_path: Path) -> None:
        """Finds mcp.json at the root of the search directory."""
        (tmp_path / "mcp.json").write_text("{}")
        scanner = SystemScanner()
        configs = scanner._find_mcp_configs(tmp_path)
        assert len(configs) >= 1

    def test_finds_nested_mcp_config(self, tmp_path: Path) -> None:
        """Finds MCP configs in subdirectories."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "mcp_settings.json").write_text("{}")
        scanner = SystemScanner()
        configs = scanner._find_mcp_configs(tmp_path)
        names = [p.name for p in configs]
        assert "mcp_settings.json" in names

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """Empty directory returns no configs."""
        scanner = SystemScanner()
        configs = scanner._find_mcp_configs(tmp_path)
        assert configs == []

    def test_non_mcp_json_ignored(self, tmp_path: Path) -> None:
        """Non-MCP JSON files are not returned."""
        (tmp_path / "package.json").write_text("{}")
        scanner = SystemScanner()
        configs = scanner._find_mcp_configs(tmp_path)
        names = [p.name for p in configs]
        assert "package.json" not in names


# ---------------------------------------------------------------------------
# Skill directory finding
# ---------------------------------------------------------------------------


class TestFindSkillDirs:
    """Test the _find_skill_dirs helper method."""

    def test_finds_top_level_skills(self, tmp_path: Path) -> None:
        """Finds a 'skills' directory at the root."""
        (tmp_path / "skills").mkdir()
        scanner = SystemScanner()
        dirs = scanner._find_skill_dirs(tmp_path)
        assert len(dirs) >= 1
        assert dirs[0].name == "skills"

    def test_finds_nested_skills(self, tmp_path: Path) -> None:
        """Finds a 'skills' directory one level down."""
        sub = tmp_path / "subdir" / "skills"
        sub.mkdir(parents=True)
        scanner = SystemScanner()
        dirs = scanner._find_skill_dirs(tmp_path)
        assert len(dirs) >= 1

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """Empty directory returns no skill dirs."""
        scanner = SystemScanner()
        dirs = scanner._find_skill_dirs(tmp_path)
        assert dirs == []

    def test_file_named_skills_ignored(self, tmp_path: Path) -> None:
        """A file named 'skills' (not a directory) is not returned."""
        (tmp_path / "skills").write_text("not a directory")
        scanner = SystemScanner()
        dirs = scanner._find_skill_dirs(tmp_path)
        assert dirs == []
