"""Fixture: agent using MCP server connections via OpenAI Agents SDK.

Used by test_openai_agents.py to verify extraction of:
- MCPServerStdio command and args
- MCPServerHTTP url
- Agent with mcp_servers list
"""
from agents import Agent
from agents.mcp import MCPServerStdio, MCPServerHTTP


stdio_server = MCPServerStdio(
    command="uvx",
    args=["some-mcp-server", "--port", "8080"],
)

http_server = MCPServerHTTP(
    url="https://mcp.internal.corp.net/v1",
)

agent = Agent(
    name="mcp_agent",
    instructions="You use MCP servers for tool access.",
    mcp_servers=[stdio_server, http_server],
)
