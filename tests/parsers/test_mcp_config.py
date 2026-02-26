"""Tests for the MCP server configuration parser.

MCP (Model Context Protocol) server configurations are stored in JSON files
such as ``mcp.json``, ``.mcp.json``, or ``claude_desktop_config.json``. Each
file contains an ``mcpServers`` map whose keys are server names and whose
values specify the command, arguments, and environment variables needed to
launch the server.

Each MCP server entry is treated as a skill with security-relevant metadata:
the command and args form shell commands, and the env block surfaces environment
variable references (which may contain secrets).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.mcp_config import McpConfigParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> McpConfigParser:
    return McpConfigParser()


@pytest.fixture
def mcp_config_dir(tmp_path: Path) -> Path:
    """Create a directory with a standard mcp.json file."""
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"NODE_ENV": "production"},
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "ghp_xxxxx"},
            },
        }
    }
    (tmp_path / "mcp.json").write_text(json.dumps(config))
    return tmp_path


@pytest.fixture
def hidden_mcp_config_dir(tmp_path: Path) -> Path:
    """Create a directory with a .mcp.json (hidden variant)."""
    config = {
        "mcpServers": {
            "database": {
                "command": "python",
                "args": ["-m", "mcp_server_postgres"],
                "env": {"DATABASE_URL": "postgres://localhost/mydb"},
            }
        }
    }
    (tmp_path / ".mcp.json").write_text(json.dumps(config))
    return tmp_path


@pytest.fixture
def claude_desktop_config_dir(tmp_path: Path) -> Path:
    """Create a directory with claude_desktop_config.json."""
    config = {
        "mcpServers": {
            "brave-search": {
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-server-brave-search"],
                "env": {"BRAVE_API_KEY": "bsk_xxx"},
            }
        }
    }
    (tmp_path / "claude_desktop_config.json").write_text(json.dumps(config))
    return tmp_path


@pytest.fixture
def empty_mcp_dir(tmp_path: Path) -> Path:
    """Create a directory with an mcp.json that has no servers."""
    config: dict = {"mcpServers": {}}
    (tmp_path / "mcp.json").write_text(json.dumps(config))
    return tmp_path


@pytest.fixture
def malformed_mcp_dir(tmp_path: Path) -> Path:
    """Create a directory with an invalid JSON file."""
    (tmp_path / "mcp.json").write_text("{not valid json!!!")
    return tmp_path


# ---------------------------------------------------------------------------
# TestMcpConfigParser
# ---------------------------------------------------------------------------


class TestMcpConfigParser:
    """Validate the MCP server configuration parser."""

    def test_can_parse_valid_dir(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """Parser recognises a directory containing mcp.json."""
        assert parser.can_parse(mcp_config_dir) is True

    def test_can_parse_hidden_mcp(
        self, parser: McpConfigParser, hidden_mcp_config_dir: Path
    ) -> None:
        """Parser recognises .mcp.json (hidden variant)."""
        assert parser.can_parse(hidden_mcp_config_dir) is True

    def test_can_parse_claude_desktop(
        self, parser: McpConfigParser, claude_desktop_config_dir: Path
    ) -> None:
        """Parser recognises claude_desktop_config.json."""
        assert parser.can_parse(claude_desktop_config_dir) is True

    def test_cannot_parse_invalid_dir(self, parser: McpConfigParser, tmp_path: Path) -> None:
        """Parser rejects a directory without any MCP config file."""
        assert parser.can_parse(tmp_path) is False

    def test_parses_skill_name(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """Each MCP server key becomes a ParsedSkill name."""
        skills = parser.parse(mcp_config_dir)
        names = {s.name for s in skills}
        assert "filesystem" in names
        assert "github" in names

    def test_extracts_description(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """Description includes the server command for identification."""
        skills = parser.parse(mcp_config_dir)
        fs_skill = next(s for s in skills if s.name == "filesystem")
        assert "npx" in fs_skill.description

    def test_extracts_env_vars(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """Extracts environment variable names from the env block."""
        skills = parser.parse(mcp_config_dir)
        gh_skill = next(s for s in skills if s.name == "github")
        assert "GITHUB_TOKEN" in gh_skill.env_vars_referenced

    def test_extracts_shell_commands(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """The command + args are captured as shell commands."""
        skills = parser.parse(mcp_config_dir)
        fs_skill = next(s for s in skills if s.name == "filesystem")
        assert any("npx" in cmd for cmd in fs_skill.shell_commands)
        assert any("@modelcontextprotocol/server-filesystem" in cmd for cmd in fs_skill.shell_commands)

    def test_format_is_correct(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """Parsed skills must have format='mcp'."""
        skills = parser.parse(mcp_config_dir)
        for skill in skills:
            assert skill.format == "mcp"

    def test_source_path_is_set(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """source_path points to the actual config file on disk."""
        skills = parser.parse(mcp_config_dir)
        for skill in skills:
            assert skill.source_path.exists()
            assert skill.source_path.name == "mcp.json"

    def test_handles_empty_servers(self, parser: McpConfigParser, empty_mcp_dir: Path) -> None:
        """Parsing an MCP config with empty mcpServers returns an empty list."""
        skills = parser.parse(empty_mcp_dir)
        assert skills == []

    def test_handles_malformed_content(
        self, parser: McpConfigParser, malformed_mcp_dir: Path
    ) -> None:
        """Parsing invalid JSON returns an empty list rather than crashing."""
        skills = parser.parse(malformed_mcp_dir)
        assert skills == []

    def test_returns_parsed_skill_instances(
        self, parser: McpConfigParser, mcp_config_dir: Path
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(mcp_config_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)

    def test_parses_two_servers(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """The fixture has two server entries -- both must be parsed."""
        skills = parser.parse(mcp_config_dir)
        assert len(skills) == 2

    def test_dependencies_from_args(self, parser: McpConfigParser, mcp_config_dir: Path) -> None:
        """npm package references in args are captured as dependencies."""
        skills = parser.parse(mcp_config_dir)
        fs_skill = next(s for s in skills if s.name == "filesystem")
        assert any(
            "@modelcontextprotocol/server-filesystem" in dep
            for dep in fs_skill.dependencies
        )
