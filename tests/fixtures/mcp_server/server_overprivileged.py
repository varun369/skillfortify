"""Overprivileged MCP server — excessive file/network/shell access fixture."""

import os
import shutil
import subprocess

import httpx
from mcp import Server

app = Server("overprivileged-server")


@app.tool()
async def run_shell(command: str) -> str:
    """Execute an arbitrary shell command."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout


@app.tool()
async def fetch_url(url: str) -> str:
    """Fetch arbitrary URL content."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    return resp.text


@app.tool()
async def manage_files(src: str, dst: str) -> str:
    """Copy files using shutil — broad filesystem access."""
    shutil.copy2(src, dst)
    return f"Copied {src} to {dst}"


@app.tool()
async def read_secrets() -> dict:
    """Read sensitive environment variables."""
    return {
        "db_password": os.environ.get("DB_PASSWORD", ""),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "secret": os.environ["APP_SECRET_KEY"],
    }


@app.resource("files://{path}")
async def read_any_file(path: str) -> str:
    """Read any file on disk — dangerous."""
    with open(path) as fh:
        return fh.read()


@app.prompt("system")
async def system_prompt() -> str:
    """Return a system prompt."""
    return "You are a helpful assistant."
