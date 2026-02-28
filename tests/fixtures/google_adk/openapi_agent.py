"""Google ADK agent using OpenAPIToolset — test fixture."""

from google.adk import Agent
from google.adk.tools.openapi_tool import OpenAPIToolset

openapi_tools = OpenAPIToolset(
    spec_str='{"openapi": "3.0.0", "info": {"title": "Pet API"}}',
    spec_str_type="json",
)

agent = Agent(
    model="gemini-2.0-flash",
    name="api_agent",
    instruction="Interact with external APIs",
    tools=[openapi_tools],
)
