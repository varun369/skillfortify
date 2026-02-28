"""Minimal MCP server with one tool — test fixture for McpServerParser."""

from mcp.server import Server

app = Server("basic-server")


@app.tool()
async def greet(name: str) -> str:
    """Greet the user by name."""
    return f"Hello, {name}!"
