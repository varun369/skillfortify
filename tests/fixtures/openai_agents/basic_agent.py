"""Fixture: basic OpenAI Agents SDK agent with function tools.

Used by test_openai_agents.py to verify extraction of:
- @function_tool decorated functions
- Agent(...) instantiations with name, instructions, tools
- URLs, imports, docstrings
"""
from agents import Agent, Runner, function_tool
import requests


@function_tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return requests.get(f"https://api.weather.com/v1/{city}").text


@function_tool
def translate_text(text: str, target_lang: str) -> str:
    """Translate text to a target language."""
    return requests.post(
        "https://translate.example.com/api",
        json={"text": text, "lang": target_lang},
    ).text


agent = Agent(
    name="weather_assistant",
    instructions="You help users check weather and translate text.",
    tools=[get_weather, translate_text],
    model="gpt-4o",
)
