"""Fixture: MetaGPT @register_tool decorated functions.

Used by test_metagpt.py to verify extraction of:
- @register_tool() decorated functions
- URLs from tool code
- Docstring as description
"""
from metagpt.tools.tool_registry import register_tool
import requests


@register_tool()
def search_web(query: str) -> str:
    """Search the web for information."""
    return requests.get(f"https://api.search.com/v1?q={query}").text


@register_tool()
def fetch_stock_price(symbol: str) -> str:
    """Fetch current stock price for a symbol."""
    return requests.get(
        f"https://finance.example.com/api/quote/{symbol}"
    ).text
