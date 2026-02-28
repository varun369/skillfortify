"""Fixture: Composio custom @action definitions.

Used by test_composio.py to verify extraction of:
- @action decorated functions (custom tool definitions)
- Docstrings from custom actions
- URLs and dependencies from custom action bodies
"""
from composio import action
import requests


@action(toolname="weather_lookup")
def get_current_weather(city: str) -> str:
    """Fetch current weather data for a given city."""
    return requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={city}"
    ).text


@action(toolname="stock_price")
def get_stock_price(ticker: str) -> dict:
    """Get the latest stock price for a ticker symbol."""
    resp = requests.get(f"https://api.finance.example.com/price/{ticker}")
    return resp.json()
