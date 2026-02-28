"""Haystack pipeline with Tool and ToolInvoker -- test fixture."""

import requests

from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.tools import ToolInvoker
from haystack.tools import Tool, create_tool_from_function


def weather_forecast(city: str) -> str:
    """Get weather forecast for a city."""
    return requests.get(f"https://api.weather.com/v1/forecast/{city}").text


def stock_price(ticker: str) -> str:
    """Look up a stock price by ticker symbol."""
    return requests.get(f"https://finance.example.com/api/quote/{ticker}").text


weather_tool = create_tool_from_function(weather_forecast)
stock_tool = Tool(
    name="stock_price",
    description="Get current stock price",
    function=stock_price,
    parameters={
        "type": "object",
        "properties": {"ticker": {"type": "string"}},
    },
)

pipe = Pipeline()
pipe.add_component("llm", OpenAIChatGenerator(model="gpt-4o"))
pipe.add_component("tool_invoker", ToolInvoker(tools=[weather_tool, stock_tool]))
pipe.connect("llm", "tool_invoker")
