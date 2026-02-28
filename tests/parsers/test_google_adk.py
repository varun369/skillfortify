"""Tests for Google ADK parser — detection, agent parsing, and capabilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.google_adk import GoogleADKParser

# ---------------------------------------------------------------------------
# Sample sources
# ---------------------------------------------------------------------------

_BASIC_AGENT_SOURCE = '''\
from google.adk import Agent

def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {"temp": 72}

agent = Agent(
    model="gemini-2.0-flash",
    name="weather_agent",
    instruction="Help users check weather",
    tools=[get_weather],
)
'''

_BUILTIN_TOOLS_SOURCE = '''\
from google.adk import Agent
from google.adk.tools import google_search, code_execution

agent = Agent(
    model="gemini-2.0-flash",
    name="search_agent",
    instruction="Search and execute code",
    tools=[google_search, code_execution],
)
'''

_MULTI_AGENT_SOURCE = '''\
from google.adk import Agent
from google.adk.tools import google_search

def summarize(text: str) -> str:
    """Summarize text content."""
    return text[:100]

researcher = Agent(
    name="researcher",
    model="gemini-2.0-flash",
    instruction="Research topics",
    tools=[google_search],
)

coordinator = Agent(
    name="coordinator",
    model="gemini-2.0-flash",
    instruction="Coordinate work",
    tools=[researcher, summarize],
)
'''

_FUNCTION_TOOL_WRAPPER_SOURCE = '''\
from google.adk import Agent
from google.adk.tools import FunctionTool

def raw_func(x: str) -> str:
    """A raw function wrapped by FunctionTool."""
    return x.upper()

wrapped = FunctionTool(raw_func)

agent = Agent(
    name="wrapper_agent",
    model="gemini-2.0-flash",
    instruction="Agent with FunctionTool wrapper",
    tools=[wrapped],
)
'''

_CALLBACK_SOURCE = '''\
from google.adk import Agent

def before_tool_callback(tool, args, tool_context):
    """Pre-tool execution hook."""
    print(f"Calling {tool}")

def my_tool(x: str) -> str:
    """Simple tool."""
    return x

agent = Agent(
    name="callback_agent",
    model="gemini-2.0-flash",
    instruction="Agent with callbacks",
    tools=[my_tool],
    before_tool_callback=before_tool_callback,
)
'''

_NO_ADK_SOURCE = '''\
import flask

app = flask.Flask(__name__)

@app.route("/")
def index():
    return "Hello"
'''

_MALFORMED_SOURCE = '''\
from google.adk import Agent
def broken(
    # missing closing paren
agent = Agent(name="broken_agent", tools=[broken])
'''


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> GoogleADKParser:
    """Instantiate a fresh GoogleADKParser."""
    return GoogleADKParser()


@pytest.fixture
def basic_dir(tmp_path: Path) -> Path:
    """Directory with a basic Google ADK agent."""
    (tmp_path / "agent.py").write_text(_BASIC_AGENT_SOURCE)
    return tmp_path


@pytest.fixture
def builtin_dir(tmp_path: Path) -> Path:
    """Directory with built-in tools agent."""
    (tmp_path / "agent.py").write_text(_BUILTIN_TOOLS_SOURCE)
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory with no Python files."""
    return tmp_path


# ---------------------------------------------------------------------------
# Tests: can_parse
# ---------------------------------------------------------------------------


class TestCanParse:
    """Validate can_parse detection for Google ADK projects."""

    def test_detects_basic_agent(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Recognises a directory with google.adk imports."""
        assert parser.can_parse(basic_dir) is True

    def test_detects_builtin_tools(
        self, parser: GoogleADKParser, builtin_dir: Path,
    ) -> None:
        """Recognises built-in tool imports."""
        assert parser.can_parse(builtin_dir) is True

    def test_rejects_empty_dir(
        self, parser: GoogleADKParser, empty_dir: Path,
    ) -> None:
        """Rejects empty directory."""
        assert parser.can_parse(empty_dir) is False

    def test_rejects_non_adk_python(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Rejects Python files without Google ADK imports."""
        (tmp_path / "app.py").write_text(_NO_ADK_SOURCE)
        assert parser.can_parse(tmp_path) is False

    def test_detects_in_tools_subdir(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Finds ADK files in tools/ subdirectory."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "my_agent.py").write_text(_BASIC_AGENT_SOURCE)
        assert parser.can_parse(tmp_path) is True

    def test_detects_in_agents_subdir(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Finds ADK files in agents/ subdirectory."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "main.py").write_text(_BASIC_AGENT_SOURCE)
        assert parser.can_parse(tmp_path) is True


# ---------------------------------------------------------------------------
# Tests: parse — Agent definitions
# ---------------------------------------------------------------------------


class TestParseAgents:
    """Validate parsing of Agent() constructor calls."""

    def test_extracts_agent_name(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Extracts agent name from Agent(name=...)."""
        skills = parser.parse(basic_dir)
        agent_skills = [s for s in skills if s.name == "weather_agent"]
        assert len(agent_skills) == 1

    def test_extracts_instruction_as_description(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Uses instruction kwarg as the skill description."""
        skills = parser.parse(basic_dir)
        agent_skills = [s for s in skills if s.name == "weather_agent"]
        assert "weather" in agent_skills[0].description.lower()

    def test_format_is_google_adk(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """All parsed skills have format='google_adk'."""
        skills = parser.parse(basic_dir)
        for skill in skills:
            assert skill.format == "google_adk"

    def test_source_path_set(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """source_path points to the actual Python file."""
        skills = parser.parse(basic_dir)
        for skill in skills:
            assert skill.source_path.exists()
            assert skill.source_path.suffix == ".py"

    def test_raw_content_preserved(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Raw source content is preserved in raw_content."""
        skills = parser.parse(basic_dir)
        agent_skills = [s for s in skills if s.name == "weather_agent"]
        assert "google.adk" in agent_skills[0].raw_content

    def test_returns_parsed_skill_instances(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(basic_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)

    def test_multi_agent_extracts_all(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Extracts multiple Agent definitions from one file."""
        (tmp_path / "multi.py").write_text(_MULTI_AGENT_SOURCE)
        skills = parser.parse(tmp_path)
        agent_names = {s.name for s in skills}
        assert "researcher" in agent_names
        assert "coordinator" in agent_names

    def test_empty_dir_returns_empty(
        self, parser: GoogleADKParser, empty_dir: Path,
    ) -> None:
        """Parsing an empty directory returns an empty list."""
        assert parser.parse(empty_dir) == []

    def test_extracts_dependencies(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Extracts import dependencies."""
        skills = parser.parse(basic_dir)
        agent_skills = [s for s in skills if s.name == "weather_agent"]
        assert "google" in agent_skills[0].dependencies


# ---------------------------------------------------------------------------
# Tests: parse — Capabilities
# ---------------------------------------------------------------------------


class TestParseCapabilities:
    """Validate capability extraction from tools lists."""

    def test_builtin_tools_capabilities(
        self, parser: GoogleADKParser, builtin_dir: Path,
    ) -> None:
        """Built-in tools are tagged as builtin:name capabilities."""
        skills = parser.parse(builtin_dir)
        agent_skills = [s for s in skills if s.name == "search_agent"]
        caps = agent_skills[0].declared_capabilities
        assert "builtin:google_search" in caps
        assert "builtin:code_execution" in caps

    def test_function_tool_capabilities(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """User-defined tools are tagged as tool:name capabilities."""
        skills = parser.parse(basic_dir)
        agent_skills = [s for s in skills if s.name == "weather_agent"]
        caps = agent_skills[0].declared_capabilities
        assert "tool:get_weather" in caps

    def test_sub_agent_capabilities(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Sub-agents in tools list are tagged as tool:name."""
        (tmp_path / "multi.py").write_text(_MULTI_AGENT_SOURCE)
        skills = parser.parse(tmp_path)
        coord = [s for s in skills if s.name == "coordinator"]
        caps = coord[0].declared_capabilities
        assert "tool:researcher" in caps


# ---------------------------------------------------------------------------
# Tests: parse — Function tools
# ---------------------------------------------------------------------------


class TestParseFunctionTools:
    """Validate extraction of function definitions used as tools."""

    def test_extracts_function_tool(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Extracts function definitions referenced in Agent tools."""
        skills = parser.parse(basic_dir)
        func_skills = [s for s in skills if s.name == "get_weather"]
        assert len(func_skills) == 1

    def test_function_tool_docstring(
        self, parser: GoogleADKParser, basic_dir: Path,
    ) -> None:
        """Uses function docstring as description."""
        skills = parser.parse(basic_dir)
        func_skills = [s for s in skills if s.name == "get_weather"]
        assert "weather" in func_skills[0].description.lower()

    def test_function_tool_wrapper(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Extracts functions wrapped with FunctionTool()."""
        (tmp_path / "wrapped.py").write_text(_FUNCTION_TOOL_WRAPPER_SOURCE)
        skills = parser.parse(tmp_path)
        func_skills = [s for s in skills if s.name == "raw_func"]
        assert len(func_skills) == 1

    def test_callback_not_extracted_as_tool(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Callback functions are not extracted as separate tools."""
        (tmp_path / "cb.py").write_text(_CALLBACK_SOURCE)
        skills = parser.parse(tmp_path)
        names = {s.name for s in skills}
        assert "before_tool_callback" not in names

    def test_callback_agent_still_parsed(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Agent with callback kwarg is still extracted properly."""
        (tmp_path / "cb.py").write_text(_CALLBACK_SOURCE)
        skills = parser.parse(tmp_path)
        assert any(s.name == "callback_agent" for s in skills)


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Validate robustness against malformed and edge-case inputs."""

    def test_malformed_source_no_crash(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Parser does not crash on malformed Python source."""
        (tmp_path / "broken.py").write_text(_MALFORMED_SOURCE)
        skills = parser.parse(tmp_path)
        assert isinstance(skills, list)

    def test_binary_file_skipped(
        self, parser: GoogleADKParser, tmp_path: Path,
    ) -> None:
        """Binary files are silently skipped."""
        (tmp_path / "data.py").write_bytes(b"\x00\x01\x02\x03")
        assert parser.parse(tmp_path) == []
