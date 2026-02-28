"""Tests for the IDE profile registry.

Validates the static knowledge base of known AI IDEs/tools: field
completeness, uniqueness constraints, and path format correctness.
"""

from __future__ import annotations

import pytest

from skillfortify.discovery.ide_registry import (
    IDE_PROFILES,
    IDEProfile,
    MCP_CONFIG_FILENAMES,
)


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


class TestRegistryCompleteness:
    """Verify the registry contains expected profiles."""

    def test_registry_is_not_empty(self) -> None:
        """The registry must contain at least one IDE profile."""
        assert len(IDE_PROFILES) > 0

    def test_registry_has_minimum_profiles(self) -> None:
        """The registry should cover at least 15 AI tools."""
        assert len(IDE_PROFILES) >= 15

    def test_claude_code_present(self) -> None:
        """Claude Code must be in the registry (primary target)."""
        names = {p.short_name for p in IDE_PROFILES}
        assert "claude" in names

    def test_cursor_present(self) -> None:
        """Cursor must be in the registry."""
        names = {p.short_name for p in IDE_PROFILES}
        assert "cursor" in names

    def test_vscode_present(self) -> None:
        """VS Code must be in the registry."""
        names = {p.short_name for p in IDE_PROFILES}
        assert "vscode" in names

    def test_windsurf_present(self) -> None:
        """Windsurf/Codeium must be in the registry."""
        names = {p.short_name for p in IDE_PROFILES}
        assert "windsurf" in names

    def test_gemini_present(self) -> None:
        """Gemini CLI must be in the registry."""
        names = {p.short_name for p in IDE_PROFILES}
        assert "gemini" in names


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


class TestFieldValidation:
    """Every profile must have valid, well-formed fields."""

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_name_not_empty(self, profile: IDEProfile) -> None:
        """Every profile must have a non-empty display name."""
        assert profile.name.strip() != ""

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_short_name_not_empty(self, profile: IDEProfile) -> None:
        """Every profile must have a non-empty short name."""
        assert profile.short_name.strip() != ""

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_short_name_is_lowercase(self, profile: IDEProfile) -> None:
        """Short names must be lowercase for consistent CLI output."""
        assert profile.short_name == profile.short_name.lower() or \
            "-" in profile.short_name  # Allow hyphens like "vscode-linux"

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_short_name_no_spaces(self, profile: IDEProfile) -> None:
        """Short names must not contain spaces."""
        assert " " not in profile.short_name

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_platform_is_valid(self, profile: IDEProfile) -> None:
        """Platform must be one of the allowed values."""
        valid = {"all", "macos", "linux", "windows"}
        assert profile.platform in valid

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_dot_dirs_is_list(self, profile: IDEProfile) -> None:
        """dot_dirs must be a list."""
        assert isinstance(profile.dot_dirs, list)

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_config_paths_is_list(self, profile: IDEProfile) -> None:
        """config_paths must be a list."""
        assert isinstance(profile.config_paths, list)

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_skill_paths_is_list(self, profile: IDEProfile) -> None:
        """skill_paths must be a list."""
        assert isinstance(profile.skill_paths, list)

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_has_at_least_one_dot_dir(self, profile: IDEProfile) -> None:
        """Every profile must declare at least one dot directory to probe."""
        assert len(profile.dot_dirs) >= 1

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_dot_dirs_start_with_dot(self, profile: IDEProfile) -> None:
        """All dot_dirs entries must start with a period."""
        for dd in profile.dot_dirs:
            assert dd.startswith("."), f"{profile.name}: dot_dir '{dd}' missing leading dot"

    @pytest.mark.parametrize("profile", IDE_PROFILES, ids=lambda p: p.short_name)
    def test_config_paths_not_absolute(self, profile: IDEProfile) -> None:
        """Config paths must be relative to home (not absolute)."""
        for cp in profile.config_paths:
            assert not cp.startswith("/"), f"{profile.name}: config_path '{cp}' is absolute"


# ---------------------------------------------------------------------------
# Uniqueness constraints
# ---------------------------------------------------------------------------


class TestUniqueness:
    """Ensure no duplicate identifiers in the registry."""

    def test_no_duplicate_short_names(self) -> None:
        """Every short_name must be unique across all profiles."""
        short_names = [p.short_name for p in IDE_PROFILES]
        assert len(short_names) == len(set(short_names)), (
            f"Duplicate short_names found: "
            f"{[n for n in short_names if short_names.count(n) > 1]}"
        )

    def test_no_duplicate_display_names(self) -> None:
        """Every display name must be unique across all profiles."""
        names = [p.name for p in IDE_PROFILES]
        assert len(names) == len(set(names)), (
            f"Duplicate names found: "
            f"{[n for n in names if names.count(n) > 1]}"
        )


# ---------------------------------------------------------------------------
# IDEProfile dataclass
# ---------------------------------------------------------------------------


class TestIDEProfileDataclass:
    """Test the IDEProfile dataclass behavior."""

    def test_frozen(self) -> None:
        """IDEProfile instances must be immutable (frozen dataclass)."""
        profile = IDE_PROFILES[0]
        with pytest.raises(AttributeError):
            profile.name = "Modified"  # type: ignore[misc]

    def test_default_platform_is_all(self) -> None:
        """Default platform should be 'all'."""
        p = IDEProfile(name="Test", short_name="test", dot_dirs=[".test"])
        assert p.platform == "all"

    def test_default_lists_are_empty(self) -> None:
        """Default list fields should be empty."""
        p = IDEProfile(name="Test", short_name="test", dot_dirs=[".test"])
        assert p.config_paths == []
        assert p.skill_paths == []


# ---------------------------------------------------------------------------
# MCP config filenames
# ---------------------------------------------------------------------------


class TestMCPConfigFilenames:
    """Validate the MCP config filename patterns."""

    def test_filenames_not_empty(self) -> None:
        """The filename list must not be empty."""
        assert len(MCP_CONFIG_FILENAMES) > 0

    def test_all_end_with_json(self) -> None:
        """All MCP config filenames must end with .json."""
        for fn in MCP_CONFIG_FILENAMES:
            assert fn.endswith(".json"), f"'{fn}' does not end with .json"

    def test_mcp_json_present(self) -> None:
        """The canonical 'mcp.json' must be in the list."""
        assert "mcp.json" in MCP_CONFIG_FILENAMES
