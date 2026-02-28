"""Google ADK agent using built-in tools — test fixture."""

from google.adk import Agent
from google.adk.tools import code_execution, google_search

agent = Agent(
    model="gemini-2.0-flash",
    name="search_agent",
    instruction="Search the web and execute code",
    tools=[google_search, code_execution],
)
