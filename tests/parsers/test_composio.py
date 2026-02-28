"""Tests for the Composio tools parser -- detection and basic parsing.

Composio is a universal agent integration layer (26.5K stars, 500+
integrations). This test module covers can_parse detection and core
parsing of Action/App references from Python files using the SDK.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
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
def basic_tools_dir(tmp_path: Path) -> Path:
    """Directory with basic Action-based Composio usage."""
    shutil.copy(_FIXTURES_DIR / "basic_tools.py", tmp_path / "basic_tools.py")
    return tmp_path


@pytest.fixture
def multi_app_dir(tmp_path: Path) -> Path:
    """Directory with multiple App-based integrations."""
    shutil.copy(_FIXTURES_DIR / "multi_app.py", tmp_path / "multi_app.py")
    return tmp_path


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
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory with no Python files."""
    return tmp_path


# ---------------------------------------------------------------------------
# can_parse detection tests
# ---------------------------------------------------------------------------


class TestComposioParserDetection:
    """Validate can_parse detection for Composio tool files."""

    def test_detects_basic_composio_imports(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """Parser recognises directory with 'from composio' imports."""
        assert parser.can_parse(basic_tools_dir) is True

    def test_detects_multi_app_file(
        self, parser: ComposioParser, multi_app_dir: Path,
    ) -> None:
        """Parser recognises App-based Composio usage."""
        assert parser.can_parse(multi_app_dir) is True

    def test_detects_custom_action_file(
        self, parser: ComposioParser, custom_action_dir: Path,
    ) -> None:
        """Parser recognises @action decorated functions."""
        assert parser.can_parse(custom_action_dir) is True

    def test_detects_entity_usage(
        self, parser: ComposioParser, entity_usage_dir: Path,
    ) -> None:
        """Parser recognises entity/connection management patterns."""
        assert parser.can_parse(entity_usage_dir) is True

    def test_rejects_empty_directory(
        self, parser: ComposioParser, empty_dir: Path,
    ) -> None:
        """Parser rejects directory without Composio files."""
        assert parser.can_parse(empty_dir) is False

    def test_rejects_non_composio_python(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Parser ignores plain Python files without Composio imports."""
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_detects_composio_langchain_imports(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Parser detects composio_langchain bridge imports."""
        source = (
            "from composio_langchain import ComposioToolSet\n"
            "toolset = ComposioToolSet()\n"
        )
        (tmp_path / "agent.py").write_text(source)
        assert parser.can_parse(tmp_path) is True

    def test_detects_tools_subdirectory(
        self, parser: ComposioParser, tmp_path: Path,
    ) -> None:
        """Parser finds Composio files in tools/ subdirectory."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        shutil.copy(_FIXTURES_DIR / "basic_tools.py", tools_dir / "basic_tools.py")
        assert parser.can_parse(tmp_path) is True


# ---------------------------------------------------------------------------
# Basic parsing tests
# ---------------------------------------------------------------------------


class TestComposioParserBasicParsing:
    """Validate core parsing of Composio tool definitions."""

    def test_parse_basic_action_references(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """Extracts Action enum references from basic usage."""
        skills = parser.parse(basic_tools_dir)
        assert len(skills) >= 1
        all_caps = []
        for skill in skills:
            all_caps.extend(skill.declared_capabilities)
        assert "action:GITHUB_CREATE_ISSUE" in all_caps
        assert "action:SLACK_SEND_MESSAGE" in all_caps

    def test_parse_basic_returns_parsed_skill(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(basic_tools_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)

    def test_format_is_composio(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """Parsed skills have format='composio'."""
        skills = parser.parse(basic_tools_dir)
        for skill in skills:
            assert skill.format == "composio"

    def test_source_path_set(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """source_path points to an existing Python file."""
        skills = parser.parse(basic_tools_dir)
        for skill in skills:
            assert skill.source_path.exists()
            assert skill.source_path.suffix == ".py"

    def test_raw_content_preserved(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """The full raw source content is preserved."""
        skills = parser.parse(basic_tools_dir)
        for skill in skills:
            assert "ComposioToolSet" in skill.raw_content

    def test_extracts_urls_from_basic_tools(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """Extracts URLs from API calls in source."""
        skills = parser.parse(basic_tools_dir)
        all_urls = []
        for skill in skills:
            all_urls.extend(skill.urls)
        assert any("api.composio.dev" in url for url in all_urls)

    def test_extracts_dependencies(
        self, parser: ComposioParser, basic_tools_dir: Path,
    ) -> None:
        """Extracts import dependencies from source file."""
        skills = parser.parse(basic_tools_dir)
        all_deps = []
        for skill in skills:
            all_deps.extend(skill.dependencies)
        assert "composio" in all_deps
        assert "requests" in all_deps


# ---------------------------------------------------------------------------
# App-based integration tests
# ---------------------------------------------------------------------------


class TestComposioParserApps:
    """Validate extraction of App-based integrations."""

    def test_extracts_app_references(
        self, parser: ComposioParser, multi_app_dir: Path,
    ) -> None:
        """Extracts App.XYZ references as declared capabilities."""
        skills = parser.parse(multi_app_dir)
        all_caps = []
        for skill in skills:
            all_caps.extend(skill.declared_capabilities)
        assert "app:GITHUB" in all_caps
        assert "app:SLACK" in all_caps
        assert "app:GMAIL" in all_caps

    def test_extracts_google_calendar_app(
        self, parser: ComposioParser, multi_app_dir: Path,
    ) -> None:
        """Extracts App.GOOGLE_CALENDAR reference."""
        skills = parser.parse(multi_app_dir)
        all_caps = []
        for skill in skills:
            all_caps.extend(skill.declared_capabilities)
        assert "app:GOOGLE_CALENDAR" in all_caps

    def test_extracts_env_string_pattern(
        self, parser: ComposioParser, multi_app_dir: Path,
    ) -> None:
        """Extracts env vars from 'env:VAR_NAME' string pattern."""
        skills = parser.parse(multi_app_dir)
        all_env = []
        for skill in skills:
            all_env.extend(skill.env_vars_referenced)
        assert "COMPOSIO_API_KEY" in all_env

    def test_description_mentions_apps(
        self, parser: ComposioParser, multi_app_dir: Path,
    ) -> None:
        """Module-level skill description mentions app names."""
        skills = parser.parse(multi_app_dir)
        combined_desc = " ".join(skill.description for skill in skills)
        assert "GITHUB" in combined_desc or "Apps:" in combined_desc
