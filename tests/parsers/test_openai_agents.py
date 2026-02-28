"""Tests for the OpenAI Agents SDK parser — core extraction.

Covers ``can_parse`` probing, ``@function_tool`` extraction, and
``Agent(...)`` instantiation parsing. Advanced pattern tests (MCP,
hosted tools, handoffs, guardrails, unsafe patterns, edge cases)
live in ``test_openai_agents_advanced.py``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.openai_agents import OpenAIAgentsParser

# Path to pre-written fixture files.
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "openai_agents"


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

@pytest.fixture
def parser() -> OpenAIAgentsParser:
    """Fresh parser instance."""
    return OpenAIAgentsParser()


@pytest.fixture
def basic_dir(tmp_path: Path) -> Path:
    """Directory with a basic agent and function tools."""
    shutil.copy(_FIXTURES / "basic_agent.py", tmp_path / "basic_agent.py")
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory with no Python files."""
    return tmp_path


# --------------------------------------------------------------------------- #
# can_parse tests                                                              #
# --------------------------------------------------------------------------- #

class TestCanParse:
    """Validate the can_parse probe method."""

    def test_detects_basic_agent(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        assert parser.can_parse(basic_dir) is True

    def test_rejects_empty_dir(
        self, parser: OpenAIAgentsParser, empty_dir: Path,
    ) -> None:
        assert parser.can_parse(empty_dir) is False

    def test_rejects_non_agents_python(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Ignores plain Python files without Agents SDK markers."""
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_detects_requirements_txt(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Detects openai-agents in requirements.txt."""
        (tmp_path / "requirements.txt").write_text("openai-agents>=0.2\nrequests\n")
        assert parser.can_parse(tmp_path) is True

    def test_detects_pyproject_toml(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Detects openai-agents in pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["openai-agents>=0.2"]\n',
        )
        assert parser.can_parse(tmp_path) is True

    def test_finds_files_in_tools_subdir(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Discovers agent files inside a tools/ subdirectory."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        shutil.copy(_FIXTURES / "basic_agent.py", tools_dir / "agent.py")
        assert parser.can_parse(tmp_path) is True

    def test_detects_mcp_imports(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Detects files with from agents.mcp import."""
        shutil.copy(_FIXTURES / "mcp_agent.py", tmp_path / "mcp.py")
        assert parser.can_parse(tmp_path) is True

    def test_detects_hosted_tool_imports(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Detects files with from agents.tools import."""
        shutil.copy(_FIXTURES / "hosted_tools.py", tmp_path / "hosted.py")
        assert parser.can_parse(tmp_path) is True


# --------------------------------------------------------------------------- #
# Function tool extraction tests                                               #
# --------------------------------------------------------------------------- #

class TestFunctionTools:
    """Validate extraction of @function_tool decorated functions."""

    def test_extracts_function_tool_names(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        skills = parser.parse(basic_dir)
        tool_names = {s.name for s in skills}
        assert "get_weather" in tool_names
        assert "translate_text" in tool_names

    def test_extracts_docstring_description(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        skills = parser.parse(basic_dir)
        weather = [s for s in skills if s.name == "get_weather"]
        assert weather
        assert "weather" in weather[0].description.lower()

    def test_extracts_urls_from_tool_body(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        skills = parser.parse(basic_dir)
        weather = [s for s in skills if s.name == "get_weather"]
        assert weather
        assert any("api.weather.com" in url for url in weather[0].urls)

    def test_format_is_openai_agents(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        for skill in parser.parse(basic_dir):
            assert skill.format == "openai_agents"

    def test_source_path_set(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        for skill in parser.parse(basic_dir):
            assert skill.source_path.exists()
            assert skill.source_path.suffix == ".py"

    def test_raw_content_preserved(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        tool_skills = [s for s in parser.parse(basic_dir) if s.name == "get_weather"]
        assert tool_skills
        assert "function_tool" in tool_skills[0].raw_content

    def test_returns_parsed_skill_instances(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        for skill in parser.parse(basic_dir):
            assert isinstance(skill, ParsedSkill)

    def test_extracts_dependencies(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        tool_skills = [s for s in parser.parse(basic_dir) if s.name == "get_weather"]
        assert tool_skills
        assert "requests" in tool_skills[0].dependencies
        assert "agents" in tool_skills[0].dependencies


# --------------------------------------------------------------------------- #
# Agent instantiation tests                                                    #
# --------------------------------------------------------------------------- #

class TestAgentInstantiation:
    """Validate extraction of Agent(...) calls."""

    def test_extracts_agent_name(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        skills = parser.parse(basic_dir)
        agent_skills = [s for s in skills if s.name == "weather_assistant"]
        assert len(agent_skills) == 1

    def test_extracts_agent_instructions(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "weather_assistant"]
        assert agent
        assert "weather" in agent[0].instructions.lower()

    def test_agent_has_model_capability(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "weather_assistant"]
        assert agent
        assert "model:gpt-4o" in agent[0].declared_capabilities

    def test_agent_version_is_unknown(
        self, parser: OpenAIAgentsParser, basic_dir: Path,
    ) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "weather_assistant"]
        assert agent
        assert agent[0].version == "unknown"
