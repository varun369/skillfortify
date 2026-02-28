"""Tests for the Flowise chatflow parser.

Flowise chatflows are exported as JSON files containing ``nodes`` and
``edges`` arrays.  The parser extracts security-relevant metadata including
code blocks, credential references, URLs, environment variables, and shell
commands from custom tool JavaScript, model inputs, and node configurations.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.flowise_flow import FlowiseParser

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "flowise"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def parser() -> FlowiseParser:
    """Return a fresh FlowiseParser instance."""
    return FlowiseParser()


@pytest.fixture
def basic_dir(tmp_path: Path) -> Path:
    """Directory with a basic Flowise chatflow."""
    shutil.copy(FIXTURES_DIR / "basic_chatflow.json", tmp_path / "basic_chatflow.json")
    return tmp_path


@pytest.fixture
def custom_tool_dir(tmp_path: Path) -> Path:
    """Directory with a chatflow containing a custom tool."""
    shutil.copy(FIXTURES_DIR / "custom_tool_flow.json", tmp_path / "custom_tool_flow.json")
    return tmp_path


@pytest.fixture
def api_key_dir(tmp_path: Path) -> Path:
    """Directory with a chatflow containing hardcoded API keys."""
    shutil.copy(FIXTURES_DIR / "api_key_flow.json", tmp_path / "api_key_flow.json")
    return tmp_path


@pytest.fixture
def multi_tool_dir(tmp_path: Path) -> Path:
    """Directory with a chatflow containing multiple custom tools."""
    shutil.copy(FIXTURES_DIR / "multi_tool_flow.json", tmp_path / "multi_tool_flow.json")
    return tmp_path


@pytest.fixture
def unsafe_dir(tmp_path: Path) -> Path:
    """Directory with a chatflow containing malicious custom tools."""
    shutil.copy(FIXTURES_DIR / "unsafe_flow.json", tmp_path / "unsafe_flow.json")
    return tmp_path


@pytest.fixture
def flowise_subdir(tmp_path: Path) -> Path:
    """Directory with a .flowise/ subdirectory containing a chatflow."""
    d = tmp_path / ".flowise"
    d.mkdir()
    shutil.copy(FIXTURES_DIR / "basic_chatflow.json", d / "flow.json")
    return tmp_path


# ---------------------------------------------------------------------------
# TestCanParse
# ---------------------------------------------------------------------------

class TestCanParse:
    """Validate the can_parse detection logic."""

    def test_detects_basic_chatflow(self, parser: FlowiseParser, basic_dir: Path) -> None:
        assert parser.can_parse(basic_dir) is True

    def test_detects_custom_tool_flow(self, parser: FlowiseParser, custom_tool_dir: Path) -> None:
        assert parser.can_parse(custom_tool_dir) is True

    def test_detects_flowise_subdir(self, parser: FlowiseParser, flowise_subdir: Path) -> None:
        assert parser.can_parse(flowise_subdir) is True

    def test_rejects_empty_dir(self, parser: FlowiseParser, tmp_path: Path) -> None:
        assert parser.can_parse(tmp_path) is False

    def test_rejects_empty_json(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "flow.json").write_text("{}")
        assert parser.can_parse(tmp_path) is False

    def test_rejects_non_flowise_json(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "x.json").write_text('{"name": "nope"}')
        assert parser.can_parse(tmp_path) is False

    def test_rejects_malformed_json(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("{nodes: [invalid")
        assert parser.can_parse(tmp_path) is False

    def test_rejects_nodes_without_matching_type(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "n.json").write_text(json.dumps({"nodes": [{"id": "x"}], "edges": []}))
        assert parser.can_parse(tmp_path) is False


# ---------------------------------------------------------------------------
# TestParseBasic
# ---------------------------------------------------------------------------

class TestParseBasic:
    """Validate basic chatflow parsing."""

    def test_name_format_version_path(self, parser: FlowiseParser, basic_dir: Path) -> None:
        skills = parser.parse(basic_dir)
        assert len(skills) >= 1
        s = skills[0]
        assert s.name == "basic_chatflow"
        assert s.format == "flowise"
        assert s.version == "unknown"
        assert s.source_path.exists()
        assert isinstance(s, ParsedSkill)

    def test_raw_content_and_capabilities(self, parser: FlowiseParser, basic_dir: Path) -> None:
        s = parser.parse(basic_dir)[0]
        assert "ChatOpenAI" in s.raw_content
        assert "ChatOpenAI" in s.declared_capabilities
        assert "ConversationChain" in s.declared_capabilities

    def test_description_contains_labels(self, parser: FlowiseParser, basic_dir: Path) -> None:
        desc = parser.parse(basic_dir)[0].description
        assert "Flowise chatflow" in desc
        assert "ChatOpenAI" in desc


# ---------------------------------------------------------------------------
# TestParseCustomTool
# ---------------------------------------------------------------------------

class TestParseCustomTool:
    """Validate custom tool code extraction."""

    def test_code_blocks_extracted(self, parser: FlowiseParser, custom_tool_dir: Path) -> None:
        s = parser.parse(custom_tool_dir)[0]
        assert len(s.code_blocks) >= 1
        assert "fetch" in s.code_blocks[0]

    def test_urls_and_deps_from_code(self, parser: FlowiseParser, custom_tool_dir: Path) -> None:
        s = parser.parse(custom_tool_dir)[0]
        assert any("api.weather.com" in u for u in s.urls)
        assert "node-fetch" in s.dependencies

    def test_capabilities_include_agent_and_tool(self, parser: FlowiseParser, custom_tool_dir: Path) -> None:
        caps = parser.parse(custom_tool_dir)[0].declared_capabilities
        assert "ToolAgent" in caps
        assert "CustomTool" in caps


# ---------------------------------------------------------------------------
# TestParseApiKeys
# ---------------------------------------------------------------------------

class TestParseApiKeys:
    """Validate detection of hardcoded API keys in node inputs."""

    def test_detects_credential_keys(self, parser: FlowiseParser, api_key_dir: Path) -> None:
        env = parser.parse(api_key_dir)[0].env_vars_referenced
        assert "openAIApiKey" in env
        assert "pineconeApiKey" in env
        assert len(env) >= 2

    def test_extracts_custom_base_url(self, parser: FlowiseParser, api_key_dir: Path) -> None:
        assert any("custom-openai.example.com" in u for u in parser.parse(api_key_dir)[0].urls)


# ---------------------------------------------------------------------------
# TestParseMultiTool
# ---------------------------------------------------------------------------

class TestParseMultiTool:
    """Validate multi-tool chatflow parsing."""

    def test_multiple_code_blocks(self, parser: FlowiseParser, multi_tool_dir: Path) -> None:
        assert len(parser.parse(multi_tool_dir)[0].code_blocks) == 3

    def test_env_vars_across_tools(self, parser: FlowiseParser, multi_tool_dir: Path) -> None:
        env = parser.parse(multi_tool_dir)[0].env_vars_referenced
        for var in ("SEARCH_API_KEY", "DATABASE_URL", "SMTP_PASSWORD", "SMTP_USER"):
            assert var in env

    def test_dependencies_across_tools(self, parser: FlowiseParser, multi_tool_dir: Path) -> None:
        deps = parser.parse(multi_tool_dir)[0].dependencies
        assert "axios" in deps
        assert "pg" in deps
        assert "nodemailer" in deps

    def test_urls_across_tools(self, parser: FlowiseParser, multi_tool_dir: Path) -> None:
        urls = parser.parse(multi_tool_dir)[0].urls
        assert any("search-engine.com" in u for u in urls)
        assert any("smtp.company.com" in u for u in urls)

    def test_capabilities(self, parser: FlowiseParser, multi_tool_dir: Path) -> None:
        caps = parser.parse(multi_tool_dir)[0].declared_capabilities
        assert "CustomTool" in caps and "ToolAgent" in caps


# ---------------------------------------------------------------------------
# TestParseUnsafe
# ---------------------------------------------------------------------------

class TestParseUnsafe:
    """Validate detection of malicious patterns in unsafe flows."""

    def test_malicious_urls(self, parser: FlowiseParser, unsafe_dir: Path) -> None:
        urls = parser.parse(unsafe_dir)[0].urls
        assert any("evil.attacker.com" in u for u in urls)
        assert any("c2.malware.net" in u for u in urls)
        assert any("malicious-cdn.evil.org" in u for u in urls)

    def test_shell_commands_detected(self, parser: FlowiseParser, unsafe_dir: Path) -> None:
        assert len(parser.parse(unsafe_dir)[0].shell_commands) >= 1

    def test_secret_env_vars(self, parser: FlowiseParser, unsafe_dir: Path) -> None:
        env = parser.parse(unsafe_dir)[0].env_vars_referenced
        assert "AWS_SECRET_ACCESS_KEY" in env
        assert "GITHUB_TOKEN" in env
        assert "openAIApiKey" in env

    def test_child_process_dependency(self, parser: FlowiseParser, unsafe_dir: Path) -> None:
        assert "child_process" in parser.parse(unsafe_dir)[0].dependencies


# ---------------------------------------------------------------------------
# TestFlowiseSubdir
# ---------------------------------------------------------------------------

class TestFlowiseSubdir:
    """Validate .flowise/ directory scanning."""

    def test_parses_and_formats(self, parser: FlowiseParser, flowise_subdir: Path) -> None:
        skills = parser.parse(flowise_subdir)
        assert len(skills) >= 1
        for skill in skills:
            assert skill.format == "flowise"


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Validate edge case handling and robustness."""

    def test_empty_json_returns_empty(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "e.json").write_text("{}")
        assert parser.parse(tmp_path) == []

    def test_malformed_json_returns_empty(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "b.json").write_text("{bad json")
        assert parser.parse(tmp_path) == []

    def test_non_flowise_json_returns_empty(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "x.json").write_text('{"name":"a"}')
        assert parser.parse(tmp_path) == []

    def test_empty_dir_returns_empty(self, parser: FlowiseParser, tmp_path: Path) -> None:
        assert parser.parse(tmp_path) == []

    def test_binary_file_no_crash(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "f.json").write_bytes(b"\x00\x01\xff\xfe")
        assert isinstance(parser.parse(tmp_path), list)

    def test_nodes_as_non_list(self, parser: FlowiseParser, tmp_path: Path) -> None:
        (tmp_path / "n.json").write_text(json.dumps({"nodes": "bad"}))
        assert parser.parse(tmp_path) == []

    def test_node_with_empty_data(self, parser: FlowiseParser, tmp_path: Path) -> None:
        data = {"nodes": [
            {"id": "x", "data": {"type": "ChatOpenAI", "inputs": {}}},
            {"id": "y", "data": {}}, {"id": "z"},
        ], "edges": []}
        (tmp_path / "p.json").write_text(json.dumps(data))
        assert len(parser.parse(tmp_path)) == 1

    def test_custom_tool_empty_js(self, parser: FlowiseParser, tmp_path: Path) -> None:
        data = {"nodes": [
            {"id": "t", "data": {"type": "CustomTool", "inputs": {"javascriptFunction": ""}}},
            {"id": "c", "data": {"type": "ChatOpenAI", "inputs": {}}},
        ], "edges": []}
        (tmp_path / "ej.json").write_text(json.dumps(data))
        s = parser.parse(tmp_path)
        assert len(s) == 1
        assert s[0].code_blocks == []

    def test_inputs_as_non_dict(self, parser: FlowiseParser, tmp_path: Path) -> None:
        data = {"nodes": [{"id": "a", "data": {"type": "ChatOpenAI", "inputs": "bad"}}], "edges": []}
        (tmp_path / "bi.json").write_text(json.dumps(data))
        assert len(parser.parse(tmp_path)) == 1

    def test_multiple_json_files(self, parser: FlowiseParser, tmp_path: Path) -> None:
        for name in ("a.json", "b.json"):
            d = {"nodes": [{"id": "c", "data": {"type": "ChatOpenAI", "inputs": {}}}], "edges": []}
            (tmp_path / name).write_text(json.dumps(d))
        assert len(parser.parse(tmp_path)) == 2
