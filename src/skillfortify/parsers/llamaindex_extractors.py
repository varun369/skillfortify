"""Extraction helpers for the LlamaIndex parser.

Contains regex patterns, AST inspection utilities, and the individual
extractor functions for FunctionTool, QueryEngineTool, Agent, and data
reader definitions. Separated from the parser class to keep each
module under the 300-line hard cap.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill

FORMAT_NAME = "llamaindex"

_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

_ENV_VAR_PATTERN = re.compile(
    r"""(?:"""
    r"""\$\{?([A-Z][A-Z0-9_]{1,})\}?"""
    r"""|os\.environ\[["']([A-Z][A-Z0-9_]{1,})["']\]"""
    r"""|os\.getenv\(["']([A-Z][A-Z0-9_]{1,})["']\)"""
    r""")""",
    re.MULTILINE,
)

_SHELL_CALL_PATTERN = re.compile(
    r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)"
    r"|os\.(?:system|popen))"
    r"""\s*\(\s*["']([^"']+)["']""",
)

_AGENT_CLASS_NAMES = frozenset({
    "ReActAgent",
    "FunctionCallingAgent",
    "OpenAIAgent",
    "CustomSimpleAgentWorker",
})

_READER_CLASS_NAMES = frozenset({
    "SimpleWebPageReader",
    "SimpleDirectoryReader",
    "DatabaseReader",
    "WikipediaReader",
    "BeautifulSoupWebReader",
    "TrafilaturaWebReader",
    "SlackReader",
    "DiscordReader",
    "GithubRepositoryReader",
    "GoogleDocsReader",
    "NotionPageReader",
    "S3Reader",
})


# -------------------------------------------------------------------
# Low-level text extraction
# -------------------------------------------------------------------

def extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from *text*."""
    return _URL_PATTERN.findall(text)


def extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from *text*."""
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from subprocess/os calls."""
    return _SHELL_CALL_PATTERN.findall(text)


def extract_imports(text: str) -> list[str]:
    """Extract top-level import package names (AST with regex fallback)."""
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                parts = stripped.split()
                if len(parts) >= 2:
                    imports.append(parts[1].split(".")[0])
        return sorted(set(imports))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return sorted(set(imports))


# -------------------------------------------------------------------
# AST helper utilities
# -------------------------------------------------------------------

def get_kwarg_str(call: ast.Call, key: str) -> str:
    """Extract a string keyword argument from an ``ast.Call`` node."""
    for kw in call.keywords:
        if kw.arg == key and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)
    return ""


def list_element_names(lst: ast.List) -> list[str]:
    """Extract identifier names from AST list elements."""
    names: list[str] = []
    for elt in lst.elts:
        if isinstance(elt, ast.Name):
            names.append(elt.id)
        elif isinstance(elt, ast.Attribute):
            names.append(elt.attr)
        elif isinstance(elt, ast.Call):
            func = elt.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                names.append(func.attr)
    return names


def build_skill(
    name: str,
    description: str,
    body: str,
    file_path: Path,
    source: str,
    capabilities: list[str] | None = None,
) -> ParsedSkill:
    """Construct a ``ParsedSkill`` from extracted LlamaIndex metadata.

    Security-sensitive patterns (URLs, env vars, shell commands) are
    extracted from the **full source**, not just the call body.  This is
    important because LlamaIndex separates function definitions from
    ``FunctionTool.from_defaults(fn=my_func)`` calls -- the dangerous
    code lives in the referenced function, not in the call itself.
    """
    return ParsedSkill(
        name=name,
        version="unknown",
        source_path=file_path,
        format=FORMAT_NAME,
        description=description,
        declared_capabilities=capabilities or [],
        code_blocks=[body] if body else [],
        urls=extract_urls(source),
        env_vars_referenced=extract_env_vars(source),
        shell_commands=extract_shell_commands(source),
        dependencies=extract_imports(source),
        raw_content=source,
    )


# -------------------------------------------------------------------
# Node-type detection predicates
# -------------------------------------------------------------------

def is_function_tool_call(node: ast.Call) -> bool:
    """True when *node* is ``FunctionTool.from_defaults(...)``."""
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "from_defaults":
        return False
    value = func.value
    if isinstance(value, ast.Name) and value.id == "FunctionTool":
        return True
    return isinstance(value, ast.Attribute) and value.attr == "FunctionTool"


def is_query_engine_tool(node: ast.Call) -> bool:
    """True when *node* is ``QueryEngineTool(...)``."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "QueryEngineTool":
        return True
    return isinstance(func, ast.Attribute) and func.attr == "QueryEngineTool"


def is_agent_from_tools(node: ast.Call) -> bool:
    """True when *node* is ``ReActAgent.from_tools(...)`` or similar."""
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "from_tools":
        return False
    value = func.value
    if isinstance(value, ast.Name) and value.id in _AGENT_CLASS_NAMES:
        return True
    return isinstance(value, ast.Attribute) and value.attr in _AGENT_CLASS_NAMES


def is_data_reader(node: ast.Call) -> bool:
    """True when *node* instantiates a known data reader class."""
    func = node.func
    if isinstance(func, ast.Name) and func.id in _READER_CLASS_NAMES:
        return True
    return isinstance(func, ast.Attribute) and func.attr in _READER_CLASS_NAMES


# -------------------------------------------------------------------
# Per-call-type parsers
# -------------------------------------------------------------------

def parse_function_tool(
    call: ast.Call, source: str, file_path: Path,
) -> ParsedSkill:
    """Extract a ``ParsedSkill`` from ``FunctionTool.from_defaults(...)``."""
    fn_name = ""
    for kw in call.keywords:
        if kw.arg == "fn" and isinstance(kw.value, ast.Name):
            fn_name = kw.value.id
    if not fn_name and call.args:
        first_arg = call.args[0]
        if isinstance(first_arg, ast.Name):
            fn_name = first_arg.id
    name = get_kwarg_str(call, "name") or fn_name or "unnamed_function_tool"
    description = get_kwarg_str(call, "description")
    body = ast.get_source_segment(source, call) or ""
    caps = [f"tool:{fn_name}"] if fn_name else []
    return build_skill(name, description, body, file_path, source, caps)


def parse_query_engine_tool(
    call: ast.Call, source: str, file_path: Path,
) -> ParsedSkill:
    """Extract a ``ParsedSkill`` from ``QueryEngineTool(...)``."""
    meta_name, meta_desc = "", ""
    for kw in call.keywords:
        if kw.arg == "metadata" and isinstance(kw.value, ast.Call):
            meta_name = get_kwarg_str(kw.value, "name")
            meta_desc = get_kwarg_str(kw.value, "description")
    name = meta_name or "unnamed_query_tool"
    body = ast.get_source_segment(source, call) or ""
    return build_skill(name, meta_desc, body, file_path, source, ["query_engine:read"])


def parse_agent_call(
    call: ast.Call, source: str, file_path: Path,
) -> ParsedSkill:
    """Extract a ``ParsedSkill`` from ``ReActAgent.from_tools(...)`` etc."""
    func = call.func
    agent_type = ""
    if isinstance(func, ast.Attribute):
        val = func.value
        if isinstance(val, ast.Name):
            agent_type = val.id
        elif isinstance(val, ast.Attribute):
            agent_type = val.attr
    tool_names: list[str] = []
    for kw in call.keywords:
        if kw.arg == "tools" and isinstance(kw.value, ast.List):
            tool_names = list_element_names(kw.value)
    if not tool_names and call.args:
        first_arg = call.args[0]
        if isinstance(first_arg, ast.List):
            tool_names = list_element_names(first_arg)
    name = agent_type or "unnamed_agent"
    body = ast.get_source_segment(source, call) or ""
    caps = [f"tool:{tn}" for tn in tool_names]
    return build_skill(name, f"LlamaIndex {agent_type} agent", body, file_path, source, caps)


def parse_data_reader(
    call: ast.Call, source: str, file_path: Path,
) -> ParsedSkill:
    """Extract a ``ParsedSkill`` from a data reader constructor."""
    func = call.func
    reader_name = ""
    if isinstance(func, ast.Name):
        reader_name = func.id
    elif isinstance(func, ast.Attribute):
        reader_name = func.attr
    body = ast.get_source_segment(source, call) or ""
    return build_skill(
        reader_name, f"Data connector: {reader_name}",
        body, file_path, source, [f"reader:{reader_name}"],
    )
