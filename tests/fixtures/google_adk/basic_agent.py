"""Basic Google ADK agent with function tools — test fixture."""

from google.adk import Agent


def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    return {"temp": 72, "conditions": "sunny"}


def get_time(timezone: str) -> str:
    """Get current time in a timezone."""
    return "12:00 PM"


agent = Agent(
    model="gemini-2.0-flash",
    name="weather_agent",
    instruction="Help users check weather and time",
    tools=[get_weather, get_time],
)
