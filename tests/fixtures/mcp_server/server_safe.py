"""Well-scoped MCP server with minimal capabilities — safe fixture."""

from mcp.server import Server

app = Server("safe-calculator")


@app.tool()
async def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@app.tool()
async def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b
