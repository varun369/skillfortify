"""Google ADK agent using MCPToolset — test fixture."""

from google.adk import Agent
from google.adk.tools.mcp_tool import MCPToolset

mcp_tools = MCPToolset(
    connection_params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    }
)

agent = Agent(
    model="gemini-2.0-flash",
    name="filesystem_agent",
    instruction="Help users manage files via MCP",
    tools=[mcp_tools],
)
