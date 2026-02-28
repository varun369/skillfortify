"""Fixture: Anthropic Agent SDK with sub-agent delegation patterns.

Used by test_anthropic_sdk.py to verify extraction of:
- Multiple Agent(...) definitions (sub-agents)
- Agent used as a tool inside another Agent
- Model references for each agent
"""
from claude_agent_sdk import Agent
from claude_agent_sdk.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"


researcher = Agent(
    name="researcher",
    model="claude-haiku-4-5-20251001",
    tools=[web_search],
    instructions="You research topics using web search.",
)

writer = Agent(
    name="writer",
    model="claude-haiku-4-5-20251001",
    tools=[],
    instructions="You write polished content based on research.",
)

coordinator = Agent(
    name="coordinator",
    model="claude-sonnet-4-20250514",
    tools=[researcher, writer],
    instructions="You coordinate between the researcher and writer agents.",
)
