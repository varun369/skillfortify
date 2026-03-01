"""Tests for SystemScanner IDE discovery and edge case handling.

Uses temporary directories to simulate various home directory layouts:
single IDE, multiple IDEs, unknown IDEs, empty homes, and permission
errors.
"""

from __future__ import annotations

from pathlib import Path


from skillfortify.discovery.ide_registry import IDEProfile
from skillfortify.discovery.system_scanner import SystemScanner

from tests.discovery.helpers import (
    create_claude_home,
    create_cursor_home,
    create_non_ai_dotdir,
    create_unknown_ide_home,
    create_unknown_ide_with_skills,
    create_windsurf_home,
)


# ---------------------------------------------------------------------------
# SystemScanner.discover_ides()
# ---------------------------------------------------------------------------


class TestDiscoverIDEs:
    """Test IDE discovery against simulated home directories."""

    def test_empty_home(self, tmp_path: Path) -> None:
        """Empty home directory yields no discovered IDEs."""
        scanner = SystemScanner()
        result = scanner.discover_ides(home=tmp_path)
        assert result == []

    def test_discover_claude(self, tmp_path: Path) -> None:
        """Discovers Claude Code when .claude/ exists."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        claude_ides = [i for i in ides if i.profile.short_name == "claude"]
        assert len(claude_ides) == 1
        assert claude_ides[0].path == tmp_path / ".claude"

    def test_discover_claude_mcp_config(self, tmp_path: Path) -> None:
        """Claude discovery finds the MCP config file."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        claude = [i for i in ides if i.profile.short_name == "claude"][0]
        config_names = [p.name for p in claude.mcp_configs]
        assert "mcp_servers.json" in config_names

    def test_discover_claude_skill_dirs(self, tmp_path: Path) -> None:
        """Claude discovery finds the skills directory."""
        create_claude_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        claude = [i for i in ides if i.profile.short_name == "claude"][0]
        skill_dir_names = [p.name for p in claude.skill_dirs]
        assert "skills" in skill_dir_names

    def test_discover_cursor(self, tmp_path: Path) -> None:
        """Discovers Cursor when .cursor/ exists."""
        create_cursor_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        cursor_ides = [i for i in ides if i.profile.short_name == "cursor"]
        assert len(cursor_ides) == 1

    def test_discover_cursor_mcp_config(self, tmp_path: Path) -> None:
        """Cursor discovery finds the mcp.json config."""
        create_cursor_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        cursor = [i for i in ides if i.profile.short_name == "cursor"][0]
        config_names = [p.name for p in cursor.mcp_configs]
        assert "mcp.json" in config_names

    def test_discover_windsurf(self, tmp_path: Path) -> None:
        """Discovers Windsurf when .codeium/ exists."""
        create_windsurf_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        windsurf_ides = [i for i in ides if i.profile.short_name == "windsurf"]
        assert len(windsurf_ides) == 1

    def test_discover_multiple_ides(self, tmp_path: Path) -> None:
        """Discovers multiple IDEs when several are installed."""
        create_claude_home(tmp_path)
        create_cursor_home(tmp_path)
        create_windsurf_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        short_names = {i.profile.short_name for i in ides}
        assert "claude" in short_names
        assert "cursor" in short_names
        assert "windsurf" in short_names

    def test_non_ai_dotdir_not_discovered(self, tmp_path: Path) -> None:
        """Regular dot-directories (like .git) are not reported."""
        create_non_ai_dotdir(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        names = [i.profile.short_name for i in ides]
        assert "git" not in names

    def test_discover_unknown_ide_with_mcp(self, tmp_path: Path) -> None:
        """Unknown IDEs with MCP configs are discovered by heuristic."""
        create_unknown_ide_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        unknown = [i for i in ides if "mysterytool" in i.profile.short_name]
        assert len(unknown) == 1
        assert "Unknown" in unknown[0].profile.name

    def test_discover_unknown_ide_with_skills(self, tmp_path: Path) -> None:
        """Unknown IDEs with skills directories are discovered."""
        create_unknown_ide_with_skills(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        unknown = [i for i in ides if "newagent" in i.profile.short_name]
        assert len(unknown) == 1
        assert len(unknown[0].skill_dirs) >= 1

    def test_mixed_known_and_unknown(self, tmp_path: Path) -> None:
        """Both known and unknown IDEs are discovered together."""
        create_claude_home(tmp_path)
        create_unknown_ide_home(tmp_path)
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        names = [i.profile.short_name for i in ides]
        assert "claude" in names
        assert "mysterytool" in names


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test graceful handling of unusual filesystem conditions."""

    def test_permission_error_on_dotdir(self, tmp_path: Path) -> None:
        """Scanner does not crash when a dot-directory is unreadable."""
        restricted = tmp_path / ".restricted"
        restricted.mkdir()
        restricted.chmod(0o000)
        try:
            scanner = SystemScanner()
            ides = scanner.discover_ides(home=tmp_path)
            assert isinstance(ides, list)
        finally:
            restricted.chmod(0o755)

    def test_broken_symlink_in_home(self, tmp_path: Path) -> None:
        """Scanner handles broken symlinks without crashing."""
        broken = tmp_path / ".broken_link"
        broken.symlink_to(tmp_path / "nonexistent_target")
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        assert isinstance(ides, list)

    def test_file_instead_of_dir(self, tmp_path: Path) -> None:
        """A file named like a dot-dir is skipped."""
        fake_file = tmp_path / ".claude"
        fake_file.write_text("I am a file, not a directory")
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        claude_ides = [i for i in ides if i.profile.short_name == "claude"]
        assert len(claude_ides) == 0

    def test_empty_mcp_config(self, tmp_path: Path) -> None:
        """Empty MCP config files are still detected (file exists)."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        (cursor_dir / "mcp.json").write_text("")
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        cursor_ides = [i for i in ides if i.profile.short_name == "cursor"]
        assert len(cursor_ides) == 1
        assert len(cursor_ides[0].mcp_configs) >= 1

    def test_nested_mcp_config(self, tmp_path: Path) -> None:
        """MCP configs in subdirectories are found."""
        deep = tmp_path / ".codeium" / "windsurf"
        deep.mkdir(parents=True)
        (deep / "mcp_config.json").write_text("{}")
        scanner = SystemScanner()
        ides = scanner.discover_ides(home=tmp_path)
        windsurf_ides = [i for i in ides if i.profile.short_name == "windsurf"]
        assert len(windsurf_ides) == 1
        config_names = [p.name for p in windsurf_ides[0].mcp_configs]
        assert "mcp_config.json" in config_names


# ---------------------------------------------------------------------------
# Platform filtering
# ---------------------------------------------------------------------------


class TestPlatformFiltering:
    """Test platform-specific IDE profile filtering."""

    def test_all_platform_always_matches(self) -> None:
        """Profiles with platform='all' match any platform."""
        scanner = SystemScanner()
        profile = IDEProfile(
            name="Test", short_name="test",
            dot_dirs=[".test"], platform="all",
        )
        assert scanner._profile_matches_platform(profile) is True

    def test_wrong_platform_does_not_match(self) -> None:
        """Profiles for a different platform are excluded."""
        scanner = SystemScanner()
        fake_platform = "windows" if scanner._current_platform() != "windows" else "linux"
        profile = IDEProfile(
            name="Test", short_name="test",
            dot_dirs=[".test"], platform=fake_platform,
        )
        assert scanner._profile_matches_platform(profile) is False

    def test_matching_platform_matches(self) -> None:
        """Profiles for the current platform are included."""
        scanner = SystemScanner()
        profile = IDEProfile(
            name="Test", short_name="test",
            dot_dirs=[".test"], platform=scanner._current_platform(),
        )
        assert scanner._profile_matches_platform(profile) is True
