"""``skillfortify frameworks`` -- List all 22 supported agent frameworks.

Prints a formatted table showing each framework's name, internal format
identifier, and file-detection pattern.  Useful for verifying coverage
and for documentation references.

Exit Codes:
    0 -- Always (informational command, cannot fail).
"""

from __future__ import annotations

import click

from skillfortify import __version__

# -----------------------------------------------------------------------
# Framework metadata table
# -----------------------------------------------------------------------
# Each tuple: (human_name, format_id, detection_hint)

_FRAMEWORKS: tuple[tuple[str, str, str], ...] = (
    ("Claude Code Skills", "claude", ".claude/skills/*.md"),
    ("MCP Configs", "mcp", "mcp.json, mcp_config.json"),
    ("MCP Servers", "mcp_server", "server.py with MCP SDK"),
    ("OpenClaw", "openclaw", ".claw/*.yaml"),
    ("OpenAI Agents SDK", "openai_agents", "@function_tool, Agent()"),
    ("Google ADK", "google_adk", "google.adk imports"),
    ("LangChain", "langchain", "BaseTool, @tool"),
    ("CrewAI", "crewai", "crew.yaml"),
    ("AutoGen", "autogen", "@register_for_llm"),
    ("Dify Plugins", "dify", "manifest.yaml"),
    ("Composio", "composio", "Action, App, @action"),
    ("Semantic Kernel", "semantic_kernel", "@kernel_function"),
    ("LlamaIndex", "llamaindex", "FunctionTool, ReActAgent"),
    ("n8n", "n8n", "*.workflow.json"),
    ("Flowise", "flowise", "chatflow JSON"),
    ("Mastra", "mastra", "createTool() (TypeScript)"),
    ("PydanticAI", "pydanticai", "@agent.tool"),
    ("Agno (Phidata)", "agno", "Agent(), Toolkit"),
    ("CAMEL-AI", "camel", "ChatAgent, RolePlaying"),
    ("MetaGPT", "metagpt", "Role, Action, @register_tool"),
    ("Haystack", "haystack", "Pipeline, Tool"),
    ("Anthropic Agent SDK", "anthropic_sdk", "@tool, MCPServer"),
)

# Column widths for alignment
_W_NUM = 3
_W_NAME = 22
_W_FMT = 17
_W_DET = 27

# Pre-built format string using str.format() (avoids f-string brace issues)
_ROW_FMT = "{num:>{wn}}  {name:<{wna}}  {fmt:<{wf}}  {det:<{wd}}"


def _format_row(num: str, name: str, fmt: str, det: str) -> str:
    """Render a single table row, right-stripped for clean output."""
    return _ROW_FMT.format(
        num=num, name=name, fmt=fmt, det=det,
        wn=_W_NUM, wna=_W_NAME, wf=_W_FMT, wd=_W_DET,
    ).rstrip()


def format_frameworks_table() -> str:
    """Build the complete frameworks table as a plain string.

    Returns:
        Multi-line string ready for terminal output.  Never raises.
    """
    lines: list[str] = []
    lines.append(
        f"SkillFortify v{__version__} -- {len(_FRAMEWORKS)} "
        f"Supported Agent Frameworks"
    )
    lines.append("")

    # Column headers
    lines.append(_format_row("#", "Framework", "Format", "Detection"))

    # Divider
    lines.append(
        _format_row(
            "-" * _W_NUM,
            "-" * _W_NAME,
            "-" * _W_FMT,
            "-" * _W_DET,
        )
    )

    # Data rows
    for idx, (name, fmt, det) in enumerate(_FRAMEWORKS, start=1):
        lines.append(_format_row(str(idx), name, fmt, det))

    lines.append("")
    lines.append(
        "  Run: skillfortify scan <path> to auto-detect and analyze."
    )
    return "\n".join(lines)


@click.command("frameworks")
def frameworks_command() -> None:
    """List all 22 supported agent frameworks and their detection patterns."""
    click.echo(format_frameworks_table())
