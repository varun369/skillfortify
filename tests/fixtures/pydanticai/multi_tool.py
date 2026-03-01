"""PydanticAI agent with multiple tools of both decorator types."""

from pydantic_ai import Agent, RunContext
import requests
import os

agent = Agent(
    'anthropic:claude-3-5-sonnet',
    system_prompt='You are a research assistant.',
)


@agent.tool
def search_web(ctx: RunContext, query: str) -> str:
    """Search the web for information."""
    return requests.get(
        "https://api.search.example.com/v2",
        params={"q": query},
    ).text


@agent.tool_plain
def calculate(expression: str) -> float:
    """Calculate a math expression safely."""
    # NOTE: This is a TEST FIXTURE for security scanning.
    # The parser should detect this as a code_block for further analysis.
    return float(expression)


@agent.tool_plain
def read_file(path: str) -> str:
    """Read a file from disk."""
    os.environ["FILE_SERVICE_TOKEN"]
    return open(path).read()
