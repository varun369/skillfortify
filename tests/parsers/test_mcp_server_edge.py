"""Edge case and error handling tests for the MCP server deep scanner.

Covers malformed input, empty directories, syntax errors, unreadable files,
mixed-format directories, and boundary conditions that the core test suite
does not exercise.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.mcp_server import McpServerParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> McpServerParser:
    """Return a fresh McpServerParser instance."""
    return McpServerParser()


# ---------------------------------------------------------------------------
# TestMalformedInput
# ---------------------------------------------------------------------------


class TestMalformedInput:
    """Parser must never raise on bad input — return empty results instead."""

    def test_syntax_error_python_returns_empty(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Python file with syntax error should yield a skill with no tools."""
        source = "from mcp.server import Server\n\ndef broken(:\n  pass\n"
        (tmp_path / "server.py").write_text(source)
        skills = parser.parse(tmp_path)
        # File is detected as MCP (import matches), but AST fails gracefully.
        assert len(skills) == 1
        assert skills[0].declared_capabilities == []

    def test_empty_python_file_no_match(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """An empty .py file should not match as an MCP server."""
        (tmp_path / "server.py").write_text("")
        assert parser.can_parse(tmp_path) is False

    def test_binary_file_no_crash(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Binary content in server.py must not crash the parser."""
        (tmp_path / "server.py").write_bytes(b"\x00\x01\x02\xff" * 100)
        # Should not raise — returns False or empty.
        assert parser.can_parse(tmp_path) is False

    def test_malformed_package_json(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Invalid JSON in package.json must not crash."""
        (tmp_path / "package.json").write_text("{not valid json!!!")
        assert parser.can_parse(tmp_path) is False

    def test_package_json_missing_dependencies(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """package.json without dependencies key should not match."""
        (tmp_path / "package.json").write_text(json.dumps({"name": "foo"}))
        assert parser.can_parse(tmp_path) is False

    def test_parse_nonexistent_path(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Parsing a non-existent directory returns empty list."""
        fake_path = tmp_path / "does_not_exist"
        result = parser.parse(fake_path)
        assert result == []

    def test_parse_file_instead_of_dir(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Passing a file path instead of a directory returns empty."""
        filepath = tmp_path / "server.py"
        filepath.write_text("from mcp.server import Server\n")
        result = parser.parse(filepath)
        assert result == []


# ---------------------------------------------------------------------------
# TestEmptyAndMinimal
# ---------------------------------------------------------------------------


class TestEmptyAndMinimal:
    """Boundary tests for minimal and degenerate inputs."""

    def test_mcp_import_only_no_tools(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """A file with only the import and no tool definitions."""
        source = (
            "from mcp.server import Server\n"
            "app = Server('empty')\n"
        )
        (tmp_path / "server.py").write_text(source)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert "0 tools" in skills[0].description

    def test_empty_dir_parse_returns_empty(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Parsing an empty directory returns no skills."""
        assert parser.parse(tmp_path) == []

    def test_ts_import_only_no_tools(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """A TS file with import but no tool registrations."""
        source = (
            'import { Server } from "@modelcontextprotocol/sdk/server";\n'
            "const server = new Server();\n"
        )
        (tmp_path / "index.ts").write_text(source)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert "0 tools" in skills[0].description


# ---------------------------------------------------------------------------
# TestMixedFormats
# ---------------------------------------------------------------------------


class TestMixedFormats:
    """Directory containing multiple MCP server files (Python + TS)."""

    def test_parses_both_py_and_ts(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Parser should return skills from both Python and TS files."""
        py_source = (
            "from mcp.server import Server\n"
            "app = Server('py-server')\n"
            "@app.tool()\n"
            "async def py_tool(): pass\n"
        )
        ts_source = (
            'import { Server } from "@modelcontextprotocol/sdk/server";\n'
            "const s = new Server();\n"
            "s.tool('ts_tool', async () => {});\n"
        )
        (tmp_path / "server.py").write_text(py_source)
        (tmp_path / "index.ts").write_text(ts_source)
        skills = parser.parse(tmp_path)
        assert len(skills) == 2
        formats = {s.format for s in skills}
        assert formats == {"mcp_server"}

    def test_non_mcp_python_files_ignored(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Non-MCP Python files in the same directory are skipped."""
        mcp_source = (
            "from mcp.server import Server\n"
            "app = Server('real')\n"
        )
        other_source = "import flask\napp = flask.Flask(__name__)\n"
        (tmp_path / "server.py").write_text(mcp_source)
        (tmp_path / "utils.py").write_text(other_source)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "server"


# ---------------------------------------------------------------------------
# TestAlternateImportStyles
# ---------------------------------------------------------------------------


class TestAlternateImportStyles:
    """Validate detection across different MCP import patterns."""

    def test_from_mcp_import_server(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """``from mcp import Server`` is detected."""
        source = "from mcp import Server\napp = Server('alt')\n"
        (tmp_path / "main.py").write_text(source)
        assert parser.can_parse(tmp_path) is True

    def test_require_style_js(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """CommonJS ``require("@modelcontextprotocol/sdk")`` is detected."""
        source = (
            'const { Server } = require("@modelcontextprotocol/sdk/server");\n'
        )
        (tmp_path / "index.js").write_text(source)
        assert parser.can_parse(tmp_path) is True

    def test_js_extension_parsed(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """.js files with MCP imports are parsed, not just .ts."""
        source = (
            'const { Server } = require("@modelcontextprotocol/sdk/server");\n'
            "const s = new Server();\n"
            "s.tool('js_tool', async () => {});\n"
        )
        (tmp_path / "index.js").write_text(source)
        skills = parser.parse(tmp_path)
        assert len(skills) == 1
        assert "js_tool" in skills[0].description


# ---------------------------------------------------------------------------
# TestCapabilityInference
# ---------------------------------------------------------------------------


class TestCapabilityInference:
    """Validate that capabilities are correctly inferred from code patterns."""

    def test_open_call_adds_filesystem(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """A bare ``open()`` call should flag filesystem capabilities."""
        source = (
            "from mcp.server import Server\n"
            "app = Server('fs')\n"
            "@app.tool()\n"
            "async def read_file(path: str):\n"
            "    with open(path) as fh:\n"
            "        return fh.read()\n"
        )
        (tmp_path / "server.py").write_text(source)
        skill = parser.parse(tmp_path)[0]
        assert "filesystem:read" in skill.declared_capabilities

    def test_subprocess_adds_system_execute(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Importing subprocess flags system:execute."""
        source = (
            "from mcp.server import Server\n"
            "import subprocess\n"
            "app = Server('cmd')\n"
            "@app.tool()\n"
            "async def run(cmd: str):\n"
            "    return subprocess.run(cmd, shell=True)\n"
        )
        (tmp_path / "server.py").write_text(source)
        skill = parser.parse(tmp_path)[0]
        assert "system:execute" in skill.declared_capabilities
        assert "subprocess.run" in skill.shell_commands

    def test_no_sensitive_env_no_credentials_cap(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Env vars without sensitive patterns should NOT flag credentials."""
        source = (
            "import os\n"
            "from mcp.server import Server\n"
            "app = Server('safe-env')\n"
            "@app.tool()\n"
            "async def config():\n"
            "    return os.environ.get('LOG_LEVEL')\n"
        )
        (tmp_path / "server.py").write_text(source)
        skill = parser.parse(tmp_path)[0]
        assert "env:read" in skill.declared_capabilities
        assert "credentials:read" not in skill.declared_capabilities

    def test_sensitive_env_flags_credentials(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Env var with SECRET in the name should flag credentials:read."""
        source = (
            "import os\n"
            "from mcp.server import Server\n"
            "app = Server('cred')\n"
            "@app.tool()\n"
            "async def secret():\n"
            "    return os.environ.get('MY_SECRET_VALUE')\n"
        )
        (tmp_path / "server.py").write_text(source)
        skill = parser.parse(tmp_path)[0]
        assert "credentials:read" in skill.declared_capabilities

    def test_version_defaults_to_unknown(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Version should default to 'unknown' when not declared."""
        source = "from mcp.server import Server\napp = Server('v')\n"
        (tmp_path / "server.py").write_text(source)
        skill = parser.parse(tmp_path)[0]
        assert skill.version == "unknown"

    def test_name_is_file_stem(
        self, parser: McpServerParser, tmp_path: Path
    ) -> None:
        """Skill name should be the filename stem."""
        source = "from mcp.server import Server\napp = Server('n')\n"
        (tmp_path / "main.py").write_text(source)
        skill = parser.parse(tmp_path)[0]
        assert skill.name == "main"
