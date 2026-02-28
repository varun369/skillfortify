"""Extraction helpers for n8n workflow JSON parsing.

Constants and helper functions for extracting security-relevant metadata
from n8n workflow node definitions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# --- Constants ---------------------------------------------------------------

N8N_DIR = ".n8n"
N8N_WORKFLOW_SUFFIX = ".workflow.json"
N8N_NODE_PREFIX = "n8n-nodes-"

_CODE_NODE_TYPES = frozenset({
    "n8n-nodes-base.code",
    "n8n-nodes-base.function",
    "n8n-nodes-base.functionItem",
})

_SHELL_NODE_TYPES = frozenset({
    "n8n-nodes-base.executeCommand",
    "n8n-nodes-base.ssh",
})

_WEBHOOK_NODE_TYPES = frozenset({
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.respondToWebhook",
})

_HTTP_NODE_TYPES = frozenset({
    "n8n-nodes-base.httpRequest",
})

_DATABASE_NODE_TYPES = frozenset({
    "n8n-nodes-base.postgres",
    "n8n-nodes-base.mySql",
    "n8n-nodes-base.mongoDb",
    "n8n-nodes-base.redis",
    "n8n-nodes-base.microsoftSql",
})

_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

_SHELL_COMMAND_PATTERN = re.compile(
    r"(?:curl|wget|bash|sh|rm|chmod|chown|pip|npm|apt-get|yum"
    r"|docker|kubectl|ssh|scp|nc|ncat)\s+[^\n]{3,}",
)


# --- Helper functions --------------------------------------------------------


def safe_load_json(file_path: Path) -> dict[str, Any] | None:
    """Load a JSON file, returning None on any error."""
    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def is_n8n_workflow(data: dict[str, Any]) -> bool:
    """Check if a parsed dict looks like an n8n workflow export."""
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False
    for node in nodes:
        if isinstance(node, dict):
            node_type = str(node.get("type", ""))
            if node_type.startswith(N8N_NODE_PREFIX):
                return True
    return False


def extract_node_urls(node: dict[str, Any]) -> list[str]:
    """Extract URLs from a node's parameters."""
    params = node.get("parameters", {})
    if not isinstance(params, dict):
        return []
    raw = json.dumps(params)
    return _URL_PATTERN.findall(raw)


def extract_node_code(node: dict[str, Any]) -> list[str]:
    """Extract code blocks from code/function nodes."""
    params = node.get("parameters", {})
    if not isinstance(params, dict):
        return []
    blocks: list[str] = []
    for key in ("jsCode", "pythonCode", "functionCode"):
        code = params.get(key)
        if isinstance(code, str) and code.strip():
            blocks.append(code)
    return blocks


def extract_node_shell_commands(node: dict[str, Any]) -> list[str]:
    """Extract shell commands from execute/SSH nodes."""
    params = node.get("parameters", {})
    if not isinstance(params, dict):
        return []
    commands: list[str] = []
    cmd = params.get("command")
    if isinstance(cmd, str) and cmd.strip():
        commands.append(cmd)
    return commands


def extract_node_credentials(node: dict[str, Any]) -> list[str]:
    """Extract credential type names from a node."""
    creds = node.get("credentials", {})
    if not isinstance(creds, dict):
        return []
    result: list[str] = []
    for cred_type, cred_data in creds.items():
        result.append(cred_type)
        if isinstance(cred_data, dict):
            name = cred_data.get("name", "")
            if isinstance(name, str) and name:
                result.append(name)
    return result


def extract_node_capabilities(node: dict[str, Any]) -> list[str]:
    """Derive declared capabilities from the node type."""
    node_type = str(node.get("type", ""))
    caps: list[str] = []
    if node_type in _CODE_NODE_TYPES:
        caps.append("code_execution")
    if node_type in _SHELL_NODE_TYPES:
        caps.append("shell_access")
    if node_type in _HTTP_NODE_TYPES:
        caps.append("network_access")
    if node_type in _WEBHOOK_NODE_TYPES:
        caps.append("webhook_endpoint")
    if node_type in _DATABASE_NODE_TYPES:
        caps.append("database_access")
    return caps
