"""Fixture: basic Anthropic Agent SDK agent with @tool functions.

Used by test_anthropic_sdk.py to verify extraction of:
- @tool decorated functions
- Agent(...) instantiations with model, tools, instructions
- URLs and import extraction
"""
from claude_agent_sdk import Agent
from claude_agent_sdk.tools import tool
import requests


@tool
def search_files(query: str, directory: str = ".") -> str:
    """Search for files matching a query in a directory."""
    import subprocess
    result = subprocess.run(["grep", "-r", query, directory], capture_output=True)
    return result.stdout.decode()


@tool
def fetch_weather(city: str) -> str:
    """Fetch current weather data for a city."""
    resp = requests.get(f"https://api.weather.com/v2/{city}")
    return resp.json()


agent = Agent(
    name="research_assistant",
    model="claude-sonnet-4-20250514",
    tools=[search_files, fetch_weather],
    instructions="You are a helpful research assistant.",
)
