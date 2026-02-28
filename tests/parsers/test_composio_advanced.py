"""Tests for the Composio tools parser -- custom actions, security, edges.

Covers custom @action definitions, entity/connection patterns,
security signal detection (shell commands, env vars, suspicious URLs),
and edge cases like malformed files and regex fallback.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.composio_tools import ComposioParser

# ---------------------------------------------------------------------------
# Path to fixture files
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "composio"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> ComposioParser:
    """Create a fresh ComposioParser instance."""
    return ComposioParser()


@pytest.fixture
def custom_action_dir(tmp_path: Path) -> Path:
    """Directory with custom @action definitions."""
    shutil.copy(_FIXTURES_DIR / "custom_action.py", tmp_path / "custom_action.py")
    return tmp_path


@pytest.fixture
def entity_usage_dir(tmp_path: Path) -> Path:
    """Directory with entity and connection management."""
    shutil.copy(_FIXTURES_DIR / "entity_usage.py", tmp_path / "entity_usage.py")
    return tmp_path


@pytest.fixture
def unsafe_action_dir(tmp_path: Path) -> Path:
    """Directory with intentionally dangerous Composio actions."""
    shutil.copy(_FIXTURES_DIR / "unsafe_action.py", tmp_path / "unsafe_action.py")
    return tmp_path


# ---------------------------------------------------------------------------
# Custom @action tests
# ---------------------------------------------------------------------------


class TestComposioParserCustomActions:
    """Validate extraction of custom @action definitions."""

    def test_extracts_custom_actions(
        self, parser: ComposioParser, custom_action_dir: Path,
    ) -> None:
        """Parser finds @action decorated functions."""
        skills = parser.parse(custom_action_dir)
        names = {skill.name for skill in skills}
        assert "weather_lookup" in names
        assert "stock_price" in names

    def test_custom_action_count(
        self, parser: ComposioParser, custom_action_dir: Path,
    ) -> None:
        """Correct number of custom actions extracted."""
        skills = parser.parse(custom_action_dir)
        assert len(skills) == 2

    def test_custom_action_description(
        self, parser: ComposioParser, custom_action_dir: Path,
    ) -> None:
        """Extracts docstring as description for custom actions."""
        skills = parser.parse(custom_action_dir)
        weather_skills = [s for s in skills if s.name == "weather_lookup"]
        assert len(weather_skills) == 1
        assert "weather" in weather_skills[0].description.lower()

    def test_custom_action_urls(
        self, parser: ComposioParser, custom_action_dir: Path,
    ) -> None:
        """Extracts URLs from custom action bodies."""
        skills = parser.parse(custom_action_dir)
        all_urls = []
        for skill in skills:
            all_urls.extend(skill.urls)
        assert any("openweathermap" in url for url in all_urls)
        assert any("finance.example.com" in url for url in all_urls)

    def test_custom_action_code_blocks(
        self, parser: ComposioParser, custom_action_dir: Path,
    ) -> None:
        """Extracts code blocks from custom action bodies."""
        skills = parser.parse(custom_action_dir)
        for skill in skills:
            assert len(skill.code_blocks) >= 1
            assert "def " in skill.code_blocks[0]


# ---------------------------------------------------------------------------
# Entity/connection tests
# ---------------------------------------------------------------------------


class TestComposioParserEntity:
    """Validate extraction from entity and connection patterns."""

    def test_extracts_entity_actions(
        self, parser: ComposioParser, entity_usage_dir: Path,
    ) -> None:
        """Extracts Action refs from entity.execute_action calls."""
        skills = parser.parse(entity_usage_dir)
        all_caps = []
        for skill in skills:
            all_caps.extend(skill.declared_capabilities)
        assert "action:GITHUB_CREATE_ISSUE" in all_caps

    def test_extracts_entity_apps(
        self, parser: ComposioParser, entity_usage_dir: Path,
    ) -> None:
        """Extracts App refs from get_connection calls."""
        skills = parser.parse(entity_usage_dir)
        all_caps = []
        for skill in skills:
            all_caps.extend(skill.declared_capabilities)
        assert "app:GITHUB" in all_caps
        assert "app:SLACK" in all_caps

    def test_extracts_entity_env_vars(
        self, parser: ComposioParser, entity_usage_dir: Path,
    ) -> None:
        """Extracts env vars from entity-based auth patterns."""
        skills = parser.parse(entity_usage_dir)
        all_env = []
        for skill in skills:
            all_env.extend(skill.env_vars_referenced)
        assert "COMPOSIO_API_KEY" in all_env


# ---------------------------------------------------------------------------
# Security signal extraction tests
# ---------------------------------------------------------------------------


class TestComposioParserSecurity:
    """Validate detection of dangerous patterns in Composio files."""

    def test_detects_shell_commands(
        self, parser: ComposioParser, unsafe_action_dir: Path,
    ) -> None:
        """Detects subprocess calls in custom actions."""
        skills = parser.parse(unsafe_action_dir)
        all_cmds = []
        for skill in skills:
            all_cmds.extend(skill.shell_commands)
        assert any("ping" in cmd for cmd in all_cmds)

    def test_detects_env_var_access(
        self, parser: ComposioParser, unsafe_action_dir: Path,
    ) -> None:
        """Detects environment variable access patterns."""
        skills = parser.parse(unsafe_action_dir)
        all_env = []
        for skill in skills:
            all_env.extend(skill.env_vars_referenced)
        assert "ADMIN_TOKEN" in all_env
        assert "SECRET_API_KEY" in all_env

    def test_detects_exfil_urls(
        self, parser: ComposioParser, unsafe_action_dir: Path,
    ) -> None:
        """Detects suspicious external URLs in action bodies."""
        skills = parser.parse(unsafe_action_dir)
        all_urls = []
        for skill in skills:
            all_urls.extend(skill.urls)
        assert any("evil.exfil.site" in url for url in all_urls)

    def test_unsafe_action_names(
        self, parser: ComposioParser, unsafe_action_dir: Path,
    ) -> None:
        """Extracts correct names from unsafe custom actions."""
        skills = parser.parse(unsafe_action_dir)
        names = {skill.name for skill in skills}
        assert "system_diagnostic" in names
        assert "data_fetcher" in names


# ---------------------------------------------------------------------------
# Edge cases and robustness tests
# ---------------------------------------------------------------------------


class TestComposioParserEdgeCases:
    """Validate robustness against malformed and edge-case inputs."""

    def test_empty_directory_returns_empty(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Parsing an empty directory returns an empty list."""
        assert parser.parse(tmp_path) == []

    def test_malformed_python_does_not_raise(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Handles files with syntax errors gracefully."""
        malformed = (
            "from composio import action\n"
            "@action(toolname='broken')\n"
            "def bad_func(:\n"
        )
        (tmp_path / "broken.py").write_text(malformed)
        skills = parser.parse(tmp_path)
        # Should not raise; may extract via regex fallback.
        assert isinstance(skills, list)

    def test_non_composio_file_ignored(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Files without composio imports are not parsed."""
        (tmp_path / "unrelated.py").write_text(
            "import flask\napp = flask.Flask(__name__)\n"
        )
        assert parser.parse(tmp_path) == []

    def test_unreadable_file_skipped(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Unreadable files are silently skipped."""
        bad_file = tmp_path / "unreadable.py"
        bad_file.write_text("from composio import ComposioToolSet\n")
        bad_file.chmod(0o000)
        try:
            skills = parser.parse(tmp_path)
            assert isinstance(skills, list)
        finally:
            bad_file.chmod(0o644)

    def test_file_with_only_composio_import(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """File with import but no Action/App refs returns empty."""
        source = (
            "from composio import ComposioToolSet\n"
            "toolset = ComposioToolSet()\n"
        )
        (tmp_path / "bare.py").write_text(source)
        skills = parser.parse(tmp_path)
        assert skills == []

    def test_mixed_composio_and_other_code(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Correctly parses Composio tools in a file with other code."""
        source = (
            "import logging\n"
            "from composio import ComposioToolSet, Action\n"
            "logger = logging.getLogger(__name__)\n"
            "toolset = ComposioToolSet()\n"
            "tools = toolset.get_tools(actions=[Action.GITHUB_STAR_REPO])\n"
            "logger.info('Ready')\n"
        )
        (tmp_path / "mixed.py").write_text(source)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert "action:GITHUB_STAR_REPO" in skills[0].declared_capabilities

    def test_regex_fallback_extracts_action_on_syntax_error(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Regex fallback captures Action refs from broken files."""
        source = (
            "from composio import Action, ComposioToolSet\n"
            "toolset = ComposioToolSet()\n"
            "tools = toolset.get_tools(actions=[Action.GMAIL_SEND_EMAIL])\n"
            "if True\n"  # SyntaxError: missing colon
        )
        (tmp_path / "broken_action.py").write_text(source)
        skills = parser.parse(tmp_path)
        assert len(skills) >= 1
        all_caps = []
        for skill in skills:
            all_caps.extend(skill.declared_capabilities)
        assert "action:GMAIL_SEND_EMAIL" in all_caps
