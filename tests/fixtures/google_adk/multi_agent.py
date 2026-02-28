"""Multi-agent Google ADK setup with sub-agents — test fixture."""

from google.adk import Agent
from google.adk.tools import google_search


def summarize(text: str) -> str:
    """Summarize a block of text."""
    return text[:100]


researcher = Agent(
    name="researcher",
    model="gemini-2.0-flash",
    instruction="Research topics on the web",
    tools=[google_search],
)

writer = Agent(
    name="writer",
    model="gemini-2.0-flash",
    instruction="Write summaries based on research",
    tools=[summarize],
)

coordinator = Agent(
    name="coordinator",
    model="gemini-2.0-flash",
    instruction="Coordinate research and writing tasks",
    tools=[researcher, writer],
)
