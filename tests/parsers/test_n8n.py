"""Tests for the n8n workflow parser.

n8n workflows are exported as JSON files containing a ``nodes`` array where
each node represents an operation. The parser must extract all security-
relevant metadata including HTTP URLs, code blocks, shell commands,
credential references, webhook endpoints, and database connections.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.n8n_workflow import N8nWorkflowParser

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "n8n"


@pytest.fixture
def parser() -> N8nWorkflowParser:
    """Return a fresh N8nWorkflowParser instance."""
    return N8nWorkflowParser()


@pytest.fixture
def basic_dir(tmp_path: Path) -> Path:
    """Directory with a basic n8n workflow."""
    shutil.copy(FIXTURES_DIR / "basic_workflow.json", tmp_path / "basic_workflow.json")
    return tmp_path


@pytest.fixture
def basic_named_dir(tmp_path: Path) -> Path:
    """Directory with a workflow using .workflow.json suffix."""
    shutil.copy(FIXTURES_DIR / "basic_workflow.json", tmp_path / "my.workflow.json")
    return tmp_path


@pytest.fixture
def http_dir(tmp_path: Path) -> Path:
    """Directory with an HTTP request workflow."""
    shutil.copy(FIXTURES_DIR / "http_workflow.json", tmp_path / "http_workflow.json")
    return tmp_path


@pytest.fixture
def code_dir(tmp_path: Path) -> Path:
    """Directory with a code execution workflow."""
    shutil.copy(FIXTURES_DIR / "code_workflow.json", tmp_path / "code_workflow.json")
    return tmp_path


@pytest.fixture
def webhook_dir(tmp_path: Path) -> Path:
    """Directory with a webhook workflow."""
    shutil.copy(FIXTURES_DIR / "webhook_workflow.json", tmp_path / "webhook_workflow.json")
    return tmp_path


@pytest.fixture
def unsafe_dir(tmp_path: Path) -> Path:
    """Directory with an unsafe workflow containing malicious patterns."""
    shutil.copy(FIXTURES_DIR / "unsafe_workflow.json", tmp_path / "unsafe_workflow.json")
    return tmp_path


@pytest.fixture
def credentials_dir(tmp_path: Path) -> Path:
    """Directory with a workflow referencing multiple credentials."""
    shutil.copy(FIXTURES_DIR / "credentials_workflow.json", tmp_path / "credentials_workflow.json")
    return tmp_path


@pytest.fixture
def n8n_config_dir(tmp_path: Path) -> Path:
    """Directory with a .n8n/ subdirectory."""
    (tmp_path / ".n8n").mkdir()
    return tmp_path


@pytest.fixture
def malformed_json_dir(tmp_path: Path) -> Path:
    """Directory with malformed JSON (not using .workflow.json suffix)."""
    (tmp_path / "broken.json").write_text("{nodes: [broken}")
    return tmp_path


@pytest.fixture
def non_n8n_json_dir(tmp_path: Path) -> Path:
    """Directory with a JSON file that is NOT an n8n workflow."""
    (tmp_path / "package.json").write_text('{"name": "my-app", "version": "1.0.0"}')
    return tmp_path


class TestCanParse:
    """Validate the can_parse detection logic."""

    def test_detects_workflow_json(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        assert parser.can_parse(basic_dir) is True

    def test_detects_named_workflow_json(self, parser: N8nWorkflowParser, basic_named_dir: Path) -> None:
        assert parser.can_parse(basic_named_dir) is True

    def test_detects_n8n_dir(self, parser: N8nWorkflowParser, n8n_config_dir: Path) -> None:
        assert parser.can_parse(n8n_config_dir) is True

    def test_rejects_empty_dir(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        assert parser.can_parse(tmp_path) is False

    def test_rejects_non_n8n_json(self, parser: N8nWorkflowParser, non_n8n_json_dir: Path) -> None:
        assert parser.can_parse(non_n8n_json_dir) is False

    def test_rejects_malformed_json(self, parser: N8nWorkflowParser, malformed_json_dir: Path) -> None:
        assert parser.can_parse(malformed_json_dir) is False

    def test_detects_http_workflow(self, parser: N8nWorkflowParser, http_dir: Path) -> None:
        assert parser.can_parse(http_dir) is True


class TestParseBasic:
    """Validate basic workflow parsing."""

    def test_parses_workflow_name(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        skills = parser.parse(basic_dir)
        assert len(skills) >= 1
        assert skills[0].name == "Basic Workflow"

    def test_format_is_n8n(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        assert parser.parse(basic_dir)[0].format == "n8n"

    def test_returns_parsed_skill_instances(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        for skill in parser.parse(basic_dir):
            assert isinstance(skill, ParsedSkill)

    def test_source_path_exists(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        assert parser.parse(basic_dir)[0].source_path.exists()

    def test_raw_content_preserved(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        assert "Basic Workflow" in parser.parse(basic_dir)[0].raw_content

    def test_dependencies_contain_node_types(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        deps = parser.parse(basic_dir)[0].dependencies
        assert "n8n-nodes-base.start" in deps
        assert "n8n-nodes-base.set" in deps

    def test_description_contains_workflow_name(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        assert "Basic Workflow" in parser.parse(basic_dir)[0].description


class TestParseHTTP:
    """Validate HTTP request node extraction."""

    def test_extracts_http_urls(self, parser: N8nWorkflowParser, http_dir: Path) -> None:
        assert any("api.example.com/users" in u for u in parser.parse(http_dir)[0].urls)

    def test_extracts_webhook_site_url(self, parser: N8nWorkflowParser, http_dir: Path) -> None:
        assert any("webhook.site" in u for u in parser.parse(http_dir)[0].urls)

    def test_network_access_capability(self, parser: N8nWorkflowParser, http_dir: Path) -> None:
        assert "network_access" in parser.parse(http_dir)[0].declared_capabilities

    def test_extracts_http_credentials(self, parser: N8nWorkflowParser, http_dir: Path) -> None:
        assert "httpBasicAuth" in parser.parse(http_dir)[0].env_vars_referenced


class TestParseCode:
    """Validate code execution node extraction."""

    def test_extracts_js_code(self, parser: N8nWorkflowParser, code_dir: Path) -> None:
        assert any("$input.all()" in b for b in parser.parse(code_dir)[0].code_blocks)

    def test_extracts_python_code(self, parser: N8nWorkflowParser, code_dir: Path) -> None:
        assert any("import os" in b for b in parser.parse(code_dir)[0].code_blocks)

    def test_extracts_legacy_function_code(self, parser: N8nWorkflowParser, code_dir: Path) -> None:
        assert any("items.map" in b for b in parser.parse(code_dir)[0].code_blocks)

    def test_code_execution_capability(self, parser: N8nWorkflowParser, code_dir: Path) -> None:
        assert "code_execution" in parser.parse(code_dir)[0].declared_capabilities

    def test_multiple_code_blocks_extracted(self, parser: N8nWorkflowParser, code_dir: Path) -> None:
        assert len(parser.parse(code_dir)[0].code_blocks) >= 3


class TestParseWebhook:
    """Validate webhook node extraction."""

    def test_webhook_endpoint_capability(self, parser: N8nWorkflowParser, webhook_dir: Path) -> None:
        assert "webhook_endpoint" in parser.parse(webhook_dir)[0].declared_capabilities

    def test_webhook_node_in_dependencies(self, parser: N8nWorkflowParser, webhook_dir: Path) -> None:
        assert "n8n-nodes-base.webhook" in parser.parse(webhook_dir)[0].dependencies


class TestParseUnsafe:
    """Validate detection of suspicious/malicious patterns."""

    def test_extracts_malicious_urls(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert any("evil.attacker.com" in u for u in parser.parse(unsafe_dir)[0].urls)

    def test_extracts_shell_from_exec_node(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert any("curl" in c for c in parser.parse(unsafe_dir)[0].shell_commands)

    def test_extracts_shell_from_ssh_node(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert any("rm -rf" in c for c in parser.parse(unsafe_dir)[0].shell_commands)

    def test_extracts_malicious_code_blocks(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert any("readFileSync" in b for b in parser.parse(unsafe_dir)[0].code_blocks)

    def test_shell_access_capability(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "shell_access" in parser.parse(unsafe_dir)[0].declared_capabilities

    def test_database_access_capability(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "database_access" in parser.parse(unsafe_dir)[0].declared_capabilities

    def test_network_access_capability(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "network_access" in parser.parse(unsafe_dir)[0].declared_capabilities

    def test_webhook_endpoint_capability(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "webhook_endpoint" in parser.parse(unsafe_dir)[0].declared_capabilities

    def test_code_execution_capability(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "code_execution" in parser.parse(unsafe_dir)[0].declared_capabilities

    def test_extracts_stolen_token_cred(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "Stolen Token" in parser.parse(unsafe_dir)[0].env_vars_referenced

    def test_extracts_ssh_credential(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "sshPassword" in parser.parse(unsafe_dir)[0].env_vars_referenced

    def test_extracts_db_credential(self, parser: N8nWorkflowParser, unsafe_dir: Path) -> None:
        assert "postgres" in parser.parse(unsafe_dir)[0].env_vars_referenced


class TestParseCredentials:
    """Validate extraction of credential references."""

    def test_extracts_slack_credential(self, parser: N8nWorkflowParser, credentials_dir: Path) -> None:
        assert "slackApi" in parser.parse(credentials_dir)[0].env_vars_referenced

    def test_extracts_gmail_credential(self, parser: N8nWorkflowParser, credentials_dir: Path) -> None:
        assert "gmailOAuth2" in parser.parse(credentials_dir)[0].env_vars_referenced

    def test_extracts_aws_credential(self, parser: N8nWorkflowParser, credentials_dir: Path) -> None:
        assert "aws" in parser.parse(credentials_dir)[0].env_vars_referenced

    def test_extracts_mysql_credential(self, parser: N8nWorkflowParser, credentials_dir: Path) -> None:
        assert "mySql" in parser.parse(credentials_dir)[0].env_vars_referenced

    def test_extracts_credential_names(self, parser: N8nWorkflowParser, credentials_dir: Path) -> None:
        assert "AWS Production" in parser.parse(credentials_dir)[0].env_vars_referenced

    def test_database_access_capability(self, parser: N8nWorkflowParser, credentials_dir: Path) -> None:
        assert "database_access" in parser.parse(credentials_dir)[0].declared_capabilities


class TestEdgeCases:
    """Validate edge case handling and robustness."""

    def test_empty_dir_returns_empty(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        assert parser.parse(tmp_path) == []

    def test_malformed_json_returns_empty(self, parser: N8nWorkflowParser, malformed_json_dir: Path) -> None:
        assert parser.parse(malformed_json_dir) == []

    def test_non_n8n_json_returns_empty(self, parser: N8nWorkflowParser, non_n8n_json_dir: Path) -> None:
        assert parser.parse(non_n8n_json_dir) == []

    def test_no_crash_on_binary_file(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        (tmp_path / "bad.workflow.json").write_bytes(b"\x00\x01\x02\xff\xfe")
        assert isinstance(parser.parse(tmp_path), list)

    def test_empty_nodes_array(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        (tmp_path / "empty.json").write_text(json.dumps({"name": "Empty", "nodes": []}))
        assert parser.parse(tmp_path) == []

    def test_nodes_with_missing_type(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "NoType", "nodes": [{"id": "1", "parameters": {}}]}
        (tmp_path / "notype.json").write_text(json.dumps(data))
        assert parser.parse(tmp_path) == []

    def test_nodes_with_non_dict_entries(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "Mixed", "nodes": ["x", 42, {"type": "n8n-nodes-base.start", "parameters": {}}]}
        (tmp_path / "mixed.json").write_text(json.dumps(data))
        skills = parser.parse(tmp_path)
        assert len(skills) == 1 and skills[0].name == "Mixed"

    def test_workflow_json_suffix_preferred(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "Named", "nodes": [{"type": "n8n-nodes-base.start", "parameters": {}}]}
        (tmp_path / "my.workflow.json").write_text(json.dumps(data))
        assert parser.parse(tmp_path)[0].name == "Named"

    def test_no_duplicate_when_workflow_suffix(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "Dedup", "nodes": [{"type": "n8n-nodes-base.start", "parameters": {}}]}
        (tmp_path / "test.workflow.json").write_text(json.dumps(data))
        assert len(parser.parse(tmp_path)) == 1

    def test_null_parameters_handled(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "NP", "nodes": [{"type": "n8n-nodes-base.code", "parameters": None}]}
        (tmp_path / "np.json").write_text(json.dumps(data))
        assert len(parser.parse(tmp_path)) == 1

    def test_missing_parameters_handled(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "NoP", "nodes": [{"type": "n8n-nodes-base.httpRequest"}]}
        (tmp_path / "nop.json").write_text(json.dumps(data))
        assert len(parser.parse(tmp_path)) == 1

    def test_version_from_versionid(self, parser: N8nWorkflowParser, tmp_path: Path) -> None:
        data = {"name": "V", "versionId": "abc-123", "nodes": [{"type": "n8n-nodes-base.start", "parameters": {}}]}
        (tmp_path / "v.json").write_text(json.dumps(data))
        assert parser.parse(tmp_path)[0].version == "abc-123"

    def test_version_defaults_to_unknown(self, parser: N8nWorkflowParser, basic_dir: Path) -> None:
        assert parser.parse(basic_dir)[0].version == "unknown"
