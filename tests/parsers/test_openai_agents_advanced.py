"""Tests for the OpenAI Agents SDK parser — advanced patterns.

Covers MCP server connections, hosted tools, handoffs, guardrails,
unsafe pattern detection, and edge-case robustness. Core extraction
tests live in ``test_openai_agents.py``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

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
def mcp_dir(tmp_path: Path) -> Path:
    """Directory with MCP server connections."""
    shutil.copy(_FIXTURES / "mcp_agent.py", tmp_path / "mcp_agent.py")
    return tmp_path


@pytest.fixture
def hosted_dir(tmp_path: Path) -> Path:
    """Directory with hosted tool imports."""
    shutil.copy(_FIXTURES / "hosted_tools.py", tmp_path / "hosted_tools.py")
    return tmp_path


@pytest.fixture
def handoff_dir(tmp_path: Path) -> Path:
    """Directory with agent-to-agent handoffs."""
    shutil.copy(_FIXTURES / "handoff_agent.py", tmp_path / "handoff_agent.py")
    return tmp_path


@pytest.fixture
def guardrails_dir(tmp_path: Path) -> Path:
    """Directory with guardrail definitions."""
    shutil.copy(_FIXTURES / "guardrails_agent.py", tmp_path / "guardrails_agent.py")
    return tmp_path


@pytest.fixture
def unsafe_dir(tmp_path: Path) -> Path:
    """Directory with unsafe agent patterns."""
    shutil.copy(_FIXTURES / "unsafe_agent.py", tmp_path / "unsafe_agent.py")
    return tmp_path


# --------------------------------------------------------------------------- #
# MCP server tests                                                             #
# --------------------------------------------------------------------------- #

class TestMcpServers:
    """Validate extraction of MCP server connections."""

    def test_extracts_stdio_server(
        self, parser: OpenAIAgentsParser, mcp_dir: Path,
    ) -> None:
        skills = parser.parse(mcp_dir)
        stdio = [s for s in skills if s.name == "uvx"]
        assert len(stdio) == 1
        caps = stdio[0].declared_capabilities
        assert any("mcp:MCPServerStdio" in cap for cap in caps)

    def test_extracts_http_server_url(
        self, parser: OpenAIAgentsParser, mcp_dir: Path,
    ) -> None:
        skills = parser.parse(mcp_dir)
        all_urls: list[str] = []
        for skill in skills:
            all_urls.extend(skill.urls)
        assert any("mcp.internal.corp.net" in url for url in all_urls)

    def test_mcp_agent_has_mcp_access(
        self, parser: OpenAIAgentsParser, mcp_dir: Path,
    ) -> None:
        skills = parser.parse(mcp_dir)
        agent = [s for s in skills if s.name == "mcp_agent"]
        assert len(agent) == 1
        assert "mcp_access" in agent[0].declared_capabilities

    def test_http_server_named_by_url(
        self, parser: OpenAIAgentsParser, mcp_dir: Path,
    ) -> None:
        skills = parser.parse(mcp_dir)
        http = [s for s in skills if "mcp.internal.corp.net" in s.name]
        assert len(http) == 1


# --------------------------------------------------------------------------- #
# Hosted tools tests                                                           #
# --------------------------------------------------------------------------- #

class TestHostedTools:
    """Validate detection of hosted tool imports."""

    def test_detects_web_search_tool(
        self, parser: OpenAIAgentsParser, hosted_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(hosted_dir)}
        assert "WebSearchTool" in names

    def test_detects_file_search_tool(
        self, parser: OpenAIAgentsParser, hosted_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(hosted_dir)}
        assert "FileSearchTool" in names

    def test_detects_code_interpreter_tool(
        self, parser: OpenAIAgentsParser, hosted_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(hosted_dir)}
        assert "CodeInterpreterTool" in names

    def test_hosted_tool_has_capability(
        self, parser: OpenAIAgentsParser, hosted_dir: Path,
    ) -> None:
        web = [s for s in parser.parse(hosted_dir) if s.name == "WebSearchTool"]
        assert web
        assert "hosted:WebSearchTool" in web[0].declared_capabilities


# --------------------------------------------------------------------------- #
# Handoff tests                                                                #
# --------------------------------------------------------------------------- #

class TestHandoffs:
    """Validate detection of agent-to-agent handoff patterns."""

    def test_triage_has_handoff_capability(
        self, parser: OpenAIAgentsParser, handoff_dir: Path,
    ) -> None:
        triage = [s for s in parser.parse(handoff_dir) if s.name == "triage_agent"]
        assert triage
        assert "agent_handoff" in triage[0].declared_capabilities

    def test_specialist_has_handoff_description(
        self, parser: OpenAIAgentsParser, handoff_dir: Path,
    ) -> None:
        spec = [s for s in parser.parse(handoff_dir) if s.name == "order_specialist"]
        assert spec
        assert "order" in spec[0].description.lower()

    def test_both_agents_extracted(
        self, parser: OpenAIAgentsParser, handoff_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(handoff_dir)}
        assert "triage_agent" in names
        assert "order_specialist" in names

    def test_function_tool_in_handoff_file(
        self, parser: OpenAIAgentsParser, handoff_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(handoff_dir)}
        assert "lookup_order" in names


# --------------------------------------------------------------------------- #
# Guardrail tests                                                              #
# --------------------------------------------------------------------------- #

class TestGuardrails:
    """Validate detection of guardrail patterns."""

    def test_agent_has_input_guardrail(
        self, parser: OpenAIAgentsParser, guardrails_dir: Path,
    ) -> None:
        agent = [s for s in parser.parse(guardrails_dir) if s.name == "guarded_agent"]
        assert agent
        assert "input_guardrail" in agent[0].declared_capabilities

    def test_agent_has_output_guardrail(
        self, parser: OpenAIAgentsParser, guardrails_dir: Path,
    ) -> None:
        agent = [s for s in parser.parse(guardrails_dir) if s.name == "guarded_agent"]
        assert agent
        assert "output_guardrail" in agent[0].declared_capabilities

    def test_guardrail_function_tool_extracted(
        self, parser: OpenAIAgentsParser, guardrails_dir: Path,
    ) -> None:
        names = {s.name for s in parser.parse(guardrails_dir)}
        assert "search_docs" in names


# --------------------------------------------------------------------------- #
# Unsafe pattern detection tests                                               #
# --------------------------------------------------------------------------- #

class TestUnsafePatterns:
    """Validate detection of shell commands, env vars, and URLs."""

    def test_extracts_env_vars(
        self, parser: OpenAIAgentsParser, unsafe_dir: Path,
    ) -> None:
        diag = [s for s in parser.parse(unsafe_dir) if s.name == "run_diagnostic"]
        assert diag
        assert "ADMIN_TOKEN" in diag[0].env_vars_referenced
        assert "EXTERNAL_API_KEY" in diag[0].env_vars_referenced

    def test_extracts_shell_commands(
        self, parser: OpenAIAgentsParser, unsafe_dir: Path,
    ) -> None:
        diag = [s for s in parser.parse(unsafe_dir) if s.name == "run_diagnostic"]
        assert diag
        assert any("curl" in cmd for cmd in diag[0].shell_commands)

    def test_extracts_external_urls(
        self, parser: OpenAIAgentsParser, unsafe_dir: Path,
    ) -> None:
        fetch = [s for s in parser.parse(unsafe_dir) if s.name == "fetch_remote"]
        assert fetch
        assert any("internal.corp.net" in url for url in fetch[0].urls)

    def test_extracts_os_system_commands(
        self, parser: OpenAIAgentsParser, unsafe_dir: Path,
    ) -> None:
        fetch = [s for s in parser.parse(unsafe_dir) if s.name == "fetch_remote"]
        assert fetch
        assert any("rm" in cmd for cmd in fetch[0].shell_commands)


# --------------------------------------------------------------------------- #
# Edge cases and robustness tests                                              #
# --------------------------------------------------------------------------- #

class TestEdgeCases:
    """Robustness: empty dirs, malformed files, no-match content."""

    def test_empty_dir_returns_empty(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        assert parser.parse(tmp_path) == []

    def test_syntax_error_uses_fallback(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        """Files with syntax errors should not crash the parser."""
        bad = tmp_path / "bad.py"
        bad.write_text("from agents import function_tool\n@function_tool\ndef broken(\n")
        skills = parser.parse(tmp_path)
        assert isinstance(skills, list)

    def test_non_python_files_ignored(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        (tmp_path / "config.yaml").write_text("from agents import Agent\n")
        assert parser.can_parse(tmp_path) is False

    def test_unreadable_file_skipped(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        bad = tmp_path / "locked.py"
        bad.write_text("from agents import Agent\n")
        bad.chmod(0o000)
        try:
            parser.parse(tmp_path)
        finally:
            bad.chmod(0o644)

    def test_multiple_files_aggregated(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        shutil.copy(_FIXTURES / "basic_agent.py", tmp_path / "a.py")
        shutil.copy(_FIXTURES / "handoff_agent.py", tmp_path / "b.py")
        names = {s.name for s in parser.parse(tmp_path)}
        assert "get_weather" in names
        assert "lookup_order" in names

    def test_agents_subdir_discovered(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        sub = tmp_path / "agents"
        sub.mkdir()
        shutil.copy(_FIXTURES / "basic_agent.py", sub / "weather.py")
        assert any(s.name == "get_weather" for s in parser.parse(tmp_path))

    def test_src_subdir_discovered(
        self, parser: OpenAIAgentsParser, tmp_path: Path,
    ) -> None:
        sub = tmp_path / "src"
        sub.mkdir()
        shutil.copy(_FIXTURES / "basic_agent.py", sub / "main.py")
        assert any(s.name == "get_weather" for s in parser.parse(tmp_path))
