"""Extraction helpers for Flowise chatflow parsing.

Provides constants and functions for extracting security-relevant metadata
from Flowise chatflow JSON exports: URLs, environment variables, shell
commands, credential references, code blocks, and dependency declarations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FLOWISE_DIR = ".flowise"

FLOWISE_NODE_TYPES: frozenset[str] = frozenset({
    "ChatOpenAI", "ChatAnthropic", "ChatGoogleGenerativeAI",
    "ChatHuggingFace", "ChatLocalAI", "ChatOllama",
    "CustomTool", "ToolAgent", "ConversationChain",
    "ConversationalRetrievalQAChain", "RetrievalQAChain",
    "VectorStoreAgent", "OpenAIAssistant", "BufferMemory",
    "ConversationSummaryMemory", "ZepMemory", "RedisBackedChatMemory",
    "Pinecone", "Chroma", "Weaviate", "QdrantVectorStore",
    "SupabaseVectorStore", "OpenAIEmbedding", "HuggingFaceEmbedding",
    "CohereEmbedding", "PDFLoader", "CSVLoader", "WebBrowser",
    "SerpAPI", "Calculator", "RequestsGet", "RequestsPost",
})

CREDENTIAL_INPUT_KEYS: frozenset[str] = frozenset({
    "openAIApiKey", "anthropicApiKey", "googleApiKey",
    "cohereApiKey", "huggingFaceApiKey", "pineconeApiKey",
    "weaviateApiKey", "qdrantApiKey", "supabaseApiKey",
    "serpApiKey", "zapierApiKey", "azureOpenAIApiKey",
    "awsAccessKeyId", "awsSecretAccessKey", "redisUrl",
    "zepApiKey", "apiKey",
})

_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")
_ENV_PATTERN = re.compile(r"process\.env\.([A-Z_][A-Z0-9_]*)")
_SHELL_PATTERN = re.compile(
    r"(?:execSync|exec|spawn|execFile|execFileSync)\s*\(\s*['\"]"
    r"([^'\"]+)['\"]",
)
_SHELL_CMD_PATTERN = re.compile(
    r"(?:curl|wget|bash|sh|rm|chmod|chown|pip|npm|apt-get|yum"
    r"|docker|kubectl|ssh|scp|nc|ncat)\s+[^\n'\"]{3,}",
)
_REQUIRE_PATTERN = re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def safe_load_json(file_path: Path) -> dict[str, Any] | None:
    """Load a JSON file, returning None on any error.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Parsed dict, or None if malformed or unreadable.
    """
    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def is_flowise_chatflow(data: dict[str, Any]) -> bool:
    """Determine if a parsed JSON dict looks like a Flowise chatflow.

    Args:
        data: Parsed JSON dict.

    Returns:
        True if the data matches Flowise chatflow heuristics.
    """
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_data = node.get("data")
        if not isinstance(node_data, dict):
            continue
        if str(node_data.get("type", "")) in FLOWISE_NODE_TYPES:
            return True
    return False


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text."""
    return _URL_PATTERN.findall(text)


def extract_env_vars(text: str) -> list[str]:
    """Extract process.env references from JavaScript code."""
    return sorted(set(_ENV_PATTERN.findall(text)))


def extract_shell_commands(text: str) -> list[str]:
    """Extract shell invocations from JavaScript code."""
    found: list[str] = []
    found.extend(_SHELL_PATTERN.findall(text))
    found.extend(_SHELL_CMD_PATTERN.findall(text))
    return found


# ---------------------------------------------------------------------------
# Node-level extraction
# ---------------------------------------------------------------------------

def extract_credentials(nodes: list[dict[str, Any]]) -> list[str]:
    """Extract credential input key names from node inputs.

    Args:
        nodes: List of Flowise node dicts.

    Returns:
        Sorted list of credential input key names found.
    """
    creds: set[str] = set()
    for node in nodes:
        data = node.get("data", {})
        if not isinstance(data, dict):
            continue
        inputs = data.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        for key, value in inputs.items():
            if key in CREDENTIAL_INPUT_KEYS and value:
                creds.add(key)
    return sorted(creds)


def extract_code_blocks(nodes: list[dict[str, Any]]) -> list[str]:
    """Extract JavaScript code from CustomTool nodes.

    Args:
        nodes: List of Flowise node dicts.

    Returns:
        List of JavaScript code strings.
    """
    blocks: list[str] = []
    for node in nodes:
        data = node.get("data", {})
        if not isinstance(data, dict):
            continue
        if str(data.get("type", "")) != "CustomTool":
            continue
        inputs = data.get("inputs", {})
        if not isinstance(inputs, dict):
            continue
        js_code = inputs.get("javascriptFunction", "")
        if js_code and isinstance(js_code, str):
            blocks.append(js_code)
    return blocks


def extract_node_dependencies(code_blocks: list[str]) -> list[str]:
    """Extract require() dependencies from JavaScript code blocks.

    Args:
        code_blocks: List of JavaScript source strings.

    Returns:
        Sorted list of unique dependency names.
    """
    deps: set[str] = set()
    for block in code_blocks:
        deps.update(_REQUIRE_PATTERN.findall(block))
    return sorted(deps)


def get_node_types(nodes: list[dict[str, Any]]) -> list[str]:
    """Collect declared component types from all nodes.

    Args:
        nodes: List of Flowise node dicts.

    Returns:
        Sorted list of unique node type strings.
    """
    types: set[str] = set()
    for node in nodes:
        data = node.get("data", {})
        if isinstance(data, dict):
            node_type = data.get("type", "")
            if node_type:
                types.add(str(node_type))
    return sorted(types)
