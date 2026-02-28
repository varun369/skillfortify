"""Tests for the Mastra agent framework parser."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.mastra_tools import MastraParser

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "mastra"

_BASIC_TOOL_SRC = """\
import { createTool } from '@mastra/core/tools';
import { z } from 'zod';

const pingTool = createTool({
  id: 'ping-service',
  description: 'Ping a remote service endpoint',
  inputSchema: z.object({ url: z.string() }),
  execute: async ({ context }) => {
    const resp = await fetch(`https://healthcheck.example.com/${context.url}`);
    return resp.json();
  },
});
"""

_AGENT_SRC = """\
import { Agent } from '@mastra/core/agents';
import { openai } from '@ai-sdk/openai';

const codeAgent = new Agent({
  name: 'code-reviewer',
  instructions: 'Review pull requests and suggest improvements',
  model: openai('gpt-4o'),
  tools: {},
});
"""

_MULTI_AGENT_SRC = """\
import { Agent } from '@mastra/core/agents';
import { createTool } from '@mastra/core/tools';

const toolA = createTool({
  id: 'tool-alpha',
  description: 'First helper tool',
  execute: async () => ({}),
});

const agentOne = new Agent({
  name: 'planner',
  instructions: 'Plan task execution steps',
  tools: { toolA },
});

const agentTwo = new Agent({
  name: 'executor',
  instructions: 'Execute planned tasks',
  tools: { toolA },
});
"""

_ENV_HEAVY_SRC = """\
import { createTool } from '@mastra/core/tools';

const secretTool = createTool({
  id: 'secret-fetcher',
  description: 'Fetch secrets from vault',
  execute: async () => {
    const dbPass = process.env.DB_PASSWORD;
    const apiKey = process.env.API_SECRET_KEY;
    const token = process.env['AUTH_TOKEN'];
    return { dbPass, apiKey, token };
  },
});
"""

# Build shell source without literal problematic strings
_SHELL_IMPORT = "import { " + "exec } from 'child" + "_process';"
_SHELL_SRC = (
    "import { createTool } from '@mastra/core/tools';\n"
    + _SHELL_IMPORT + "\n\n"
    + "const dangerTool = createTool({\n"
    + "  id: 'shell-runner',\n"
    + "  description: 'Run arbitrary commands',\n"
    + "  execute: async ({ context }) => {\n"
    + "    return new Promise((resolve) => {\n"
    + "      exec(context.cmd, (err, stdout) => resolve(stdout));\n"
    + "    });\n"
    + "  },\n"
    + "});\n"
)

_FS_SRC = """\
import { createTool } from '@mastra/core/tools';
import * as fs from 'fs';

const fileTool = createTool({
  id: 'file-reader',
  description: 'Read a file from disk',
  execute: async ({ context }) => {
    return fs.readFileSync(context.path, 'utf-8');
  },
});
"""

_EMPTY_TS = "// This file has no Mastra imports or tools.\nconsole.log('hello world');\n"

_MALFORMED_TS = """\
import { createTool from '@mastra/core/tools';
// missing closing brace -- syntax error in TS but we still try regex
const broken = createTool({
  id: 'broken-tool',
  description: 'This has malformed syntax',
"""

_PKG_JSON_MASTRA = json.dumps({"name": "test-mastra",
    "dependencies": {"@mastra/core": "^0.5.0", "zod": "^3.22.0"},
    "devDependencies": {"typescript": "^5.3.0"}})
_PKG_JSON_NO_MASTRA = json.dumps({"name": "test-other",
    "dependencies": {"express": "^4.18.0"}})
# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def parser() -> MastraParser:
    return MastraParser()

@pytest.fixture
def basic_tool_dir(tmp_path: Path) -> Path:
    (tmp_path / "tool.ts").write_text(_BASIC_TOOL_SRC)
    return tmp_path

@pytest.fixture
def agent_dir(tmp_path: Path) -> Path:
    (tmp_path / "agent.ts").write_text(_AGENT_SRC)
    return tmp_path

@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    (tmp_path / "mastra.config.ts").write_text(_BASIC_TOOL_SRC)
    return tmp_path

@pytest.fixture
def pkg_json_dir(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text(_PKG_JSON_MASTRA)
    (tmp_path / "index.ts").write_text(_BASIC_TOOL_SRC)
    return tmp_path

@pytest.fixture
def fixture_dir(tmp_path: Path) -> Path:
    dest = tmp_path / "mastra"
    shutil.copytree(_FIXTURES, dest)
    return dest

@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    return tmp_path

# ── Detection tests ───────────────────────────────────────────────────────

class TestMastraCanParse:
    """Validate MastraParser.can_parse() detection logic."""

    def test_detects_mastra_config_ts(self, parser: MastraParser, config_dir: Path) -> None:
        assert parser.can_parse(config_dir) is True

    def test_detects_mastra_config_js(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "mastra.config.js").write_text(_BASIC_TOOL_SRC)
        assert parser.can_parse(tmp_path) is True

    def test_detects_package_json_dep(self, parser: MastraParser, pkg_json_dir: Path) -> None:
        assert parser.can_parse(pkg_json_dir) is True

    def test_detects_import_in_ts_file(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        assert parser.can_parse(basic_tool_dir) is True

    def test_rejects_empty_dir(self, parser: MastraParser, empty_dir: Path) -> None:
        assert parser.can_parse(empty_dir) is False

    def test_rejects_non_mastra_package(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(_PKG_JSON_NO_MASTRA)
        assert parser.can_parse(tmp_path) is False

    def test_rejects_plain_ts_file(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "app.ts").write_text(_EMPTY_TS)
        assert parser.can_parse(tmp_path) is False

    def test_rejects_non_directory(self, parser: MastraParser, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")
        assert parser.can_parse(f) is False

    def test_detects_fixture_dir(self, parser: MastraParser, fixture_dir: Path) -> None:
        assert parser.can_parse(fixture_dir) is True


# ── Tool extraction tests ─────────────────────────────────────────────────

class TestMastraToolParsing:
    """Validate extraction of createTool() definitions."""

    def test_extracts_tool_id(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        skills = parser.parse(basic_tool_dir)
        assert any(s.name == "ping-service" for s in skills)

    def test_extracts_tool_description(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        skills = parser.parse(basic_tool_dir)
        tool = next(s for s in skills if s.name == "ping-service")
        assert "Ping a remote service" in tool.description

    def test_extracts_multiple_tools(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "tools.ts").write_text(_MULTI_AGENT_SRC)
        skills = parser.parse(tmp_path)
        assert any(s.name == "tool-alpha" for s in skills)

    def test_format_is_mastra(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        for skill in parser.parse(basic_tool_dir):
            assert skill.format == "mastra"

    def test_returns_parsed_skill_instances(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        for skill in parser.parse(basic_tool_dir):
            assert isinstance(skill, ParsedSkill)

    def test_source_path_exists(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        for skill in parser.parse(basic_tool_dir):
            assert skill.source_path.exists()

    def test_raw_content_populated(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        assert all(len(s.raw_content) > 0 for s in parser.parse(basic_tool_dir))

    def test_fixture_basic_tool(self, parser: MastraParser, fixture_dir: Path) -> None:
        skills = parser.parse(fixture_dir)
        assert any(s.name == "get-weather" for s in skills)

    def test_fixture_multi_tool_count(self, parser: MastraParser, fixture_dir: Path) -> None:
        names = {s.name for s in parser.parse(fixture_dir)}
        assert "get-stock-price" in names
        assert "get-news" in names
        assert "calculate" in names


# ── Agent extraction tests ────────────────────────────────────────────────

class TestMastraAgentParsing:
    """Validate extraction of new Agent() definitions."""

    def test_extracts_agent_name(self, parser: MastraParser, agent_dir: Path) -> None:
        assert any(s.name == "code-reviewer" for s in parser.parse(agent_dir))

    def test_extracts_agent_instructions(self, parser: MastraParser, agent_dir: Path) -> None:
        agent = next(s for s in parser.parse(agent_dir) if s.name == "code-reviewer")
        assert "Review pull requests" in agent.instructions

    def test_agent_description_prefix(self, parser: MastraParser, agent_dir: Path) -> None:
        agent = next(s for s in parser.parse(agent_dir) if s.name == "code-reviewer")
        assert "Mastra agent" in agent.description

    def test_multiple_agents(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "agents.ts").write_text(_MULTI_AGENT_SRC)
        names = {s.name for s in parser.parse(tmp_path) if s.instructions}
        assert "planner" in names
        assert "executor" in names

    def test_fixture_agent_config(self, parser: MastraParser, fixture_dir: Path) -> None:
        assert any(s.name == "weather-agent" for s in parser.parse(fixture_dir))


# ── Security metadata extraction tests ────────────────────────────────────

class TestMastraSecurityExtraction:
    """Validate URL, env var, shell command, and capability extraction."""

    def test_extracts_urls(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        tool = next(s for s in parser.parse(basic_tool_dir) if s.name == "ping-service")
        assert any("healthcheck.example.com" in u for u in tool.urls)

    def test_extracts_env_vars(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "secret.ts").write_text(_ENV_HEAVY_SRC)
        tool = next(s for s in parser.parse(tmp_path) if s.name == "secret-fetcher")
        assert "DB_PASSWORD" in tool.env_vars_referenced
        assert "API_SECRET_KEY" in tool.env_vars_referenced

    def test_extracts_bracket_env_var(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "secret.ts").write_text(_ENV_HEAVY_SRC)
        tool = next(s for s in parser.parse(tmp_path) if s.name == "secret-fetcher")
        assert "AUTH_TOKEN" in tool.env_vars_referenced

    def test_extracts_shell_commands(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "shell.ts").write_text(_SHELL_SRC)
        tool = next(s for s in parser.parse(tmp_path) if s.name == "shell-runner")
        assert len(tool.shell_commands) > 0

    def test_detects_network_capability(self, parser: MastraParser, basic_tool_dir: Path) -> None:
        tool = next(s for s in parser.parse(basic_tool_dir) if s.name == "ping-service")
        assert "network:read" in tool.declared_capabilities

    def test_detects_filesystem_capability(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "file.ts").write_text(_FS_SRC)
        tool = next(s for s in parser.parse(tmp_path) if s.name == "file-reader")
        assert "filesystem:read" in tool.declared_capabilities

    def test_detects_system_execute(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "shell.ts").write_text(_SHELL_SRC)
        tool = next(s for s in parser.parse(tmp_path) if s.name == "shell-runner")
        assert "system:execute" in tool.declared_capabilities

    def test_detects_credentials_read(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "secret.ts").write_text(_ENV_HEAVY_SRC)
        tool = next(s for s in parser.parse(tmp_path) if s.name == "secret-fetcher")
        assert "credentials:read" in tool.declared_capabilities

    def test_fixture_unsafe_tool_caps(self, parser: MastraParser, fixture_dir: Path) -> None:
        shell_tool = next((s for s in parser.parse(fixture_dir) if s.name == "run-command"), None)
        assert shell_tool is not None
        assert "system:execute" in shell_tool.declared_capabilities
        assert "credentials:read" in shell_tool.declared_capabilities

    def test_fixture_unsafe_exfil_url(self, parser: MastraParser, fixture_dir: Path) -> None:
        file_tool = next((s for s in parser.parse(fixture_dir) if s.name == "read-file"), None)
        assert file_tool is not None
        assert any("evil.example.com" in u for u in file_tool.urls)


# ── Dependency extraction tests ───────────────────────────────────────────

class TestMastraDependencies:
    """Validate npm dependency extraction from package.json."""

    def test_extracts_npm_deps(self, parser: MastraParser, pkg_json_dir: Path) -> None:
        skills = parser.parse(pkg_json_dir)
        assert len(skills) > 0
        assert "@mastra/core" in skills[0].dependencies

    def test_extracts_dev_deps(self, parser: MastraParser, pkg_json_dir: Path) -> None:
        all_deps: set[str] = set()
        for s in parser.parse(pkg_json_dir):
            all_deps.update(s.dependencies)
        assert "typescript" in all_deps

    def test_fixture_deps(self, parser: MastraParser, fixture_dir: Path) -> None:
        all_deps: set[str] = set()
        for s in parser.parse(fixture_dir):
            all_deps.update(s.dependencies)
        assert "@mastra/core" in all_deps
        assert "zod" in all_deps


# ── Edge case and robustness tests ────────────────────────────────────────

class TestMastraEdgeCases:
    """Validate graceful handling of malformed and edge-case inputs."""

    def test_empty_dir_returns_empty(self, parser: MastraParser, empty_dir: Path) -> None:
        assert parser.parse(empty_dir) == []

    def test_malformed_ts_does_not_raise(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "broken.ts").write_text(_MALFORMED_TS)
        skills = parser.parse(tmp_path)
        assert any(s.name == "broken-tool" for s in skills)

    def test_non_directory_parse_returns_empty(self, parser: MastraParser, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")
        assert parser.parse(f) == []

    def test_unreadable_config_returns_empty(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "mastra.config.ts").write_text("")
        assert parser.parse(tmp_path) == []

    def test_empty_ts_file(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "empty.ts").write_text("")
        assert parser.parse(tmp_path) == []

    def test_binary_file_skipped(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "binary.ts").write_bytes(b"\x00\x01\x02\xff\xfe")
        assert parser.parse(tmp_path) == []

    def test_package_json_malformed(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{broken json")
        assert parser.can_parse(tmp_path) is False

    def test_package_json_non_dict(self, parser: MastraParser, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("[1, 2, 3]")
        assert parser.can_parse(tmp_path) is False

    def test_subdirectory_src_scanning(self, parser: MastraParser, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "tool.ts").write_text(_BASIC_TOOL_SRC)
        assert parser.can_parse(tmp_path) is True
        assert any(s.name == "ping-service" for s in parser.parse(tmp_path))

    def test_tools_subdirectory_scanning(self, parser: MastraParser, tmp_path: Path) -> None:
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "weather.ts").write_text(_BASIC_TOOL_SRC)
        assert parser.can_parse(tmp_path) is True
