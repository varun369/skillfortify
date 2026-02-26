"""Tests for the LangChain tools parser.

LangChain tools are Python files containing BaseTool subclasses or @tool
decorated functions. The parser must extract names, descriptions, shell
commands, URLs, environment variables, dependencies, and code blocks from
both class-based and decorator-based tool definitions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.langchain import LangChainParser


# ---------------------------------------------------------------------------
# Sample sources
# ---------------------------------------------------------------------------

_CLASS_TOOL_SOURCE = '''\
from langchain.tools import BaseTool

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for information"

    def _run(self, query: str) -> str:
        import requests
        resp = requests.get("https://api.search.example.com/v1", params={"q": query})
        return resp.text
'''

_DECORATOR_TOOL_SOURCE = '''\
from langchain_core.tools import tool
import os

@tool
def fetch_weather(city: str) -> str:
    """Fetch weather data for a city."""
    import requests
    key = os.environ["WEATHER_API_KEY"]
    return requests.get(f"https://weather.example.com/api/{city}").text
'''

_SHELL_TOOL_SOURCE = '''\
from langchain.tools import BaseTool
import subprocess

class ShellRunner(BaseTool):
    name = "shell_runner"
    description = "Run shell commands"

    def _run(self, cmd: str) -> str:
        return subprocess.run("ls -la /tmp", capture_output=True, text=True).stdout
'''

_MULTI_TOOL_SOURCE = '''\
from langchain.tools import BaseTool, tool

class ToolA(BaseTool):
    name = "tool_a"
    description = "First tool"

    def _run(self, x: str) -> str:
        return x

@tool
def tool_b(x: str) -> str:
    """Second tool"""
    return x
'''

_ANNOTATED_TOOL_SOURCE = '''\
from langchain.tools import BaseTool

class AnnotatedTool(BaseTool):
    name: str = "annotated_search"
    description: str = "An annotated tool"

    def _run(self, query: str) -> str:
        return query
'''

_ENV_VARS_SOURCE = '''\
from langchain.tools import tool
import os

@tool
def secret_tool(x: str) -> str:
    """Uses secrets."""
    key = os.environ["API_SECRET_KEY"]
    token = os.getenv("AUTH_TOKEN")
    return x
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> LangChainParser:
    return LangChainParser()


@pytest.fixture
def langchain_dir(tmp_path: Path) -> Path:
    """Create a directory with a LangChain class-based tool."""
    (tmp_path / "search_tool.py").write_text(_CLASS_TOOL_SOURCE)
    return tmp_path


@pytest.fixture
def langchain_decorator_dir(tmp_path: Path) -> Path:
    """Create a directory with a LangChain decorator-based tool."""
    (tmp_path / "weather.py").write_text(_DECORATOR_TOOL_SOURCE)
    return tmp_path


@pytest.fixture
def langchain_tools_subdir(tmp_path: Path) -> Path:
    """Create a tools/ subdirectory with a LangChain tool."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "search.py").write_text(_CLASS_TOOL_SOURCE)
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory with no Python files."""
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLangChainParser:
    """Validate the LangChain tools parser."""

    def test_can_parse_class_tool(self, parser: LangChainParser, langchain_dir: Path) -> None:
        """Parser recognises a directory with BaseTool subclass."""
        assert parser.can_parse(langchain_dir) is True

    def test_can_parse_decorator_tool(
        self, parser: LangChainParser, langchain_decorator_dir: Path,
    ) -> None:
        """Parser recognises a directory with @tool decorated function."""
        assert parser.can_parse(langchain_decorator_dir) is True

    def test_can_parse_tools_subdir(
        self, parser: LangChainParser, langchain_tools_subdir: Path,
    ) -> None:
        """Parser finds tools in the tools/ subdirectory."""
        assert parser.can_parse(langchain_tools_subdir) is True

    def test_cannot_parse_empty_dir(self, parser: LangChainParser, empty_dir: Path) -> None:
        """Parser rejects a directory without LangChain tools."""
        assert parser.can_parse(empty_dir) is False

    def test_cannot_parse_non_langchain_python(
        self, parser: LangChainParser, tmp_path: Path,
    ) -> None:
        """Parser ignores plain Python files without LangChain imports."""
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_parse_class_tool_name(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """Extracts tool name from BaseTool.name class attribute."""
        skills = parser.parse(langchain_dir)
        assert len(skills) == 1
        assert skills[0].name == "web_search"

    def test_parse_class_tool_description(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """Extracts description from BaseTool.description attribute."""
        skills = parser.parse(langchain_dir)
        assert "Search the web" in skills[0].description

    def test_parse_decorator_tool_name(
        self, parser: LangChainParser, langchain_decorator_dir: Path,
    ) -> None:
        """Extracts tool name from @tool function name."""
        skills = parser.parse(langchain_decorator_dir)
        assert len(skills) == 1
        assert skills[0].name == "fetch_weather"

    def test_parse_decorator_tool_description(
        self, parser: LangChainParser, langchain_decorator_dir: Path,
    ) -> None:
        """Extracts description from @tool function docstring."""
        skills = parser.parse(langchain_decorator_dir)
        assert "Fetch weather" in skills[0].description

    def test_extracts_urls(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """Extracts URLs from tool code."""
        skills = parser.parse(langchain_dir)
        assert any("api.search.example.com" in u for u in skills[0].urls)

    def test_extracts_env_vars(
        self, parser: LangChainParser, langchain_decorator_dir: Path,
    ) -> None:
        """Extracts environment variable references."""
        skills = parser.parse(langchain_decorator_dir)
        assert "WEATHER_API_KEY" in skills[0].env_vars_referenced

    def test_extracts_shell_commands(
        self, parser: LangChainParser, tmp_path: Path,
    ) -> None:
        """Extracts shell commands from subprocess calls."""
        (tmp_path / "runner.py").write_text(_SHELL_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert any("ls" in cmd for cmd in skills[0].shell_commands)

    def test_extracts_dependencies(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """Extracts import dependencies from the source file."""
        skills = parser.parse(langchain_dir)
        assert "langchain" in skills[0].dependencies

    def test_extracts_code_blocks(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """Extracts code blocks (tool body) from parsed tools."""
        skills = parser.parse(langchain_dir)
        assert len(skills[0].code_blocks) >= 1
        assert "WebSearchTool" in skills[0].code_blocks[0]

    def test_format_is_correct(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """Parsed skills have format='langchain'."""
        skills = parser.parse(langchain_dir)
        assert skills[0].format == "langchain"

    def test_source_path_set(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """source_path points to the actual Python file."""
        skills = parser.parse(langchain_dir)
        assert skills[0].source_path.exists()
        assert skills[0].source_path.suffix == ".py"

    def test_raw_content_preserved(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """The full raw source content is preserved."""
        skills = parser.parse(langchain_dir)
        assert "BaseTool" in skills[0].raw_content

    def test_multiple_tools_in_one_file(
        self, parser: LangChainParser, tmp_path: Path,
    ) -> None:
        """Parses multiple tool definitions from a single file."""
        (tmp_path / "multi.py").write_text(_MULTI_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"tool_a", "tool_b"}

    def test_annotated_assignments(
        self, parser: LangChainParser, tmp_path: Path,
    ) -> None:
        """Handles type-annotated name/description assignments."""
        (tmp_path / "annotated.py").write_text(_ANNOTATED_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "annotated_search"
        assert "annotated tool" in skills[0].description.lower()

    def test_multiple_env_vars(
        self, parser: LangChainParser, tmp_path: Path,
    ) -> None:
        """Extracts multiple environment variable references."""
        (tmp_path / "secrets.py").write_text(_ENV_VARS_SOURCE)
        skills = parser.parse(tmp_path)
        assert "API_SECRET_KEY" in skills[0].env_vars_referenced
        assert "AUTH_TOKEN" in skills[0].env_vars_referenced

    def test_handles_empty_dir(
        self, parser: LangChainParser, empty_dir: Path,
    ) -> None:
        """Parsing an empty directory returns an empty list."""
        skills = parser.parse(empty_dir)
        assert skills == []

    def test_handles_malformed_python(
        self, parser: LangChainParser, tmp_path: Path,
    ) -> None:
        """Handles files with syntax errors gracefully via regex fallback."""
        malformed = "from langchain.tools import BaseTool\nclass Broken(BaseTool):\n  name = (\n"
        (tmp_path / "broken.py").write_text(malformed)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "Broken"

    def test_returns_parsed_skill_instances(
        self, parser: LangChainParser, langchain_dir: Path,
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(langchain_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)
