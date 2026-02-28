"""Tests for the MetaGPT roles parser.

Fixture files in ``tests/fixtures/metagpt/``:
    basic_role.py, action_def.py, team_setup.py, tool_registry.py, unsafe_role.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.metagpt_roles import MetaGPTParser

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "metagpt"


@pytest.fixture
def parser() -> MetaGPTParser:
    return MetaGPTParser()


@pytest.fixture
def basic_role_dir(tmp_path: Path) -> Path:
    (tmp_path / "basic_role.py").write_text(
        (_FIXTURES_DIR / "basic_role.py").read_text(encoding="utf-8"),
    )
    return tmp_path


@pytest.fixture
def action_def_dir(tmp_path: Path) -> Path:
    (tmp_path / "action_def.py").write_text(
        (_FIXTURES_DIR / "action_def.py").read_text(encoding="utf-8"),
    )
    return tmp_path


@pytest.fixture
def team_setup_dir(tmp_path: Path) -> Path:
    (tmp_path / "team_setup.py").write_text(
        (_FIXTURES_DIR / "team_setup.py").read_text(encoding="utf-8"),
    )
    return tmp_path


@pytest.fixture
def tool_registry_dir(tmp_path: Path) -> Path:
    (tmp_path / "tool_registry.py").write_text(
        (_FIXTURES_DIR / "tool_registry.py").read_text(encoding="utf-8"),
    )
    return tmp_path


@pytest.fixture
def unsafe_role_dir(tmp_path: Path) -> Path:
    (tmp_path / "unsafe_role.py").write_text(
        (_FIXTURES_DIR / "unsafe_role.py").read_text(encoding="utf-8"),
    )
    return tmp_path


@pytest.fixture
def pyproject_dir(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "my-agent"\ndependencies = ["metagpt>=0.8"]\n',
    )
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    return tmp_path


class TestCanParse:
    """Verify MetaGPTParser.can_parse detection heuristics."""

    def test_detects_basic_role(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        assert parser.can_parse(basic_role_dir) is True

    def test_detects_action_file(self, parser: MetaGPTParser, action_def_dir: Path) -> None:
        assert parser.can_parse(action_def_dir) is True

    def test_detects_team_file(self, parser: MetaGPTParser, team_setup_dir: Path) -> None:
        assert parser.can_parse(team_setup_dir) is True

    def test_detects_tool_registry(self, parser: MetaGPTParser, tool_registry_dir: Path) -> None:
        assert parser.can_parse(tool_registry_dir) is True

    def test_detects_pyproject_toml(self, parser: MetaGPTParser, pyproject_dir: Path) -> None:
        assert parser.can_parse(pyproject_dir) is True

    def test_rejects_empty_dir(self, parser: MetaGPTParser, empty_dir: Path) -> None:
        assert parser.can_parse(empty_dir) is False

    def test_rejects_non_metagpt_python(self, parser: MetaGPTParser, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_detects_roles_subdir(self, parser: MetaGPTParser, tmp_path: Path) -> None:
        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        (roles_dir / "analyst.py").write_text(
            (_FIXTURES_DIR / "basic_role.py").read_text(encoding="utf-8"),
        )
        assert parser.can_parse(tmp_path) is True


class TestParseRoles:
    """Verify extraction of MetaGPT Role subclasses."""

    def test_extracts_role_name(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        skills = parser.parse(basic_role_dir)
        role_skills = [s for s in skills if "[Role]" in s.description]
        assert "Analyst" in {s.name for s in role_skills}

    def test_extracts_role_profile(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        skills = parser.parse(basic_role_dir)
        role_skills = [s for s in skills if s.name == "Analyst"]
        assert role_skills and "Data Analyst" in role_skills[0].description

    def test_extracts_role_goal(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        skills = parser.parse(basic_role_dir)
        role_skills = [s for s in skills if s.name == "Analyst"]
        assert role_skills and "Analyze datasets" in role_skills[0].description

    def test_multiple_roles_in_team(self, parser: MetaGPTParser, team_setup_dir: Path) -> None:
        skills = parser.parse(team_setup_dir)
        role_names = {s.name for s in skills if "[Role]" in s.description}
        assert "Programmer" in role_names
        assert "Reviewer" in role_names

    def test_format_is_metagpt(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        for skill in parser.parse(basic_role_dir):
            assert skill.format == "metagpt"


class TestParseActions:
    """Verify extraction of MetaGPT Action subclasses."""

    def test_extracts_action_name(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        skills = parser.parse(basic_role_dir)
        action_names = {s.name for s in skills if "[Action]" in s.description}
        assert "AnalyzeData" in action_names

    def test_extracts_multiple_actions(self, parser: MetaGPTParser, action_def_dir: Path) -> None:
        skills = parser.parse(action_def_dir)
        action_names = {s.name for s in skills if "[Action]" in s.description}
        assert action_names == {"FetchWebPage", "SummarizeText", "TranslateDocument"}

    def test_action_count(self, parser: MetaGPTParser, action_def_dir: Path) -> None:
        skills = parser.parse(action_def_dir)
        assert len([s for s in skills if "[Action]" in s.description]) == 3

    def test_action_urls_extracted(self, parser: MetaGPTParser, action_def_dir: Path) -> None:
        skills = parser.parse(action_def_dir)
        fetch_skills = [s for s in skills if s.name == "FetchWebPage"]
        assert fetch_skills
        assert any("scraper.example.com" in u for u in fetch_skills[0].urls)


class TestParseRegisterTool:
    """Verify extraction of @register_tool() decorated functions."""

    def test_extracts_tool_names(self, parser: MetaGPTParser, tool_registry_dir: Path) -> None:
        skills = parser.parse(tool_registry_dir)
        tool_names = {s.name for s in skills if "[Tool]" in s.description}
        assert tool_names == {"search_web", "fetch_stock_price"}

    def test_tool_count(self, parser: MetaGPTParser, tool_registry_dir: Path) -> None:
        skills = parser.parse(tool_registry_dir)
        assert len([s for s in skills if "[Tool]" in s.description]) == 2

    def test_tool_docstring_as_description(
        self, parser: MetaGPTParser, tool_registry_dir: Path,
    ) -> None:
        skills = parser.parse(tool_registry_dir)
        tool_skills = [s for s in skills if s.name == "search_web"]
        assert tool_skills and "Search the web" in tool_skills[0].description

    def test_tool_urls(self, parser: MetaGPTParser, tool_registry_dir: Path) -> None:
        skills = parser.parse(tool_registry_dir)
        tool_skills = [s for s in skills if s.name == "search_web"]
        assert tool_skills
        assert any("api.search.com" in u for u in tool_skills[0].urls)


class TestSecuritySignals:
    """Verify detection of dangerous patterns in MetaGPT skills."""

    def test_extracts_env_vars(self, parser: MetaGPTParser, unsafe_role_dir: Path) -> None:
        skills = parser.parse(unsafe_role_dir)
        action_skills = [s for s in skills if s.name == "ExfiltrateData"]
        assert action_skills
        env_vars = action_skills[0].env_vars_referenced
        assert "ADMIN_SECRET" in env_vars
        assert "EXFIL_API_KEY" in env_vars

    def test_extracts_shell_commands(self, parser: MetaGPTParser, unsafe_role_dir: Path) -> None:
        skills = parser.parse(unsafe_role_dir)
        action_skills = [s for s in skills if s.name == "ExfiltrateData"]
        assert action_skills
        cmds = action_skills[0].shell_commands
        assert any("curl" in cmd for cmd in cmds)
        assert any("rm" in cmd for cmd in cmds)

    def test_extracts_unsafe_urls(self, parser: MetaGPTParser, unsafe_role_dir: Path) -> None:
        skills = parser.parse(unsafe_role_dir)
        action_skills = [s for s in skills if s.name == "ExfiltrateData"]
        assert action_skills
        assert any("evil.exfil.site" in u for u in action_skills[0].urls)

    def test_extracts_dependencies(self, parser: MetaGPTParser, unsafe_role_dir: Path) -> None:
        all_deps: set[str] = set()
        for skill in parser.parse(unsafe_role_dir):
            all_deps.update(skill.dependencies)
        assert {"os", "subprocess", "metagpt"} <= all_deps


class TestEdgeCases:
    """Verify robustness against malformed / unusual inputs."""

    def test_empty_dir_returns_empty(self, parser: MetaGPTParser, empty_dir: Path) -> None:
        assert parser.parse(empty_dir) == []

    def test_syntax_error_does_not_raise(self, parser: MetaGPTParser, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text(
            "from metagpt.roles import Role\nclass Bad(Role\n",
        )
        skills = parser.parse(tmp_path)
        assert isinstance(skills, list)

    def test_non_utf8_file_does_not_raise(self, parser: MetaGPTParser, tmp_path: Path) -> None:
        (tmp_path / "binary.py").write_bytes(b"\x80\x81\x82from metagpt import Role\n")
        assert isinstance(parser.parse(tmp_path), list)

    def test_returns_parsed_skill_instances(
        self, parser: MetaGPTParser, basic_role_dir: Path,
    ) -> None:
        for skill in parser.parse(basic_role_dir):
            assert isinstance(skill, ParsedSkill)

    def test_source_path_exists(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        for skill in parser.parse(basic_role_dir):
            assert skill.source_path.exists()

    def test_raw_content_populated(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        for skill in parser.parse(basic_role_dir):
            assert len(skill.raw_content) > 0

    def test_code_blocks_populated(self, parser: MetaGPTParser, basic_role_dir: Path) -> None:
        role_skills = [s for s in parser.parse(basic_role_dir) if s.name == "Analyst"]
        assert role_skills and role_skills[0].code_blocks
        assert "Analyst" in role_skills[0].code_blocks[0]

    def test_regex_fallback_for_role(self, parser: MetaGPTParser, tmp_path: Path) -> None:
        (tmp_path / "fallback.py").write_text(
            "from metagpt.roles import Role\n"
            "class FallbackRole(Role):\n"
            "    name = 'FallbackRole'\n"
            "def broken(\n",
        )
        assert "FallbackRole" in {s.name for s in parser.parse(tmp_path)}

    def test_regex_fallback_for_register_tool(
        self, parser: MetaGPTParser, tmp_path: Path,
    ) -> None:
        (tmp_path / "fallback_tool.py").write_text(
            "from metagpt.tools.tool_registry import register_tool\n"
            "@register_tool()\n"
            "def my_fallback_tool(x):\n"
            "    return x\n"
            "class Broken(\n",
        )
        assert "my_fallback_tool" in {s.name for s in parser.parse(tmp_path)}


class TestTeamComposition:
    """Verify that Team files parse all roles and actions correctly."""

    def test_team_file_total_skills(self, parser: MetaGPTParser, team_setup_dir: Path) -> None:
        skills = parser.parse(team_setup_dir)
        assert len(skills) == 4  # 2 Actions + 2 Roles

    def test_team_actions_extracted(self, parser: MetaGPTParser, team_setup_dir: Path) -> None:
        action_names = {s.name for s in parser.parse(team_setup_dir) if "[Action]" in s.description}
        assert action_names == {"WriteCode", "ReviewCode"}

    def test_team_roles_extracted(self, parser: MetaGPTParser, team_setup_dir: Path) -> None:
        role_names = {s.name for s in parser.parse(team_setup_dir) if "[Role]" in s.description}
        assert role_names == {"Programmer", "Reviewer"}
