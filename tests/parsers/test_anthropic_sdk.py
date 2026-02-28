"""Tests for the Anthropic Agent SDK parser.

Covers ``can_parse`` probing, ``@tool`` extraction, ``Agent(...)``
instantiation, ``MCPServer(...)`` connections, ``Hook`` subclass
detection, sub-agent patterns, unsafe pattern detection, and edge cases.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.anthropic_sdk import AnthropicSDKParser

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "anthropic_sdk"


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

@pytest.fixture
def parser() -> AnthropicSDKParser:
    """Fresh parser instance."""
    return AnthropicSDKParser()


@pytest.fixture
def basic_dir(tmp_path: Path) -> Path:
    shutil.copy(_FIXTURES / "basic_agent.py", tmp_path / "basic_agent.py")
    return tmp_path


@pytest.fixture
def mcp_dir(tmp_path: Path) -> Path:
    shutil.copy(_FIXTURES / "mcp_tools.py", tmp_path / "mcp_tools.py")
    return tmp_path


@pytest.fixture
def hooks_dir(tmp_path: Path) -> Path:
    shutil.copy(_FIXTURES / "hooks_agent.py", tmp_path / "hooks_agent.py")
    return tmp_path


@pytest.fixture
def sub_agents_dir(tmp_path: Path) -> Path:
    shutil.copy(_FIXTURES / "sub_agents.py", tmp_path / "sub_agents.py")
    return tmp_path


@pytest.fixture
def unsafe_dir(tmp_path: Path) -> Path:
    shutil.copy(_FIXTURES / "unsafe_agent.py", tmp_path / "unsafe_agent.py")
    return tmp_path


# --------------------------------------------------------------------------- #
# can_parse tests                                                              #
# --------------------------------------------------------------------------- #

class TestCanParse:
    """Validate the can_parse probe method."""

    def test_detects_basic_agent(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        assert parser.can_parse(basic_dir) is True

    def test_rejects_empty_dir(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        assert parser.can_parse(tmp_path) is False

    def test_rejects_non_sdk_python(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_detects_requirements_txt(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("claude-agent-sdk>=0.1\nrequests\n")
        assert parser.can_parse(tmp_path) is True

    def test_detects_pyproject_toml(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["claude-agent-sdk>=0.1"]\n',
        )
        assert parser.can_parse(tmp_path) is True

    def test_finds_files_in_tools_subdir(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "tools").mkdir()
        shutil.copy(_FIXTURES / "basic_agent.py", tmp_path / "tools" / "agent.py")
        assert parser.can_parse(tmp_path) is True

    def test_finds_files_in_agents_subdir(
        self, parser: AnthropicSDKParser, tmp_path: Path,
    ) -> None:
        (tmp_path / "agents").mkdir()
        shutil.copy(_FIXTURES / "basic_agent.py", tmp_path / "agents" / "main.py")
        assert parser.can_parse(tmp_path) is True

    def test_detects_mcp_imports(self, parser: AnthropicSDKParser, mcp_dir: Path) -> None:
        assert parser.can_parse(mcp_dir) is True

    def test_detects_hooks_imports(self, parser: AnthropicSDKParser, hooks_dir: Path) -> None:
        assert parser.can_parse(hooks_dir) is True


# --------------------------------------------------------------------------- #
# @tool extraction tests                                                       #
# --------------------------------------------------------------------------- #

class TestToolExtraction:
    """Validate extraction of @tool decorated functions."""

    def test_extracts_tool_names(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        names = {s.name for s in parser.parse(basic_dir)}
        assert "search_files" in names
        assert "fetch_weather" in names

    def test_extracts_docstring(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        weather = [s for s in parser.parse(basic_dir) if s.name == "fetch_weather"]
        assert weather and "weather" in weather[0].description.lower()

    def test_extracts_urls(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        weather = [s for s in parser.parse(basic_dir) if s.name == "fetch_weather"]
        assert weather and any("api.weather.com" in u for u in weather[0].urls)

    def test_format_is_anthropic_sdk(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        for skill in parser.parse(basic_dir):
            assert skill.format == "anthropic_sdk"

    def test_source_path_set(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        for skill in parser.parse(basic_dir):
            assert skill.source_path.exists() and skill.source_path.suffix == ".py"

    def test_raw_content_preserved(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        tool_skills = [s for s in parser.parse(basic_dir) if s.name == "search_files"]
        assert tool_skills and "claude_agent_sdk" in tool_skills[0].raw_content

    def test_returns_parsed_skill_instances(
        self, parser: AnthropicSDKParser, basic_dir: Path,
    ) -> None:
        for skill in parser.parse(basic_dir):
            assert isinstance(skill, ParsedSkill)

    def test_extracts_dependencies(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        tool_skills = [s for s in parser.parse(basic_dir) if s.name == "fetch_weather"]
        assert tool_skills
        assert "requests" in tool_skills[0].dependencies
        assert "claude_agent_sdk" in tool_skills[0].dependencies


# --------------------------------------------------------------------------- #
# Agent instantiation tests                                                    #
# --------------------------------------------------------------------------- #

class TestAgentInstantiation:
    """Validate extraction of Agent(...) calls."""

    def test_extracts_agent_name(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        agents = [s for s in parser.parse(basic_dir) if s.name == "research_assistant"]
        assert len(agents) == 1

    def test_extracts_instructions(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "research_assistant"]
        assert agent and "research" in agent[0].instructions.lower()

    def test_model_capability(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "research_assistant"]
        assert agent and "model:claude-sonnet-4-20250514" in agent[0].declared_capabilities

    def test_version_is_unknown(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "research_assistant"]
        assert agent and agent[0].version == "unknown"

    def test_tool_capabilities(self, parser: AnthropicSDKParser, basic_dir: Path) -> None:
        agent = [s for s in parser.parse(basic_dir) if s.name == "research_assistant"]
        assert agent
        caps = agent[0].declared_capabilities
        assert "tool:search_files" in caps and "tool:fetch_weather" in caps


# --------------------------------------------------------------------------- #
# MCPServer extraction tests                                                   #
# --------------------------------------------------------------------------- #

class TestMCPServers:
    """Validate extraction of MCPServer(...) instantiations."""

    def test_extracts_mcp_names(self, parser: AnthropicSDKParser, mcp_dir: Path) -> None:
        names = {s.name for s in parser.parse(mcp_dir) if "mcp:" in str(s.declared_capabilities)}
        assert "npx" in names and "uvx" in names

    def test_mcp_capability(self, parser: AnthropicSDKParser, mcp_dir: Path) -> None:
        npx = [s for s in parser.parse(mcp_dir) if s.name == "npx"]
        assert npx and "mcp:npx" in npx[0].declared_capabilities

    def test_mcp_agent_detected(self, parser: AnthropicSDKParser, mcp_dir: Path) -> None:
        assert len([s for s in parser.parse(mcp_dir) if s.name == "mcp_agent"]) == 1

    def test_mcp_format(self, parser: AnthropicSDKParser, mcp_dir: Path) -> None:
        for skill in parser.parse(mcp_dir):
            assert skill.format == "anthropic_sdk"


# --------------------------------------------------------------------------- #
# Hook extraction tests                                                        #
# --------------------------------------------------------------------------- #

class TestHookExtraction:
    """Validate extraction of Hook subclass definitions."""

    def test_extracts_hook_names(self, parser: AnthropicSDKParser, hooks_dir: Path) -> None:
        names = {s.name for s in parser.parse(hooks_dir) if "hook:" in str(s.declared_capabilities)}
        assert "AuditHook" in names and "RateLimitHook" in names

    def test_hook_method_capabilities(self, parser: AnthropicSDKParser, hooks_dir: Path) -> None:
        audit = [s for s in parser.parse(hooks_dir) if s.name == "AuditHook"]
        assert audit
        caps = audit[0].declared_capabilities
        assert "hook:before_tool_call" in caps and "hook:after_tool_call" in caps

    def test_hook_docstring(self, parser: AnthropicSDKParser, hooks_dir: Path) -> None:
        audit = [s for s in parser.parse(hooks_dir) if s.name == "AuditHook"]
        assert audit and "audit" in audit[0].description.lower()

    def test_agent_with_hooks(self, parser: AnthropicSDKParser, hooks_dir: Path) -> None:
        agent = [s for s in parser.parse(hooks_dir) if s.name == "audited_agent"]
        assert agent and "lifecycle_hooks" in agent[0].declared_capabilities


# --------------------------------------------------------------------------- #
# Sub-agent extraction tests                                                   #
# --------------------------------------------------------------------------- #

class TestSubAgents:
    """Validate extraction of sub-agent delegation patterns."""

    def test_extracts_all_agents(
        self, parser: AnthropicSDKParser, sub_agents_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(sub_agents_dir)
                 if "model:" in str(s.declared_capabilities)}
        assert {"researcher", "writer", "coordinator"} <= names

    def test_coordinator_references_sub_agents(
        self, parser: AnthropicSDKParser, sub_agents_dir: Path,
    ) -> None:
        coord = [s for s in parser.parse(sub_agents_dir) if s.name == "coordinator"]
        assert coord
        caps = coord[0].declared_capabilities
        assert "tool:researcher" in caps and "tool:writer" in caps

    def test_each_agent_has_model(
        self, parser: AnthropicSDKParser, sub_agents_dir: Path,
    ) -> None:
        skills = parser.parse(sub_agents_dir)
        researcher = [s for s in skills if s.name == "researcher"]
        coord = [s for s in skills if s.name == "coordinator"]
        assert researcher and "model:claude-haiku-4-5-20251001" in researcher[0].declared_capabilities
        assert coord and "model:claude-sonnet-4-20250514" in coord[0].declared_capabilities

    def test_tool_function_extracted(
        self, parser: AnthropicSDKParser, sub_agents_dir: Path,
    ) -> None:
        assert "web_search" in {s.name for s in parser.parse(sub_agents_dir)}


# --------------------------------------------------------------------------- #
# Unsafe pattern detection tests                                               #
# --------------------------------------------------------------------------- #

class TestUnsafePatterns:
    """Validate detection of dangerous patterns in tool code."""

    def test_detects_env_vars(self, parser: AnthropicSDKParser, unsafe_dir: Path) -> None:
        cmd = [s for s in parser.parse(unsafe_dir) if s.name == "run_command"]
        assert cmd
        env = cmd[0].env_vars_referenced
        assert "ADMIN_SECRET_KEY" in env and "CLOUD_API_TOKEN" in env

    def test_detects_shell_commands(self, parser: AnthropicSDKParser, unsafe_dir: Path) -> None:
        cmd = [s for s in parser.parse(unsafe_dir) if s.name == "run_command"]
        assert cmd and len(cmd[0].shell_commands) > 0

    def test_detects_external_urls(self, parser: AnthropicSDKParser, unsafe_dir: Path) -> None:
        exfil = [s for s in parser.parse(unsafe_dir) if s.name == "exfiltrate_data"]
        assert exfil and any("internal.corp.net" in u for u in exfil[0].urls)

    def test_detects_evil_url(self, parser: AnthropicSDKParser, unsafe_dir: Path) -> None:
        cmd = [s for s in parser.parse(unsafe_dir) if s.name == "run_command"]
        assert cmd and any("evil.exfil.site" in u for u in cmd[0].urls)

    def test_unsafe_agent_extracted(self, parser: AnthropicSDKParser, unsafe_dir: Path) -> None:
        assert len([s for s in parser.parse(unsafe_dir) if s.name == "unsafe_agent"]) == 1


# --------------------------------------------------------------------------- #
# Edge case and robustness tests                                               #
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    """Validate robustness on malformed and edge-case inputs."""

    def test_empty_dir_returns_empty(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        assert parser.parse(tmp_path) == []

    def test_syntax_error_no_raise(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text(
            "from claude_agent_sdk import Agent\ndef broken(:\n    pass\n",
        )
        assert isinstance(parser.parse(tmp_path), list)

    def test_binary_file_no_raise(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "data.py").write_bytes(
            b"\x00\x01from claude_agent_sdk import Agent\xff\xfe",
        )
        assert isinstance(parser.parse(tmp_path), list)

    def test_no_agent_name_skipped(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "anon.py").write_text(
            "from claude_agent_sdk import Agent\n"
            'agent = Agent(model="claude-sonnet-4-20250514")\n',
        )
        names = [s.name for s in parser.parse(tmp_path)]
        assert all(n != "" for n in names)

    def test_multiple_files_aggregated(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        shutil.copy(_FIXTURES / "basic_agent.py", tmp_path / "basic.py")
        shutil.copy(_FIXTURES / "mcp_tools.py", tmp_path / "mcp.py")
        names = {s.name for s in parser.parse(tmp_path)}
        assert "search_files" in names and "npx" in names

    def test_empty_file_no_crash(self, parser: AnthropicSDKParser, tmp_path: Path) -> None:
        (tmp_path / "empty.py").write_text("from claude_agent_sdk import Agent\n")
        assert isinstance(parser.parse(tmp_path), list)
