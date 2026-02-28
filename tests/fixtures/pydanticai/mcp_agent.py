"""PydanticAI agent with MCP server connections."""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, MCPServerHTTP

server_stdio = MCPServerStdio('npx', ['-y', '@anthropic/mcp-server-filesystem'])
server_http = MCPServerHTTP("https://mcp.example.com/sse")

agent = Agent(
    'openai:gpt-4o',
    system_prompt='You are a file management assistant.',
    mcp_servers=[server_stdio, server_http],
)


@agent.tool_plain
def local_helper(x: str) -> str:
    """A local helper tool alongside MCP servers."""
    return x.upper()
