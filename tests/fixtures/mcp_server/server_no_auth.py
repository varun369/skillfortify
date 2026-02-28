"""MCP server without authentication — security issue fixture."""

from mcp.server import Server

app = Server("no-auth-server")


@app.tool()
async def read_database(query: str) -> str:
    """Run a database query with no authentication gate."""
    import sqlite3

    conn = sqlite3.connect("/var/data/production.db")
    cursor = conn.execute(query)
    return str(cursor.fetchall())


@app.resource("config://settings")
async def get_settings() -> str:
    """Return application settings — unprotected."""
    with open("/etc/app/settings.yaml") as fh:
        return fh.read()
