"""Tests for the Dify plugin parser.

Dify plugins are defined via ``manifest.yaml`` or ``manifest.json`` files
with a structured schema declaring tool identity, parameters, credential
requirements, and endpoint configurations. The parser must extract all
security-relevant metadata including credential variable names, URLs,
environment variables, shell commands, and dependencies.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.dify_plugin import DifyPluginParser

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "dify"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def parser() -> DifyPluginParser:
    """Return a fresh DifyPluginParser instance."""
    return DifyPluginParser()


@pytest.fixture
def basic_plugin_dir(tmp_path: Path) -> Path:
    """Directory with a basic Dify manifest.yaml."""
    shutil.copy(FIXTURES_DIR / "manifest_basic.yaml", tmp_path / "manifest.yaml")
    return tmp_path


@pytest.fixture
def unsafe_plugin_dir(tmp_path: Path) -> Path:
    """Directory with a manifest containing suspicious patterns."""
    shutil.copy(FIXTURES_DIR / "manifest_unsafe.yaml", tmp_path / "manifest.yaml")
    return tmp_path


@pytest.fixture
def credentials_plugin_dir(tmp_path: Path) -> Path:
    """Directory with a manifest declaring multiple credentials."""
    shutil.copy(FIXTURES_DIR / "manifest_credentials.yaml", tmp_path / "manifest.yaml")
    return tmp_path


@pytest.fixture
def multi_tool_dir(tmp_path: Path) -> Path:
    """Directory with a multi-tool manifest."""
    shutil.copy(FIXTURES_DIR / "manifest_multi_tool.yaml", tmp_path / "manifest.yaml")
    return tmp_path


@pytest.fixture
def provider_dir(tmp_path: Path) -> Path:
    """Directory with a provider YAML (not a manifest)."""
    shutil.copy(FIXTURES_DIR / "provider.yaml", tmp_path / "provider.yaml")
    return tmp_path


@pytest.fixture
def dify_subdir(tmp_path: Path) -> Path:
    """Directory with a .dify/ subdirectory containing a manifest."""
    dify_dir = tmp_path / ".dify"
    dify_dir.mkdir()
    shutil.copy(FIXTURES_DIR / "manifest_basic.yaml", dify_dir / "plugin.yaml")
    return tmp_path


@pytest.fixture
def empty_manifest_dir(tmp_path: Path) -> Path:
    """Directory with an empty manifest.yaml."""
    shutil.copy(FIXTURES_DIR / "empty_manifest.yaml", tmp_path / "manifest.yaml")
    return tmp_path


@pytest.fixture
def json_manifest_dir(tmp_path: Path) -> Path:
    """Directory with a manifest.json (JSON format)."""
    content = (
        '{"version": "0.1.0", "type": "tool", "author": "json-dev",'
        ' "name": "json-plugin", "description": "A JSON-defined plugin",'
        ' "tool": {"identity": {"name": "json_tool"}}}'
    )
    (tmp_path / "manifest.json").write_text(content)
    return tmp_path


@pytest.fixture
def malformed_yaml_dir(tmp_path: Path) -> Path:
    """Directory with a malformed manifest.yaml."""
    (tmp_path / "manifest.yaml").write_text("name: [broken\n  missing: {bracket")
    return tmp_path


@pytest.fixture
def non_dify_yaml_dir(tmp_path: Path) -> Path:
    """Directory with a YAML that is NOT a Dify manifest."""
    (tmp_path / "manifest.yaml").write_text("name: not-dify\ndescription: random\n")
    return tmp_path


# ---------------------------------------------------------------------------
# TestCanParse
# ---------------------------------------------------------------------------

class TestCanParse:
    """Validate the can_parse detection logic."""

    def test_detects_basic_manifest(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        assert parser.can_parse(basic_plugin_dir) is True

    def test_detects_json_manifest(self, parser: DifyPluginParser, json_manifest_dir: Path) -> None:
        assert parser.can_parse(json_manifest_dir) is True

    def test_detects_dify_subdir(self, parser: DifyPluginParser, dify_subdir: Path) -> None:
        assert parser.can_parse(dify_subdir) is True

    def test_rejects_empty_dir(self, parser: DifyPluginParser, tmp_path: Path) -> None:
        assert parser.can_parse(tmp_path) is False

    def test_rejects_empty_manifest(self, parser: DifyPluginParser, empty_manifest_dir: Path) -> None:
        assert parser.can_parse(empty_manifest_dir) is False

    def test_rejects_non_dify_yaml(self, parser: DifyPluginParser, non_dify_yaml_dir: Path) -> None:
        assert parser.can_parse(non_dify_yaml_dir) is False

    def test_rejects_malformed_yaml(self, parser: DifyPluginParser, malformed_yaml_dir: Path) -> None:
        assert parser.can_parse(malformed_yaml_dir) is False


# ---------------------------------------------------------------------------
# TestParseBasic
# ---------------------------------------------------------------------------

class TestParseBasic:
    """Validate basic manifest parsing."""

    def test_parses_plugin_name(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert len(skills) >= 1
        assert skills[0].name == "hello-world"

    def test_parses_version(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert skills[0].version == "0.0.1"

    def test_format_is_dify(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert skills[0].format == "dify"

    def test_returns_parsed_skill_instances(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        for skill in parser.parse(basic_plugin_dir):
            assert isinstance(skill, ParsedSkill)

    def test_source_path_exists(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert skills[0].source_path.exists()

    def test_raw_content_preserved(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert "hello-world" in skills[0].raw_content

    def test_declared_capabilities_includes_type(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert "tool" in skills[0].declared_capabilities

    def test_description_extracted(self, parser: DifyPluginParser, basic_plugin_dir: Path) -> None:
        skills = parser.parse(basic_plugin_dir)
        assert "hello world" in skills[0].description.lower()


# ---------------------------------------------------------------------------
# TestParseUnsafe
# ---------------------------------------------------------------------------

class TestParseUnsafe:
    """Validate detection of suspicious content in unsafe manifests."""

    def test_extracts_malicious_urls(self, parser: DifyPluginParser, unsafe_plugin_dir: Path) -> None:
        urls = parser.parse(unsafe_plugin_dir)[0].urls
        assert any("evil.example.com" in url for url in urls)

    def test_extracts_exfil_urls(self, parser: DifyPluginParser, unsafe_plugin_dir: Path) -> None:
        urls = parser.parse(unsafe_plugin_dir)[0].urls
        assert any("exfil.attacker.net" in url for url in urls)

    def test_extracts_shell_commands(self, parser: DifyPluginParser, unsafe_plugin_dir: Path) -> None:
        shell_cmds = parser.parse(unsafe_plugin_dir)[0].shell_commands
        assert any("curl" in cmd for cmd in shell_cmds)

    def test_extracts_dangerous_shell(self, parser: DifyPluginParser, unsafe_plugin_dir: Path) -> None:
        shell_cmds = parser.parse(unsafe_plugin_dir)[0].shell_commands
        assert any("rm -rf" in cmd for cmd in shell_cmds)

    def test_extracts_credential_vars(self, parser: DifyPluginParser, unsafe_plugin_dir: Path) -> None:
        env_vars = parser.parse(unsafe_plugin_dir)[0].env_vars_referenced
        assert "ATTACKER_API_KEY" in env_vars

    def test_extracts_env_vars_from_meta(self, parser: DifyPluginParser, unsafe_plugin_dir: Path) -> None:
        env_vars = parser.parse(unsafe_plugin_dir)[0].env_vars_referenced
        assert "SECRET_TOKEN" in env_vars


# ---------------------------------------------------------------------------
# TestParseCredentials
# ---------------------------------------------------------------------------

class TestParseCredentials:
    """Validate extraction of credential declarations."""

    def test_extracts_multiple_credentials(self, parser: DifyPluginParser, credentials_plugin_dir: Path) -> None:
        env_vars = parser.parse(credentials_plugin_dir)[0].env_vars_referenced
        assert "API_KEY" in env_vars
        assert "API_SECRET" in env_vars
        assert "OAUTH_TOKEN" in env_vars

    def test_extracts_api_urls(self, parser: DifyPluginParser, credentials_plugin_dir: Path) -> None:
        urls = parser.parse(credentials_plugin_dir)[0].urls
        assert any("api.service.com" in url for url in urls)


# ---------------------------------------------------------------------------
# TestParseMultiTool
# ---------------------------------------------------------------------------

class TestParseMultiTool:
    """Validate multi-tool manifest parsing."""

    def test_parses_multi_tool_manifest(self, parser: DifyPluginParser, multi_tool_dir: Path) -> None:
        assert len(parser.parse(multi_tool_dir)) >= 1

    def test_extracts_multi_tool_credentials(self, parser: DifyPluginParser, multi_tool_dir: Path) -> None:
        env_vars = parser.parse(multi_tool_dir)[0].env_vars_referenced
        assert "SEARCH_API_KEY" in env_vars
        assert "SMTP_PASSWORD" in env_vars

    def test_extracts_dependencies(self, parser: DifyPluginParser, multi_tool_dir: Path) -> None:
        deps = parser.parse(multi_tool_dir)[0].dependencies
        assert any("requests" in dep for dep in deps)
        assert any("boto3" in dep for dep in deps)

    def test_extracts_search_url(self, parser: DifyPluginParser, multi_tool_dir: Path) -> None:
        urls = parser.parse(multi_tool_dir)[0].urls
        assert any("search-api.example.com" in url for url in urls)


# ---------------------------------------------------------------------------
# TestParseProvider
# ---------------------------------------------------------------------------

class TestParseProvider:
    """Validate provider YAML parsing."""

    def test_parses_provider_file(self, parser: DifyPluginParser, provider_dir: Path) -> None:
        assert len(parser.parse(provider_dir)) >= 1

    def test_provider_name_from_identity(self, parser: DifyPluginParser, provider_dir: Path) -> None:
        assert parser.parse(provider_dir)[0].name == "custom_provider"

    def test_provider_credentials_extracted(self, parser: DifyPluginParser, provider_dir: Path) -> None:
        env_vars = parser.parse(provider_dir)[0].env_vars_referenced
        assert "PROVIDER_API_KEY" in env_vars
        assert "PROVIDER_SECRET" in env_vars

    def test_provider_format_is_dify(self, parser: DifyPluginParser, provider_dir: Path) -> None:
        assert parser.parse(provider_dir)[0].format == "dify"

    def test_provider_description(self, parser: DifyPluginParser, provider_dir: Path) -> None:
        assert "custom" in parser.parse(provider_dir)[0].description.lower()


# ---------------------------------------------------------------------------
# TestParseDifyDir
# ---------------------------------------------------------------------------

class TestParseDifyDir:
    """Validate .dify/ directory parsing."""

    def test_parses_dify_subdir(self, parser: DifyPluginParser, dify_subdir: Path) -> None:
        assert len(parser.parse(dify_subdir)) >= 1

    def test_dify_subdir_format(self, parser: DifyPluginParser, dify_subdir: Path) -> None:
        for skill in parser.parse(dify_subdir):
            assert skill.format == "dify"


# ---------------------------------------------------------------------------
# TestJsonManifest
# ---------------------------------------------------------------------------

class TestJsonManifest:
    """Validate JSON manifest parsing."""

    def test_parses_json_manifest(self, parser: DifyPluginParser, json_manifest_dir: Path) -> None:
        skills = parser.parse(json_manifest_dir)
        assert len(skills) >= 1
        assert skills[0].name == "json-plugin"

    def test_json_version(self, parser: DifyPluginParser, json_manifest_dir: Path) -> None:
        assert parser.parse(json_manifest_dir)[0].version == "0.1.0"


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Validate edge case handling and robustness."""

    def test_empty_manifest_returns_empty(self, parser: DifyPluginParser, empty_manifest_dir: Path) -> None:
        assert parser.parse(empty_manifest_dir) == []

    def test_malformed_yaml_returns_empty(self, parser: DifyPluginParser, malformed_yaml_dir: Path) -> None:
        assert parser.parse(malformed_yaml_dir) == []

    def test_non_dify_yaml_returns_empty(self, parser: DifyPluginParser, non_dify_yaml_dir: Path) -> None:
        assert parser.parse(non_dify_yaml_dir) == []

    def test_empty_dir_returns_empty(self, parser: DifyPluginParser, tmp_path: Path) -> None:
        assert parser.parse(tmp_path) == []

    def test_no_crash_on_binary_file(self, parser: DifyPluginParser, tmp_path: Path) -> None:
        (tmp_path / "manifest.yaml").write_bytes(b"\x00\x01\x02\xff\xfe")
        assert isinstance(parser.parse(tmp_path), list)
