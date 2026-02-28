"""Tests for the MCP server deep scanner parser.

The ``McpServerParser`` analyses actual MCP server source code (Python and
TypeScript/JS) to extract security-relevant metadata: tool definitions,
environment variable access, shell commands, network calls, and filesystem
operations.  This complements ``McpConfigParser`` which only reads JSON
configuration files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.mcp_server import McpServerParser

# Path to test fixture files shipped with the repo.
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "mcp_server"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> McpServerParser:
    """Return a fresh McpServerParser instance."""
    return McpServerParser()


@pytest.fixture
def basic_server_dir(tmp_path: Path) -> Path:
    """Directory containing the minimal basic server fixture."""
    shutil.copy(_FIXTURES / "server_basic.py", tmp_path / "server.py")
    return tmp_path


@pytest.fixture
def overprivileged_dir(tmp_path: Path) -> Path:
    """Directory with the overprivileged server fixture."""
    shutil.copy(_FIXTURES / "server_overprivileged.py", tmp_path / "server.py")
    return tmp_path


@pytest.fixture
def safe_server_dir(tmp_path: Path) -> Path:
    """Directory with the safe calculator server fixture."""
    shutil.copy(_FIXTURES / "server_safe.py", tmp_path / "server.py")
    return tmp_path


@pytest.fixture
def env_leak_dir(tmp_path: Path) -> Path:
    """Directory with the env-leak server fixture."""
    shutil.copy(_FIXTURES / "server_env_leak.py", tmp_path / "server.py")
    return tmp_path


@pytest.fixture
def ts_server_dir(tmp_path: Path) -> Path:
    """Directory with a TypeScript MCP server fixture."""
    shutil.copy(_FIXTURES / "server_basic.ts", tmp_path / "index.ts")
    return tmp_path


@pytest.fixture
def package_json_dir(tmp_path: Path) -> Path:
    """Directory with only a package.json referencing the MCP SDK."""
    shutil.copy(_FIXTURES / "package.json", tmp_path / "package.json")
    return tmp_path


@pytest.fixture
def no_auth_dir(tmp_path: Path) -> Path:
    """Directory with the no-auth server fixture."""
    shutil.copy(_FIXTURES / "server_no_auth.py", tmp_path / "server.py")
    return tmp_path


# ---------------------------------------------------------------------------
# TestCanParse
# ---------------------------------------------------------------------------


class TestCanParse:
    """Validate the ``can_parse`` detection logic."""

    def test_detects_python_mcp_server(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        assert parser.can_parse(basic_server_dir) is True

    def test_detects_ts_mcp_server(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        assert parser.can_parse(ts_server_dir) is True

    def test_detects_package_json_mcp(
        self, parser: McpServerParser, package_json_dir: Path
    ) -> None:
        assert parser.can_parse(package_json_dir) is True

    def test_rejects_empty_dir(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        assert parser.can_parse(tmp_path) is False

    def test_rejects_non_mcp_python(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        (tmp_path / "server.py").write_text("print('hello')\n")
        assert parser.can_parse(tmp_path) is False

    def test_rejects_file_not_dir(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        filepath = tmp_path / "server.py"
        filepath.write_text("from mcp.server import Server\n")
        assert parser.can_parse(filepath) is False

    def test_detects_pyproject_with_mcp(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["mcp>=1.0"]\n'
        )
        assert parser.can_parse(tmp_path) is True

    def test_rejects_pyproject_without_mcp(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["flask>=3.0"]\n'
        )
        assert parser.can_parse(tmp_path) is False


# ---------------------------------------------------------------------------
# TestParsePython
# ---------------------------------------------------------------------------


class TestParsePython:
    """Validate parsing of Python MCP server source files."""

    def test_returns_parsed_skill(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        skills = parser.parse(basic_server_dir)
        assert len(skills) == 1
        assert isinstance(skills[0], ParsedSkill)

    def test_format_is_mcp_server(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        skill = parser.parse(basic_server_dir)[0]
        assert skill.format == "mcp_server"

    def test_extracts_tool_name_in_description(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        skill = parser.parse(basic_server_dir)[0]
        assert "greet" in skill.description

    def test_safe_server_has_no_dangerous_caps(
        self, parser: McpServerParser, safe_server_dir: Path
    ) -> None:
        skill = parser.parse(safe_server_dir)[0]
        assert "system:execute" not in skill.declared_capabilities
        assert "network:read" not in skill.declared_capabilities
        assert "credentials:read" not in skill.declared_capabilities

    def test_overprivileged_detects_shell(
        self, parser: McpServerParser, overprivileged_dir: Path
    ) -> None:
        skill = parser.parse(overprivileged_dir)[0]
        assert "system:execute" in skill.declared_capabilities
        assert len(skill.shell_commands) > 0

    def test_overprivileged_detects_network(
        self, parser: McpServerParser, overprivileged_dir: Path
    ) -> None:
        skill = parser.parse(overprivileged_dir)[0]
        assert "network:read" in skill.declared_capabilities
        assert "network:write" in skill.declared_capabilities

    def test_overprivileged_detects_filesystem(
        self, parser: McpServerParser, overprivileged_dir: Path
    ) -> None:
        skill = parser.parse(overprivileged_dir)[0]
        assert "filesystem:read" in skill.declared_capabilities
        assert "filesystem:write" in skill.declared_capabilities

    def test_overprivileged_detects_credentials(
        self, parser: McpServerParser, overprivileged_dir: Path
    ) -> None:
        skill = parser.parse(overprivileged_dir)[0]
        assert "credentials:read" in skill.declared_capabilities

    def test_overprivileged_env_vars(
        self, parser: McpServerParser, overprivileged_dir: Path
    ) -> None:
        skill = parser.parse(overprivileged_dir)[0]
        env_vars = skill.env_vars_referenced
        assert "DB_PASSWORD" in env_vars
        assert "OPENAI_API_KEY" in env_vars
        assert "APP_SECRET_KEY" in env_vars

    def test_env_leak_server_captures_all_vars(
        self, parser: McpServerParser, env_leak_dir: Path
    ) -> None:
        skill = parser.parse(env_leak_dir)[0]
        env_vars = skill.env_vars_referenced
        assert "GITHUB_TOKEN" in env_vars
        assert "AWS_SECRET_ACCESS_KEY" in env_vars
        assert "DATABASE_PASSWORD" in env_vars
        assert "OPENAI_API_KEY" in env_vars
        assert "LOG_LEVEL" in env_vars

    def test_env_leak_server_detects_urls(
        self, parser: McpServerParser, env_leak_dir: Path
    ) -> None:
        skill = parser.parse(env_leak_dir)[0]
        assert any("exfil.example.com" in url for url in skill.urls)

    def test_no_auth_server_detects_file_access(
        self, parser: McpServerParser, no_auth_dir: Path
    ) -> None:
        skill = parser.parse(no_auth_dir)[0]
        assert "filesystem:read" in skill.declared_capabilities

    def test_source_path_points_to_file(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        skill = parser.parse(basic_server_dir)[0]
        assert skill.source_path.exists()
        assert skill.source_path.suffix == ".py"

    def test_raw_content_is_populated(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        skill = parser.parse(basic_server_dir)[0]
        assert "from mcp.server import Server" in skill.raw_content

    def test_code_blocks_contain_source(
        self, parser: McpServerParser, basic_server_dir: Path
    ) -> None:
        skill = parser.parse(basic_server_dir)[0]
        assert len(skill.code_blocks) == 1
        assert "def greet" in skill.code_blocks[0]

    def test_multiple_tools_in_description(
        self, parser: McpServerParser, overprivileged_dir: Path
    ) -> None:
        skill = parser.parse(overprivileged_dir)[0]
        # At least 2 tool names should appear in the description.
        tool_names = ["run_shell", "fetch_url", "manage_files", "read_secrets"]
        matches = sum(1 for name in tool_names if name in skill.description)
        assert matches >= 2


# ---------------------------------------------------------------------------
# TestParseTypeScript
# ---------------------------------------------------------------------------


class TestParseTypeScript:
    """Validate parsing of TypeScript MCP server source files."""

    def test_returns_parsed_skill(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skills = parser.parse(ts_server_dir)
        assert len(skills) == 1
        assert isinstance(skills[0], ParsedSkill)

    def test_format_is_mcp_server(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skill = parser.parse(ts_server_dir)[0]
        assert skill.format == "mcp_server"

    def test_extracts_tool_names(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skill = parser.parse(ts_server_dir)[0]
        assert "greet" in skill.description
        assert "fetch_data" in skill.description

    def test_detects_env_vars(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skill = parser.parse(ts_server_dir)[0]
        assert "API_SECRET_KEY" in skill.env_vars_referenced

    def test_detects_network_capability(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skill = parser.parse(ts_server_dir)[0]
        assert "network:read" in skill.declared_capabilities

    def test_detects_credentials_capability(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skill = parser.parse(ts_server_dir)[0]
        assert "credentials:read" in skill.declared_capabilities

    def test_detects_env_read_capability(
        self, parser: McpServerParser, ts_server_dir: Path
    ) -> None:
        skill = parser.parse(ts_server_dir)[0]
        assert "env:read" in skill.declared_capabilities
