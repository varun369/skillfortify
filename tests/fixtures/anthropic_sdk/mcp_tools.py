"""Fixture: Anthropic Agent SDK agent using MCPServer connections.

Used by test_anthropic_sdk.py to verify extraction of:
- MCPServer instantiations with command and args
- Agent with MCP tool references
"""
from claude_agent_sdk import Agent
from claude_agent_sdk.tools import MCPServer

filesystem_mcp = MCPServer(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem"],
)

db_mcp = MCPServer(
    command="uvx",
    args=["mcp-server-sqlite", "--db", "data.db"],
)

agent = Agent(
    name="mcp_agent",
    model="claude-sonnet-4-20250514",
    tools=[filesystem_mcp, db_mcp],
    instructions="You access the filesystem and database through MCP servers.",
)
