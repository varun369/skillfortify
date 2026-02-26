"""Tests for the AutoGen tools parser.

AutoGen registers tools via @agent.register_for_llm decorators and function
schema dicts. The parser must extract names, descriptions, shell commands,
URLs, environment variables, dependencies, and code blocks from both
registration patterns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.autogen import AutoGenParser


# ---------------------------------------------------------------------------
# Sample sources
# ---------------------------------------------------------------------------

_REGISTER_TOOL_SOURCE = '''\
from autogen import AssistantAgent, UserProxyAgent
import requests

assistant = AssistantAgent("assistant")

@assistant.register_for_llm(description="Search the web for information")
def search(query: str) -> str:
    resp = requests.get("https://api.search.example.com/v1", params={"q": query})
    return resp.text
'''

_FUNCTION_SCHEMA_SOURCE = '''\
from autogen import AssistantAgent

functions = [
    {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
]

assistant = AssistantAgent("assistant", llm_config={"functions": functions})
'''

_SHELL_TOOL_SOURCE = '''\
from autogen import AssistantAgent
import subprocess

assistant = AssistantAgent("assistant")

@assistant.register_for_llm(description="Execute a command")
def run_command(cmd: str) -> str:
    return subprocess.run("whoami", capture_output=True, text=True).stdout
'''

_ENV_VARS_SOURCE = '''\
from autogen import AssistantAgent
import os

assistant = AssistantAgent("assistant")

@assistant.register_for_llm(description="Fetch secret data")
def fetch_secret(key: str) -> str:
    token = os.environ["SECRET_TOKEN"]
    api_key = os.getenv("API_KEY")
    return f"{token}:{api_key}"
'''

_MULTI_REGISTER_SOURCE = '''\
from autogen import AssistantAgent

assistant = AssistantAgent("assistant")

@assistant.register_for_llm(description="First tool")
def tool_one(x: str) -> str:
    return x

@assistant.register_for_llm(description="Second tool")
def tool_two(x: str) -> str:
    return x
'''

_MULTI_SCHEMA_SOURCE = '''\
from autogen import AssistantAgent

functions = [
    {
        "name": "func_a",
        "description": "Function A",
        "parameters": {"type": "object"}
    },
    {
        "name": "func_b",
        "description": "Function B",
        "parameters": {"type": "object"}
    }
]
'''

_PYAUTOGEN_SOURCE = '''\
from pyautogen import AssistantAgent

assistant = AssistantAgent("assistant")

@assistant.register_for_llm(description="PyAutoGen tool")
def py_tool(x: str) -> str:
    return x
'''

_DOCSTRING_FALLBACK_SOURCE = '''\
from autogen import AssistantAgent

assistant = AssistantAgent("assistant")

@assistant.register_for_llm()
def documented_tool(x: str) -> str:
    """This tool has a docstring description."""
    return x
'''

_URL_SOURCE = '''\
from autogen import AssistantAgent
import requests

assistant = AssistantAgent("assistant")

@assistant.register_for_llm(description="Fetch data from API")
def fetch_data(endpoint: str) -> str:
    resp = requests.post("https://internal.corp.net/api/data")
    return resp.text
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> AutoGenParser:
    return AutoGenParser()


@pytest.fixture
def register_dir(tmp_path: Path) -> Path:
    """Directory with a register_for_llm tool."""
    (tmp_path / "search.py").write_text(_REGISTER_TOOL_SOURCE)
    return tmp_path


@pytest.fixture
def schema_dir(tmp_path: Path) -> Path:
    """Directory with a function schema tool."""
    (tmp_path / "config.py").write_text(_FUNCTION_SCHEMA_SOURCE)
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAutoGenParser:
    """Validate the AutoGen tools parser."""

    def test_can_parse_register_tool(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """Parser recognises register_for_llm decorated functions."""
        assert parser.can_parse(register_dir) is True

    def test_can_parse_function_schema(
        self, parser: AutoGenParser, schema_dir: Path,
    ) -> None:
        """Parser recognises function schema dicts."""
        assert parser.can_parse(schema_dir) is True

    def test_cannot_parse_empty_dir(self, parser: AutoGenParser, empty_dir: Path) -> None:
        """Parser rejects a directory without AutoGen tools."""
        assert parser.can_parse(empty_dir) is False

    def test_cannot_parse_non_autogen_python(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Parser ignores plain Python files without AutoGen markers."""
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_parse_register_tool_name(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """Extracts function name from register_for_llm tool."""
        skills = parser.parse(register_dir)
        reg_skills = [s for s in skills if s.name == "search"]
        assert len(reg_skills) == 1

    def test_parse_register_tool_description(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """Extracts description from register_for_llm keyword argument."""
        skills = parser.parse(register_dir)
        reg_skills = [s for s in skills if s.name == "search"]
        assert "Search the web" in reg_skills[0].description

    def test_parse_function_schema_name(
        self, parser: AutoGenParser, schema_dir: Path,
    ) -> None:
        """Extracts name from function schema dict."""
        skills = parser.parse(schema_dir)
        schema_skills = [s for s in skills if s.name == "get_weather"]
        assert len(schema_skills) == 1

    def test_parse_function_schema_description(
        self, parser: AutoGenParser, schema_dir: Path,
    ) -> None:
        """Extracts description from function schema dict."""
        skills = parser.parse(schema_dir)
        schema_skills = [s for s in skills if s.name == "get_weather"]
        assert "Get weather" in schema_skills[0].description

    def test_extracts_urls(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Extracts URLs from tool code."""
        (tmp_path / "api.py").write_text(_URL_SOURCE)
        skills = parser.parse(tmp_path)
        reg_skills = [s for s in skills if s.name == "fetch_data"]
        assert any("internal.corp.net" in u for u in reg_skills[0].urls)

    def test_extracts_env_vars(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Extracts environment variable references."""
        (tmp_path / "secrets.py").write_text(_ENV_VARS_SOURCE)
        skills = parser.parse(tmp_path)
        reg_skills = [s for s in skills if s.name == "fetch_secret"]
        assert "SECRET_TOKEN" in reg_skills[0].env_vars_referenced
        assert "API_KEY" in reg_skills[0].env_vars_referenced

    def test_extracts_shell_commands(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Extracts shell commands from subprocess calls."""
        (tmp_path / "cmd.py").write_text(_SHELL_TOOL_SOURCE)
        skills = parser.parse(tmp_path)
        reg_skills = [s for s in skills if s.name == "run_command"]
        assert any("whoami" in cmd for cmd in reg_skills[0].shell_commands)

    def test_extracts_dependencies(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """Extracts import dependencies."""
        skills = parser.parse(register_dir)
        reg_skills = [s for s in skills if s.name == "search"]
        assert "autogen" in reg_skills[0].dependencies

    def test_format_is_correct(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """All parsed skills have format='autogen'."""
        skills = parser.parse(register_dir)
        for skill in skills:
            assert skill.format == "autogen"

    def test_multiple_register_tools(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Parses multiple register_for_llm functions from one file."""
        (tmp_path / "multi.py").write_text(_MULTI_REGISTER_SOURCE)
        skills = parser.parse(tmp_path)
        reg_skills = [s for s in skills if s.name in ("tool_one", "tool_two")]
        assert len(reg_skills) == 2

    def test_multiple_function_schemas(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Parses multiple function schema dicts."""
        (tmp_path / "schemas.py").write_text(_MULTI_SCHEMA_SOURCE)
        skills = parser.parse(tmp_path)
        names = {s.name for s in skills}
        assert "func_a" in names
        assert "func_b" in names

    def test_pyautogen_import(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Recognises pyautogen import (alternative package name)."""
        (tmp_path / "pyag.py").write_text(_PYAUTOGEN_SOURCE)
        assert parser.can_parse(tmp_path) is True
        skills = parser.parse(tmp_path)
        assert any(s.name == "py_tool" for s in skills)

    def test_docstring_fallback_description(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Falls back to docstring when register_for_llm has no description."""
        (tmp_path / "doc.py").write_text(_DOCSTRING_FALLBACK_SOURCE)
        skills = parser.parse(tmp_path)
        doc_skills = [s for s in skills if s.name == "documented_tool"]
        assert doc_skills
        assert "docstring description" in doc_skills[0].description

    def test_source_path_set(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """source_path points to the actual Python file."""
        skills = parser.parse(register_dir)
        for skill in skills:
            assert skill.source_path.exists()
            assert skill.source_path.suffix == ".py"

    def test_raw_content_preserved(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """Raw source content is preserved."""
        skills = parser.parse(register_dir)
        reg_skills = [s for s in skills if s.name == "search"]
        assert "AssistantAgent" in reg_skills[0].raw_content

    def test_handles_empty_dir(
        self, parser: AutoGenParser, empty_dir: Path,
    ) -> None:
        """Parsing an empty directory returns an empty list."""
        skills = parser.parse(empty_dir)
        assert skills == []

    def test_returns_parsed_skill_instances(
        self, parser: AutoGenParser, register_dir: Path,
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(register_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)

    def test_tools_subdir(
        self, parser: AutoGenParser, tmp_path: Path,
    ) -> None:
        """Parser finds tools in the tools/ subdirectory."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "agent_tools.py").write_text(_REGISTER_TOOL_SOURCE)
        assert parser.can_parse(tmp_path) is True
        skills = parser.parse(tmp_path)
        assert any(s.name == "search" for s in skills)
