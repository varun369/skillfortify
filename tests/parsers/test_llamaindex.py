"""Tests for the LlamaIndex tools parser.

LlamaIndex tools are Python files containing FunctionTool.from_defaults(),
QueryEngineTool(), ReActAgent.from_tools(), and data reader instantiations.
The parser extracts names, descriptions, capabilities, shell commands,
URLs, environment variables, dependencies, and code blocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.llamaindex_tools import LlamaIndexParser

# ---------------------------------------------------------------------------
# Inline source fragments
# ---------------------------------------------------------------------------

_FUNCTION_TOOL = (
    "from llama_index.core.tools import FunctionTool\n\n"
    "def multiply(a: int, b: int) -> int:\n"
    '    """Multiply two numbers."""\n'
    "    return a * b\n\n"
    "tool = FunctionTool.from_defaults(fn=multiply)\n"
)

_NAMED_TOOL = (
    "from llama_index.core.tools import FunctionTool\n\n"
    "def compute(x: int) -> int:\n"
    '    """Compute."""\n    return x * 2\n\n'
    "tool = FunctionTool.from_defaults(\n"
    '    fn=compute, name="calculator", description="A simple calculator",\n)\n'
)

_QUERY_ENGINE = (
    "from llama_index.core.tools import QueryEngineTool, ToolMetadata\n\n"
    "tool = QueryEngineTool(\n    query_engine=None,\n"
    "    metadata=ToolMetadata(\n"
    '        name="doc_search", description="Search through documents",\n    ),\n)\n'
)

_REACT_AGENT = (
    "from llama_index.core.agent import ReActAgent\n"
    "from llama_index.core.tools import FunctionTool\n"
    "from llama_index.llms.openai import OpenAI\n\n"
    "def greet(name: str) -> str:\n"
    '    """Greet someone."""\n    return f"Hello {name}"\n\n'
    "tool = FunctionTool.from_defaults(fn=greet)\n"
    'agent = ReActAgent.from_tools([tool], llm=OpenAI(model="gpt-4"))\n'
)

_DATA_READER = (
    "from llama_index.readers.web import SimpleWebPageReader\n\n"
    "reader = SimpleWebPageReader(html_to_text=True)\n"
    'docs = reader.load_data(urls=["https://example.com/page"])\n'
)

_ENV_VARS = (
    "from llama_index.core.tools import FunctionTool\nimport os\n\n"
    "def secret_fn(x: str) -> str:\n"
    '    """Access secret."""\n'
    '    key = os.environ["OPENAI_API_KEY"]\n'
    '    token = os.getenv("AUTH_TOKEN")\n    return x\n\n'
    "tool = FunctionTool.from_defaults(fn=secret_fn)\n"
)

_SHELL_CMD = (
    "from llama_index.core.tools import FunctionTool\nimport subprocess\n\n"
    "def run_cmd(cmd: str) -> str:\n"
    '    """Run a command."""\n'
    '    return subprocess.run("ls -la /tmp", capture_output=True, text=True).stdout\n\n'
    "tool = FunctionTool.from_defaults(fn=run_cmd)\n"
)

_URL_TOOL = (
    "from llama_index.core.tools import FunctionTool\n\n"
    "def fetch(url: str) -> str:\n"
    '    """Fetch data."""\n    import requests\n'
    '    return requests.get("https://api.example.com/v1/data").text\n\n'
    'tool = FunctionTool.from_defaults(fn=fetch, name="api_fetch")\n'
)

_MULTI_TOOLS = (
    "from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata\n\n"
    "def add(a, b): return a + b\ndef sub(a, b): return a - b\n\n"
    "add_tool = FunctionTool.from_defaults(fn=add)\n"
    "sub_tool = FunctionTool.from_defaults(fn=sub)\n"
    "q = QueryEngineTool(query_engine=None,\n"
    '    metadata=ToolMetadata(name="search", description="Search docs"))\n'
)

_POSITIONAL_FN = (
    "from llama_index.core.tools import FunctionTool\n\n"
    "def helper(x: str) -> str:\n"
    '    """A helper."""\n    return x\n\n'
    "tool = FunctionTool.from_defaults(helper)\n"
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "llamaindex"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def parser() -> LlamaIndexParser:
    return LlamaIndexParser()


@pytest.fixture
def fn_dir(tmp_path: Path) -> Path:
    (tmp_path / "tools.py").write_text(_FUNCTION_TOOL)
    return tmp_path


@pytest.fixture
def qe_dir(tmp_path: Path) -> Path:
    (tmp_path / "query.py").write_text(_QUERY_ENGINE)
    return tmp_path


@pytest.fixture
def agent_dir(tmp_path: Path) -> Path:
    (tmp_path / "agent.py").write_text(_REACT_AGENT)
    return tmp_path


@pytest.fixture
def reader_dir(tmp_path: Path) -> Path:
    (tmp_path / "reader.py").write_text(_DATA_READER)
    return tmp_path


# ---------------------------------------------------------------------------
# can_parse
# ---------------------------------------------------------------------------

class TestCanParse:
    """Validate LlamaIndex format detection."""

    def test_detects_function_tool(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        assert parser.can_parse(fn_dir) is True

    def test_detects_query_engine(self, parser: LlamaIndexParser, qe_dir: Path) -> None:
        assert parser.can_parse(qe_dir) is True

    def test_detects_agent(self, parser: LlamaIndexParser, agent_dir: Path) -> None:
        assert parser.can_parse(agent_dir) is True

    def test_detects_reader(self, parser: LlamaIndexParser, reader_dir: Path) -> None:
        assert parser.can_parse(reader_dir) is True

    def test_rejects_empty(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        assert parser.can_parse(tmp_path) is False

    def test_rejects_plain_python(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_detects_tools_subdir(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        sub = tmp_path / "tools"
        sub.mkdir()
        (sub / "t.py").write_text(_FUNCTION_TOOL)
        assert parser.can_parse(tmp_path) is True


# ---------------------------------------------------------------------------
# FunctionTool
# ---------------------------------------------------------------------------

class TestFunctionTool:
    """Validate FunctionTool.from_defaults() extraction."""

    def test_extracts_name(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        skills = parser.parse(fn_dir)
        assert any(s.name == "multiply" for s in skills)

    def test_named_kwarg(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "c.py").write_text(_NAMED_TOOL)
        skills = parser.parse(tmp_path)
        assert any(s.name == "calculator" for s in skills)
        calc = [s for s in skills if s.name == "calculator"][0]
        assert "simple calculator" in calc.description.lower()

    def test_positional_fn(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "p.py").write_text(_POSITIONAL_FN)
        skills = parser.parse(tmp_path)
        assert any(s.name == "helper" for s in skills)

    def test_capabilities(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        skills = parser.parse(fn_dir)
        fn_skill = [s for s in skills if s.name == "multiply"][0]
        assert "tool:multiply" in fn_skill.declared_capabilities


# ---------------------------------------------------------------------------
# QueryEngineTool
# ---------------------------------------------------------------------------

class TestQueryEngineTool:
    """Validate QueryEngineTool extraction."""

    def test_extracts_name(self, parser: LlamaIndexParser, qe_dir: Path) -> None:
        skills = parser.parse(qe_dir)
        assert any(s.name == "doc_search" for s in skills)

    def test_description(self, parser: LlamaIndexParser, qe_dir: Path) -> None:
        skills = parser.parse(qe_dir)
        skill = [s for s in skills if s.name == "doc_search"][0]
        assert "Search through documents" in skill.description

    def test_capabilities(self, parser: LlamaIndexParser, qe_dir: Path) -> None:
        skills = parser.parse(qe_dir)
        skill = [s for s in skills if s.name == "doc_search"][0]
        assert "query_engine:read" in skill.declared_capabilities


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TestAgent:
    """Validate ReActAgent.from_tools() extraction."""

    def test_extracts_agent(self, parser: LlamaIndexParser, agent_dir: Path) -> None:
        skills = parser.parse(agent_dir)
        assert any(s.name == "ReActAgent" for s in skills)

    def test_agent_description(self, parser: LlamaIndexParser, agent_dir: Path) -> None:
        skills = parser.parse(agent_dir)
        agent_skill = [s for s in skills if s.name == "ReActAgent"][0]
        assert "ReActAgent" in agent_skill.description

    def test_agent_tool_caps(self, parser: LlamaIndexParser, agent_dir: Path) -> None:
        skills = parser.parse(agent_dir)
        agent_skill = [s for s in skills if s.name == "ReActAgent"][0]
        assert "tool:tool" in agent_skill.declared_capabilities


# ---------------------------------------------------------------------------
# Data reader
# ---------------------------------------------------------------------------

class TestDataReader:
    """Validate data reader extraction."""

    def test_extracts_reader(self, parser: LlamaIndexParser, reader_dir: Path) -> None:
        skills = parser.parse(reader_dir)
        assert any(s.name == "SimpleWebPageReader" for s in skills)

    def test_reader_caps(self, parser: LlamaIndexParser, reader_dir: Path) -> None:
        skills = parser.parse(reader_dir)
        skill = [s for s in skills if s.name == "SimpleWebPageReader"][0]
        assert "reader:SimpleWebPageReader" in skill.declared_capabilities


# ---------------------------------------------------------------------------
# Security extraction
# ---------------------------------------------------------------------------

class TestSecurity:
    """Validate extraction of security-sensitive patterns."""

    def test_env_vars(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "e.py").write_text(_ENV_VARS)
        skills = parser.parse(tmp_path)
        all_env = {v for s in skills for v in s.env_vars_referenced}
        assert "OPENAI_API_KEY" in all_env
        assert "AUTH_TOKEN" in all_env

    def test_shell_commands(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "s.py").write_text(_SHELL_CMD)
        skills = parser.parse(tmp_path)
        all_cmds = [c for s in skills for c in s.shell_commands]
        assert any("ls" in cmd for cmd in all_cmds)

    def test_urls(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "u.py").write_text(_URL_TOOL)
        skills = parser.parse(tmp_path)
        all_urls = [u for s in skills for u in s.urls]
        assert any("api.example.com" in url for url in all_urls)

    def test_dependencies(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        skills = parser.parse(fn_dir)
        assert "llama_index" in skills[0].dependencies


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------

class TestOutputShape:
    """Validate structural properties of parser output."""

    def test_format(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        for skill in parser.parse(fn_dir):
            assert skill.format == "llamaindex"

    def test_source_path(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        for skill in parser.parse(fn_dir):
            assert skill.source_path.exists()
            assert skill.source_path.suffix == ".py"

    def test_raw_content(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        for skill in parser.parse(fn_dir):
            assert "FunctionTool" in skill.raw_content

    def test_code_blocks(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        for skill in parser.parse(fn_dir):
            assert len(skill.code_blocks) >= 1

    def test_parsed_skill_type(self, parser: LlamaIndexParser, fn_dir: Path) -> None:
        for skill in parser.parse(fn_dir):
            assert isinstance(skill, ParsedSkill)

    def test_multiple_tools(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "m.py").write_text(_MULTI_TOOLS)
        skills = parser.parse(tmp_path)
        assert len(skills) >= 3


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Validate graceful handling of edge cases."""

    def test_empty_dir(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        assert parser.parse(tmp_path) == []

    def test_malformed_no_raise(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        bad = "from llama_index.core.tools import FunctionTool\ntool = FunctionTool.from_defaults(\n"
        (tmp_path / "b.py").write_text(bad)
        skills = parser.parse(tmp_path)
        assert isinstance(skills, list)

    def test_malformed_regex_fallback(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        bad = "from llama_index.core.tools import FunctionTool\ntool = FunctionTool.from_defaults(\n"
        (tmp_path / "b.py").write_text(bad)
        assert len(parser.parse(tmp_path)) >= 1

    def test_non_utf8_skipped(self, parser: LlamaIndexParser, tmp_path: Path) -> None:
        (tmp_path / "x.py").write_bytes(b"\xff\xfe" + b"from llama_index" + b"\x00" * 50)
        assert isinstance(parser.parse(tmp_path), list)

    def test_fixture_basic(self, parser: LlamaIndexParser) -> None:
        if not FIXTURES_DIR.exists():
            pytest.skip("Fixtures directory not found")
        skills = parser.parse(FIXTURES_DIR)
        names = {s.name for s in skills}
        assert "multiply" in names or "addition" in names

    def test_fixture_env_vars(self, parser: LlamaIndexParser) -> None:
        if not FIXTURES_DIR.exists():
            pytest.skip("Fixtures directory not found")
        skills = parser.parse(FIXTURES_DIR)
        all_env = {v for s in skills for v in s.env_vars_referenced}
        assert "SECRET_API_KEY" in all_env

    def test_fixture_urls(self, parser: LlamaIndexParser) -> None:
        if not FIXTURES_DIR.exists():
            pytest.skip("Fixtures directory not found")
        skills = parser.parse(FIXTURES_DIR)
        all_urls = [u for s in skills for u in s.urls]
        assert any("evil.example.com" in url for url in all_urls)

    def test_fixture_shell(self, parser: LlamaIndexParser) -> None:
        if not FIXTURES_DIR.exists():
            pytest.skip("Fixtures directory not found")
        skills = parser.parse(FIXTURES_DIR)
        all_cmds = [c for s in skills for c in s.shell_commands]
        assert any("rm" in cmd for cmd in all_cmds)
