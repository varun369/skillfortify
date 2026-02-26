"""Tests for the CrewAI tools parser.

CrewAI tools are defined as Python files with BaseTool subclasses or @tool
functions (similar to LangChain), plus YAML crew config files that declare
tool references for agents. The parser must handle both YAML configs and
Python tool files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.crewai import CrewAIParser


# ---------------------------------------------------------------------------
# Sample sources
# ---------------------------------------------------------------------------

_CREW_YAML = """\
agents:
  researcher:
    role: "Research Analyst"
    tools:
      - search_tool
      - web_scraper
  writer:
    role: "Content Writer"
    tools:
      - text_generator
"""

_AGENTS_YAML = """\
agents:
  analyst:
    role: "Data Analyst"
    tools:
      - data_fetcher
"""

_CLASS_TOOL_SOURCE = '''\
from crewai.tools import BaseTool
import requests

class SearchTool(BaseTool):
    name: str = "Search Tool"
    description: str = "Searches the web for information"

    def _run(self, query: str) -> str:
        resp = requests.get("https://api.search.example.com/v1", params={"q": query})
        return resp.text
'''

_DECORATOR_TOOL_SOURCE = '''\
from crewai.tools import tool
import os

@tool
def scrape_page(url: str) -> str:
    """Scrape a web page and return its content."""
    import requests
    key = os.environ["SCRAPER_API_KEY"]
    return requests.get(f"https://scraper.example.com/api?url={url}").text
'''

_SHELL_TOOL_SOURCE = '''\
from crewai.tools import BaseTool
import subprocess

class CommandTool(BaseTool):
    name: str = "command_runner"
    description: str = "Runs system commands"

    def _run(self, cmd: str) -> str:
        return subprocess.run("cat /etc/passwd", capture_output=True, text=True).stdout
'''

_MULTI_TOOL_SOURCE = '''\
from crewai.tools import BaseTool, tool

class ToolAlpha(BaseTool):
    name: str = "alpha"
    description: str = "First tool"

    def _run(self, x: str) -> str:
        return x

@tool
def tool_beta(x: str) -> str:
    """Second tool"""
    return x
'''

_MALFORMED_YAML = """\
agents:
  researcher:
    - this is invalid
"""

_ENV_VARS_SOURCE = '''\
from crewai.tools import tool
import os

@tool
def secret_tool(x: str) -> str:
    """Uses secrets."""
    key = os.environ["DB_PASSWORD"]
    token = os.getenv("SERVICE_TOKEN")
    return x
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> CrewAIParser:
    return CrewAIParser()


@pytest.fixture
def crew_yaml_dir(tmp_path: Path) -> Path:
    """Create a directory with crew.yaml."""
    (tmp_path / "crew.yaml").write_text(_CREW_YAML)
    return tmp_path


@pytest.fixture
def agents_yaml_dir(tmp_path: Path) -> Path:
    """Create a directory with agents.yaml."""
    (tmp_path / "agents.yaml").write_text(_AGENTS_YAML)
    return tmp_path


@pytest.fixture
def crewai_python_dir(tmp_path: Path) -> Path:
    """Create a directory with a CrewAI Python tool file."""
    (tmp_path / "search.py").write_text(_CLASS_TOOL_SOURCE)
    return tmp_path


@pytest.fixture
def crewai_full_dir(tmp_path: Path) -> Path:
    """Directory with both crew.yaml and Python tools."""
    (tmp_path / "crew.yaml").write_text(_CREW_YAML)
    (tmp_path / "tools.py").write_text(_CLASS_TOOL_SOURCE)
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrewAIParser:
    """Validate the CrewAI tools parser."""

    def test_can_parse_crew_yaml(self, parser: CrewAIParser, crew_yaml_dir: Path) -> None:
        """Parser recognises a directory with crew.yaml."""
        assert parser.can_parse(crew_yaml_dir) is True

    def test_can_parse_agents_yaml(self, parser: CrewAIParser, agents_yaml_dir: Path) -> None:
        """Parser recognises a directory with agents.yaml."""
        assert parser.can_parse(agents_yaml_dir) is True

    def test_can_parse_python_tools(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """Parser recognises a directory with CrewAI Python tool files."""
        assert parser.can_parse(crewai_python_dir) is True

    def test_cannot_parse_empty_dir(self, parser: CrewAIParser, empty_dir: Path) -> None:
        """Parser rejects a directory without CrewAI artifacts."""
        assert parser.can_parse(empty_dir) is False

    def test_cannot_parse_non_crewai_python(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Parser ignores Python files without CrewAI imports."""
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_parse_crew_yaml_tool_names(
        self, parser: CrewAIParser, crew_yaml_dir: Path,
    ) -> None:
        """Extracts tool names from crew.yaml agent definitions."""
        skills = parser.parse(crew_yaml_dir)
        names = {s.name for s in skills}
        assert "search_tool" in names
        assert "web_scraper" in names
        assert "text_generator" in names

    def test_parse_crew_yaml_count(
        self, parser: CrewAIParser, crew_yaml_dir: Path,
    ) -> None:
        """Correct number of tools extracted from crew.yaml."""
        skills = parser.parse(crew_yaml_dir)
        assert len(skills) == 3  # 2 from researcher + 1 from writer

    def test_parse_agents_yaml(
        self, parser: CrewAIParser, agents_yaml_dir: Path,
    ) -> None:
        """Extracts tools from agents.yaml."""
        skills = parser.parse(agents_yaml_dir)
        assert len(skills) == 1
        assert skills[0].name == "data_fetcher"

    def test_parse_class_tool_name(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """Extracts tool name from BaseTool subclass."""
        skills = parser.parse(crewai_python_dir)
        assert any(s.name == "Search Tool" for s in skills)

    def test_parse_class_tool_description(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """Extracts description from BaseTool subclass."""
        skills = parser.parse(crewai_python_dir)
        tool_skills = [s for s in skills if s.name == "Search Tool"]
        assert tool_skills
        assert "Searches the web" in tool_skills[0].description

    def test_parse_decorator_tool(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Extracts tool from @tool decorated function."""
        (tmp_path / "scraper.py").write_text(_DECORATOR_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        assert any(s.name == "scrape_page" for s in skills)

    def test_extracts_urls(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """Extracts URLs from tool code."""
        skills = parser.parse(crewai_python_dir)
        tool_skills = [s for s in skills if s.name == "Search Tool"]
        assert any("api.search.example.com" in u for u in tool_skills[0].urls)

    def test_extracts_env_vars(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Extracts environment variable references."""
        (tmp_path / "scraper.py").write_text(_DECORATOR_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        tool_skills = [s for s in skills if s.name == "scrape_page"]
        assert "SCRAPER_API_KEY" in tool_skills[0].env_vars_referenced

    def test_extracts_shell_commands(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Extracts shell commands from subprocess calls."""
        (tmp_path / "cmd.py").write_text(_SHELL_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        tool_skills = [s for s in skills if s.name == "command_runner"]
        assert any("cat" in cmd for cmd in tool_skills[0].shell_commands)

    def test_extracts_dependencies(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """Extracts import dependencies."""
        skills = parser.parse(crewai_python_dir)
        tool_skills = [s for s in skills if s.name == "Search Tool"]
        assert "crewai" in tool_skills[0].dependencies

    def test_format_is_correct(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """All parsed skills have format='crewai'."""
        skills = parser.parse(crewai_python_dir)
        for skill in skills:
            assert skill.format == "crewai"

    def test_format_yaml_tools(
        self, parser: CrewAIParser, crew_yaml_dir: Path,
    ) -> None:
        """YAML-derived tools also have format='crewai'."""
        skills = parser.parse(crew_yaml_dir)
        for skill in skills:
            assert skill.format == "crewai"

    def test_combined_yaml_and_python(
        self, parser: CrewAIParser, crewai_full_dir: Path,
    ) -> None:
        """Parses both YAML configs and Python tool files."""
        skills = parser.parse(crewai_full_dir)
        # 3 from crew.yaml + 1 from Python class
        assert len(skills) == 4

    def test_multiple_tools_in_one_file(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Parses multiple tool definitions from a single file."""
        (tmp_path / "multi.py").write_text(_MULTI_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        names = {s.name for s in skills}
        assert "alpha" in names
        assert "tool_beta" in names

    def test_malformed_yaml(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Handles malformed crew.yaml gracefully."""
        (tmp_path / "crew.yaml").write_text(_MALFORMED_YAML)
        skills = parser.parse(tmp_path)
        assert skills == []

    def test_handles_empty_dir(
        self, parser: CrewAIParser, empty_dir: Path,
    ) -> None:
        """Parsing an empty directory returns an empty list."""
        skills = parser.parse(empty_dir)
        assert skills == []

    def test_multiple_env_vars(
        self, parser: CrewAIParser, tmp_path: Path,
    ) -> None:
        """Extracts multiple environment variable references."""
        (tmp_path / "secrets.py").write_text(_ENV_VARS_SOURCE)
        skills = parser.parse(tmp_path)
        tool_skills = [s for s in skills if s.name == "secret_tool"]
        assert "DB_PASSWORD" in tool_skills[0].env_vars_referenced
        assert "SERVICE_TOKEN" in tool_skills[0].env_vars_referenced

    def test_source_path_set(
        self, parser: CrewAIParser, crewai_python_dir: Path,
    ) -> None:
        """source_path points to the actual file."""
        skills = parser.parse(crewai_python_dir)
        tool_skills = [s for s in skills if s.name == "Search Tool"]
        assert tool_skills[0].source_path.exists()

    def test_returns_parsed_skill_instances(
        self, parser: CrewAIParser, crewai_full_dir: Path,
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(crewai_full_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)
